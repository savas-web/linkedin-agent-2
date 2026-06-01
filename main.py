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

# Load .env as fallback for any vars not already in the environment (e.g. when plist was installed without them)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            if _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip()

import config as cfg_module
import state as st
import examples as ex
import analytics as an
from linkedin_browser import LinkedInBrowser
from claude_agent import generate_reply, generate_followup, should_followup

NOTION_TOKEN   = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_ID   = "333075d6-4265-80ff-9696-e53f14238595"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def create_notion_lead(name: str, linkedin_url: str, sent_at: str):
    if not NOTION_TOKEN:
        return
    try:
        payload = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Lead Name": {"title": [{"text": {"content": name}}]},
                "LinkedIN ": {"url": linkedin_url or None},
                "Status": {"status": {"name": "Loom/link/vn sent"}},
                "LAST FOLLOW UP DATE": {"date": {"start": sent_at[:10]}},
            },
        }
        r = httpx.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"  📋 Notion lead created for {name}")
        else:
            print(f"  ⚠️ Notion lead failed ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Notion lead error: {e}")
from telegram_bot import build_app, send_approval, send_followup_approval
import json


DASHBOARD_URL = os.environ.get("DASHBOARD_URL") or "https://rooney-control-tower.up.railway.app"
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY") or "rd-secret-2026"
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
        if messages and messages[-1]["role"] == "assistant" and not item.get("is_followup"):
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
            an.record_agent_sent(thread_id)
            data = st.load()
            data["total_sent"] += 1
            data["weekly_sent"] = data.get("weekly_sent", 0) + 1
            data["approved_queue"] = [
                x for x in data["approved_queue"]
                if not (x["thread_id"] == thread_id and x["message"] == message)
            ]
            st.save(data)
            print(f"  ✅ Sent! Total approved+sent: {data['total_sent']}/{cfg['auto_threshold']}")

            # if the message contains the Calendly link, create a Notion lead
            calendly_link = cfg.get("calendly_link", "")
            if calendly_link and calendly_link in message:
                conv = an.load().get(thread_id, {})
                create_notion_lead(
                    name=conv.get("name", item.get("name", "Unknown")),
                    linkedin_url=conv.get("profile_url", ""),
                    sent_at=datetime.now(timezone.utc).isoformat(),
                )


async def process_inbox(browser: LinkedInBrowser, tg_app, cfg: dict) -> bool:
    data = st.load()
    pending_threads = {v["thread_id"] for v in data.get("pending_approvals", {}).values()}
    pending_threads |= {v["thread_id"] for v in data.get("approved_queue", [])}

    conversations = await browser.get_unread_conversations()
    if not conversations:
        print("  No conversations found.")
        return False

    actioned = False
    log_path = cfg["client_dir"] / "conversations_log.json"

    for conv in conversations:
        thread_id = conv["thread_id"]
        name = conv["name"]

        if thread_id in pending_threads:
            print(f"  ⏳ {name} — already awaiting approval, skipping.")
            continue

        if an.was_recently_checked(thread_id):
            print(f"  ⏭️  {name} — checked recently, skipping.")
            continue

        print(f"  📨 Reading conversation with {name}...")
        messages = await browser.get_conversation_messages(thread_id)

        if not messages:
            continue

        last = messages[-1]

        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if an.is_dismissed(thread_id, last_user_msg):
            print(f"  🚫 {name} — dismissed (no new message), skipping.")
            continue
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
            an.record_checked(thread_id)
            continue

        profile_url = conv.get("profile_url")
        profile = await browser.get_profile_data(profile_url) if profile_url else {}
        profile["name"] = name

        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        log[thread_id] = {"name": name, "profile_url": profile_url or "", "messages": messages}
        log_path.write_text(json.dumps(log, indent=2))

        an.update_conversation(thread_id, name, messages, cfg.get("calendly_link", ""), profile=profile)

        print(f"  🤖 Generating reply for {name}...")
        try:
            reply = generate_reply(messages, profile, cfg)
        except Exception as api_err:
            print(f"  ⚠️  Claude API error for {name}, skipping: {api_err}")
            await browser.mark_as_unread(thread_id)
            continue
        if not reply:
            print(f"  ⚠️  Could not generate reply for {name}.")
            await browser.mark_as_unread(thread_id)
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


async def check_followups(browser: LinkedInBrowser, tg_app, cfg: dict):
    max_fu = cfg.get("max_follow_ups", 2)
    fu_days = cfg.get("follow_up_days", 3)

    candidates = an.get_followup_candidates(max_fu, fu_days)
    if not candidates:
        return
    candidates = candidates[:3]

    data = st.load()
    pending_threads = {v["thread_id"] for v in data.get("pending_approvals", {}).values()}

    for candidate in candidates:
        thread_id = candidate["thread_id"]
        name = candidate["name"]
        if thread_id in pending_threads:
            continue

        print(f"  🔁 Follow-up candidate: {name}")
        try:
            # Stabilise browser before navigating to the thread
            await browser.page.goto("about:blank", timeout=8_000)
            messages = await browser.get_conversation_messages(thread_id)
        except Exception as e:
            print(f"  ⚠️  Could not read thread for {name}: {e}")
            alive = await browser.is_alive()
            print(f"  ⛔ Dismissing {name} permanently {'(browser crashed)' if not alive else '(thread unreadable)'}.")
            an.mark_dismissed(thread_id)
            if not alive:
                await browser.restart()
            continue
        if not messages or messages[-1]["role"] == "user":
            continue

        if not should_followup(messages, cfg):
            print(f"  ⛔ {name} — conversation closed/dismissed, skipping permanently.")
            an.mark_dismissed(thread_id)
            continue

        profile = candidate.get("profile", {}) or {}
        if not profile.get("recent_posts"):
            try:
                profile_url = await browser.get_profile_url_from_conversation()
                if profile_url:
                    posts = await browser.get_recent_posts(profile_url)
                    if posts:
                        profile["recent_posts"] = posts
                        profile["profile_url"] = profile_url
            except Exception:
                pass
        profile["name"] = name
        last_sent = messages[-1]["content"]
        reply = generate_followup(messages, name, cfg=cfg, profile=profile)
        if not reply:
            continue

        approval_id = uuid.uuid4().hex[:8]
        tg_msg_id = await send_followup_approval(tg_app, approval_id, name, last_sent, reply)

        data = st.load()
        data["pending_approvals"][approval_id] = {
            "thread_id": thread_id,
            "name": name,
            "their_message": last_sent,
            "proposed_reply": reply,
            "tg_message_id": tg_msg_id,
            "is_followup": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        st.save(data)
        an.record_followup(thread_id)
        print(f"  ✅ Follow-up queued for {name}")


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

        if age >= reminder_threshold and last_reminded is None:
            name = approval.get("name", "someone")
            await tg_app.bot.send_message(
                chat_id=cfg["telegram_chat_id"],
                text=f"⏰ Reminder: you have a message waiting for approval for *{name}* that has been sitting for over 3 hours. Scroll up and tap Approve, Edit, or Skip.",
                parse_mode="Markdown",
            )
            data["pending_approvals"][approval_id]["last_reminded"] = now.isoformat()

    st.save(data)


async def main():
    # Register SIGTERM via asyncio's safe mechanism (runs inside the event loop,
    # not in a raw OS signal handler). Raw signal.signal() callbacks that call
    # print/traceback are async-signal-unsafe and corrupt the kqueue selector
    # in Python 3.14. This cancels the main task cleanly instead.
    import signal as _sig
    _main_task = asyncio.current_task()
    asyncio.get_running_loop().add_signal_handler(
        _sig.SIGTERM, lambda: _main_task.cancel("SIGTERM")
    )

    client_name = get_client_name()
    cfg = cfg_module.load(client_name)
    client_dir = cfg["client_dir"]

    st.init(client_dir)
    ex.init(client_dir)
    an.init(client_dir)
    an.backfill_agent_sent()

    print(f"🚀 LinkedIn Appointment Setter — starting up ({client_name})...")

    tg_app = build_app(cfg)
    await tg_app.initialize()
    await tg_app.bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(2)
    await tg_app.start()
    for attempt in range(5):
        try:
            await tg_app.updater.start_polling(drop_pending_updates=True)
            break
        except Exception as e:
            if "Conflict" in str(e) and attempt < 4:
                print(f"Telegram conflict, retrying in 10s (attempt {attempt+1}/5)...")
                await asyncio.sleep(10)
            else:
                raise
    print("✅ Telegram bot running.")

    headless = cfg.get("headless", True)
    poll_interval = cfg["poll_interval"]
    print(f"🔄 Polling every {poll_interval}s. Running continuously.\n")

    # One browser object for the lifetime of the process.
    # Playwright subprocess stays alive; only the browser CONTEXT is opened
    # and closed per tick so no Chromium runs during the sleep gap.
    browser = LinkedInBrowser(client_dir, headless=headless)
    await browser.start()  # starts Playwright subprocess only

    session_alert_sent = False

    try:
        while True:
            print("─── Tick ───────────────────────────────")
            tick_start = asyncio.get_event_loop().time()

            if cfg.get("weekdays_only") and datetime.now().weekday() >= 5:
                print("  Weekend — skipping tick (weekdays_only)")
                await asyncio.sleep(poll_interval)
                continue

            # Open a fresh browser context for this tick
            try:
                await browser.start()  # reuses playwright, opens new context
            except Exception as e:
                print(f"  ⚠️  Browser context failed to start: {e}")
                await asyncio.sleep(30)
                continue

            logged_in = await browser.is_logged_in()
            if not logged_in:
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
                print("  Session expired — opening visible browser so client can log in...")
                await browser.stop()
                login_browser = LinkedInBrowser(client_dir, headless=False)
                await login_browser.start()
                logged_in_now = False
                for _ in range(60):  # wait up to 10 minutes
                    try:
                        logged_in_now = await login_browser.is_logged_in()
                    except Exception:
                        pass
                    if logged_in_now:
                        break
                    await asyncio.sleep(10)
                await login_browser.stop()
                if logged_in_now:
                    print("  Login detected! Resuming normal operation...")
                    session_alert_sent = False
                else:
                    print("  Login timed out after 10 minutes, will retry next tick...")
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

            _sd_file = Path(__file__).parent / "shutdown_dates.json"
            _sd_map = json.loads(_sd_file.read_text()) if _sd_file.exists() else {}
            shutdown_date = _sd_map.get(cfg["client_name"]) or cfg.get("shutdown_date")
            if shutdown_date and datetime.now(ZoneInfo("Europe/Amsterdam")).date() >= datetime.fromisoformat(shutdown_date).date():
                print(f"  🛑 Shutdown date {shutdown_date} reached. Stopping agent.")
                await tg_app.bot.send_message(
                    chat_id=cfg["telegram_chat_id"],
                    text=f"🛑 *{cfg['agent_name']}*\n\nYour subscription has ended and the agent has been stopped. Thank you for using Rooney Digital!",
                    parse_mode="Markdown",
                )
                client_name = cfg["client_name"]
                plist = os.path.expanduser(f"~/Library/LaunchAgents/digital.rooney.{client_name}.plist")
                os.system(f"launchctl unload {plist}")
                break

            try:
                await flush_unread_queue(browser)
                await flush_approved_queue(browser, cfg)
                await process_inbox(browser, tg_app, cfg)
                await check_followups(browser, tg_app, cfg)
                await check_pending_reminders(tg_app, cfg)
                await send_weekly_report(tg_app, cfg)
                await send_heartbeat(cfg)
            except Exception as e:
                print(f"  ⚠️  Tick error (recovering): {e}")
            finally:
                # Close browser context before sleeping unless keep_browser_open is set
                if not cfg.get("keep_browser_open"):
                    try:
                        await browser.stop_context()
                    except Exception:
                        pass

            elapsed = asyncio.get_event_loop().time() - tick_start
            remaining = max(10, poll_interval - elapsed)
            print(f"Sleeping {int(remaining)}s...\n")
            await asyncio.sleep(remaining)
    except KeyboardInterrupt:
        print("\n🛑 KeyboardInterrupt — shutting down...")
    except asyncio.CancelledError:
        import traceback
        print(f"\n🛑 CancelledError — shutting down (traceback below):")
        traceback.print_exc()
    except Exception as e:
        import traceback
        print(f"\n💀 FATAL: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        try:
            await browser.stop()
        except Exception:
            pass
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        print("Bye.")


if __name__ == "__main__":
    asyncio.run(main())
