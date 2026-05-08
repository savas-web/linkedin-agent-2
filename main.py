import asyncio
import hashlib
import sys
import uuid
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

logging.getLogger("telegram.ext._utils.networkloop").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)

import config as cfg_module
import state as st
import examples as ex
import analytics as an
from linkedin_browser import LinkedInBrowser
from claude_agent import generate_reply
from telegram_bot import build_app, send_approval
import json


DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY", "")
OPERATOR_BOT_TOKEN = os.environ.get("OPERATOR_TELEGRAM_BOT_TOKEN", "")
OPERATOR_CHAT_ID = os.environ.get("OPERATOR_TELEGRAM_CHAT_ID", "")


async def send_operator_alert(text: str):
    if not OPERATOR_BOT_TOKEN or not OPERATOR_CHAT_ID:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{OPERATOR_BOT_TOKEN}/sendMessage",
                json={"chat_id": OPERATOR_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            )
    except Exception:
        pass


async def send_heartbeat(cfg: dict, last_error: str = None):
    if not DASHBOARD_URL:
        return
    try:
        data = st.load()
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{DASHBOARD_URL}/heartbeat",
                json={
                    "client_name": cfg["client_name"],
                    "agent_name": cfg["agent_name"],
                    "total_sent": data.get("total_sent", 0),
                    "pending_approvals": len(data.get("pending_approvals", {})),
                    "dashboard_token": cfg.get("dashboard_token", ""),
                    "last_error": last_error,
                    "analytics": an.get_summary(),
                },
                headers={"x-api-key": DASHBOARD_API_KEY},
            )
    except Exception:
        pass


def _msg_hash(thread_id: str, message: str) -> str:
    return hashlib.md5(f"{thread_id}:{message[:100]}".encode()).hexdigest()


def is_duplicate(thread_id: str, message: str) -> bool:
    data = st.load()
    return _msg_hash(thread_id, message) in data.get("sent_hashes", [])


def record_sent(thread_id: str, message: str):
    data = st.load()
    hashes = data.get("sent_hashes", [])
    hashes.append(_msg_hash(thread_id, message))
    data["sent_hashes"] = hashes[-1000:]
    st.save(data)


def get_client_name() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return "max_rooney"


async def send_weekly_report(tg_app, cfg: dict):
    now = datetime.now(ZoneInfo("Europe/Amsterdam"))
    if now.weekday() != 0 or now.hour != 10:
        return

    data = st.load()
    current_week = now.strftime("%Y-W%W")
    if data.get("last_report_week") == current_week:
        return

    weekly_sent = data.get("weekly_sent", 0)
    pending = len(data.get("pending_approvals", {}))
    week_label = now.strftime("%-d %b %Y")

    summary = an.get_summary()
    stages = summary.get("stages", {})
    text = (
        f"🎖 *{cfg['agent_name']} — Weekly Report*\n\n"
        f"Week of {week_label}\n\n"
        f"Replies sent this week: *{weekly_sent}*\n"
        f"Pending approvals: *{pending}*\n"
        f"Total sent all time: *{data.get('total_sent', 0)}*\n\n"
        f"*Conversation Stages*\n"
        f"New (no reply yet): *{stages.get('new', 0)}*\n"
        f"Replied: *{stages.get('replied', 0)}*\n"
        f"Warm (3+ exchanges): *{stages.get('warm', 0)}*\n"
        f"Calendly sent: *{stages.get('calendly_sent', 0)}*\n"
        f"Dead (14 days silent): *{stages.get('dead', 0)}*"
    )

    await tg_app.bot.send_message(
        chat_id=cfg["telegram_chat_id"],
        text=text,
        parse_mode="Markdown",
    )

    data["last_report_week"] = current_week
    data["weekly_sent"] = 0
    st.save(data)
    print("  📊 Weekly report sent.")


async def flush_unread_queue(browser: LinkedInBrowser):
    data = st.load()
    queue = list(data.get("mark_unread_queue", []))
    if not queue:
        return
    for thread_id in queue:
        await browser.mark_as_unread(thread_id)
    data = st.load()
    data["mark_unread_queue"] = []
    st.save(data)


async def flush_approved_queue(browser: LinkedInBrowser, cfg: dict):
    data = st.load()
    queue = list(data.get("approved_queue", []))
    if not queue:
        return

    for item in queue:
        thread_id = item["thread_id"]
        message = item["message"]

        approved_at = item.get("approved_at")
        if approved_at:
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(approved_at)).total_seconds()
            if elapsed < 300:
                remaining = int(300 - elapsed)
                print(f"  ⏳ Approved reply for {thread_id} — sending in {remaining}s.")
                continue

        messages = await browser.get_conversation_messages(thread_id)
        if messages and messages[-1]["role"] == "assistant":
            print(f"  ⏭️  Skipping approved message for thread {thread_id} — we already sent the last message manually.")
            data = st.load()
            data["approved_queue"] = [
                x for x in data["approved_queue"]
                if not (x["thread_id"] == thread_id and x["message"] == message)
            ]
            st.save(data)
            continue

        if is_duplicate(thread_id, message):
            print(f"  ⛔ Duplicate detected for thread {thread_id}, skipping.")
            data = st.load()
            data["approved_queue"] = [
                x for x in data["approved_queue"]
                if not (x["thread_id"] == thread_id and x["message"] == message)
            ]
            st.save(data)
            continue

        print(f"  → Sending approved reply to thread {thread_id}...")
        success = await browser.send_message(thread_id, message)
        if success:
            record_sent(thread_id, message)
            data = st.load()
            data["total_sent"] += 1
            data["weekly_sent"] = data.get("weekly_sent", 0) + 1
            data["approved_queue"] = [
                x for x in data["approved_queue"]
                if not (x["thread_id"] == thread_id and x["message"] == message)
            ]
            st.save(data)
            print(f"  ✅ Sent! Total approved+sent: {data['total_sent']}/{cfg['auto_threshold']}")


async def process_inbox(browser: LinkedInBrowser, tg_app, cfg: dict) -> bool:
    data = st.load()
    pending_threads = {v["thread_id"] for v in data.get("pending_approvals", {}).values()}

    conversations = await browser.get_unread_conversations()
    if not conversations:
        print("  No unread conversations.")
        return False

    actioned = False
    log_path = cfg["client_dir"] / "conversations_log.json"

    for conv in conversations:
        thread_id = conv["thread_id"]
        name = conv["name"]

        if thread_id in pending_threads:
            print(f"  ⏳ {name} — already awaiting approval, skipping.")
            continue

        print(f"  📨 Reading conversation with {name}...")
        messages = await browser.get_conversation_messages(thread_id)

        if not messages:
            continue

        last = messages[-1]
        if last.get("is_media") and last["role"] == "user":
            print(f"  📎 {name} sent media we can't read — marking unread and notifying.")
            await browser.mark_as_unread(thread_id)
            await tg_app.bot.send_message(
                chat_id=cfg["telegram_chat_id"],
                text=(
                    f"🎖 *{cfg['agent_name']}*\n"
                    f"📎 *{name}* sent a photo, video or file that I can't read.\n"
                    f"I've marked the conversation as unread so you can handle it manually."
                ),
                parse_mode="Markdown"
            )
            continue

        if last["role"] == "assistant":
            print(f"  ↩️  {name} — last message is ours, nothing new to reply to.")
            continue

        profile_url = conv.get("profile_url")
        profile = await browser.get_profile_data(profile_url) if profile_url else {}
        profile["name"] = name

        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        log[thread_id] = {"name": name, "profile_url": profile_url or "", "messages": messages}
        log_path.write_text(json.dumps(log, indent=2))

        an.update_conversation(thread_id, name, messages, cfg.get("calendly_link", ""))

        print(f"  🤖 Generating reply for {name}...")
        reply = generate_reply(messages, profile, cfg)
        if not reply:
            print(f"  ⚠️  Could not generate reply for {name}.")
            continue

        data = st.load()
        total_sent = data.get("total_sent", 0)

        if total_sent >= cfg["auto_threshold"]:
            if is_duplicate(thread_id, reply):
                print(f"  ⛔ Duplicate detected for {name}, skipping.")
                continue
            print(f"  🚀 Auto-sending to {name}...")
            success = await browser.send_message(thread_id, reply)
            if success:
                record_sent(thread_id, reply)
                data = st.load()
                data["total_sent"] += 1
                data["weekly_sent"] = data.get("weekly_sent", 0) + 1
                st.save(data)
                print(f"  ✅ Auto-sent to {name}. Total: {data['total_sent']}")
                actioned = True
        else:
            their_last = next(
                (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
            )
            approval_id = uuid.uuid4().hex[:8]
            tg_msg_id = await send_approval(tg_app, approval_id, name, their_last, reply)

            data = st.load()
            data["pending_approvals"][approval_id] = {
                "thread_id": thread_id,
                "name": name,
                "their_message": their_last,
                "proposed_reply": reply,
                "tg_message_id": tg_msg_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            st.save(data)
            remaining = cfg["auto_threshold"] - total_sent
            print(f"  📱 Sent to Telegram for approval ({remaining} approvals left until auto-mode).")
            actioned = True

    return actioned


async def check_pending_reminders(tg_app, cfg: dict):
    data = st.load()
    pending = data.get("pending_approvals", {})
    now = datetime.now(timezone.utc)
    reminder_threshold = 3 * 3600

    for approval_id, approval in pending.items():
        created_at = approval.get("created_at")
        if not created_at:
            continue
        age = (now - datetime.fromisoformat(created_at)).total_seconds()
        last_reminded = approval.get("last_reminded")
        if last_reminded:
            time_since_reminder = (now - datetime.fromisoformat(last_reminded)).total_seconds()
        else:
            time_since_reminder = None

        if age >= reminder_threshold and (time_since_reminder is None or time_since_reminder >= reminder_threshold):
            name = approval.get("name", "someone")
            await tg_app.bot.send_message(
                chat_id=cfg["telegram_chat_id"],
                text=f"⏰ Reminder: you have a message waiting for approval for *{name}* that has been sitting for over 3 hours. Scroll up and tap Approve, Edit, or Skip.",
                parse_mode="Markdown",
            )
            data["pending_approvals"][approval_id]["last_reminded"] = now.isoformat()

    st.save(data)


async def main():
    client_name = get_client_name()
    cfg = cfg_module.load(client_name)
    client_dir = cfg["client_dir"]

    st.init(client_dir)
    ex.init(client_dir)
    an.init(client_dir)

    print(f"🚀 LinkedIn Appointment Setter — starting up ({client_name})...")

    tg_app = build_app(cfg)
    await tg_app.initialize()
    await tg_app.bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(2)
    await tg_app.start()
    await tg_app.updater.start_polling(drop_pending_updates=True)
    print("✅ Telegram bot running.")

    browser = LinkedInBrowser(client_dir)
    await browser.start()
    await browser.ensure_logged_in()
    print("✅ LinkedIn browser ready.\n")

    poll_interval = cfg["poll_interval"]
    print(f"🔄 Polling every {poll_interval}s. Running continuously.\n")

    browser_error_count = 0
    session_alert_sent = False

    try:
        while True:
            print("─── Tick ───────────────────────────────")

            if not await browser.is_alive():
                browser_error_count += 1
                print(f"  Browser closed (failure {browser_error_count}), restarting...")
                if browser_error_count >= 2:
                    await send_operator_alert(
                        f"⚠️ *{cfg['agent_name']}* ({cfg['client_name']})\n"
                        f"Browser has crashed {browser_error_count} times. Attempting restart."
                    )
                await browser.restart()
                browser_error_count = 0
            else:
                browser_error_count = 0

            if not await browser.is_logged_in():
                if not session_alert_sent:
                    print("  LinkedIn session expired, alerting operator and client...")
                    await send_operator_alert(
                        f"🔒 *{cfg['agent_name']}* ({cfg['client_name']})\n"
                        f"LinkedIn session has expired. The client needs to log back in.\n"
                        f"The agent is paused until they do."
                    )
                    await tg_app.bot.send_message(
                        chat_id=cfg["telegram_chat_id"],
                        text=(
                            f"🔒 *{cfg['agent_name']}*\n\n"
                            f"LinkedIn session has expired and the agent is paused.\n\n"
                            f"To resume:\n"
                            f"1. Open your Mac\n"
                            f"2. A Chrome browser window will open automatically\n"
                            f"3. Log back into LinkedIn in that window\n"
                            f"4. The agent resumes on its own once you are logged in"
                        ),
                        parse_mode="Markdown",
                    )
                    session_alert_sent = True
                print("  Skipping tick, waiting for LinkedIn login...")
                await asyncio.sleep(poll_interval)
                continue
            else:
                if session_alert_sent:
                    await send_operator_alert(
                        f"✅ *{cfg['agent_name']}* ({cfg['client_name']})\n"
                        f"LinkedIn session restored. Agent is running again."
                    )
                    await tg_app.bot.send_message(
                        chat_id=cfg["telegram_chat_id"],
                        text=f"✅ *{cfg['agent_name']}*\n\nLinkedIn session restored. Agent is running again.",
                        parse_mode="Markdown",
                    )
                session_alert_sent = False

            await flush_unread_queue(browser)
            await flush_approved_queue(browser, cfg)
            await process_inbox(browser, tg_app, cfg)
            await check_pending_reminders(tg_app, cfg)
            await send_weekly_report(tg_app, cfg)
            await send_heartbeat(cfg)

            print(f"Sleeping {poll_interval}s...\n")
            await asyncio.sleep(poll_interval)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n🛑 Shutting down...")
    finally:
        await browser.stop()
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        print("Bye.")


if __name__ == "__main__":
    asyncio.run(main())
