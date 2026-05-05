import asyncio
import sys
import uuid

from linkedin_browser import LinkedInBrowser
from claude_agent import generate_reply
from telegram_bot import build_app, send_approval
import state as st
from config import POLL_INTERVAL, AUTO_THRESHOLD

IDLE_STOP_AFTER = 3  # stop after this many consecutive empty polls


async def flush_approved_queue(browser: LinkedInBrowser):
    data = st.load()
    queue = list(data.get("approved_queue", []))
    if not queue:
        return

    for item in queue:
        thread_id = item["thread_id"]
        message = item["message"]
        print(f"  → Sending approved reply to thread {thread_id}...")
        success = await browser.send_message(thread_id, message)
        if success:
            data = st.load()
            data["total_sent"] += 1
            data["approved_queue"] = [
                x for x in data["approved_queue"]
                if not (x["thread_id"] == thread_id and x["message"] == message)
            ]
            st.save(data)
            print(f"  ✅ Sent! Total approved+sent: {data['total_sent']}/{AUTO_THRESHOLD}")


async def process_inbox(browser: LinkedInBrowser, tg_app) -> bool:
    """Returns True if any new messages were found and actioned."""
    data = st.load()
    pending_threads = {v["thread_id"] for v in data.get("pending_approvals", {}).values()}

    conversations = await browser.get_unread_conversations()
    if not conversations:
        print("  No unread conversations.")
        return False

    actioned = False

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

        if messages[-1]["role"] == "assistant":
            print(f"  ↩️  {name} — last message is ours, nothing new to reply to.")
            continue

        profile_url = conv.get("profile_url")
        profile = await browser.get_profile_data(profile_url) if profile_url else {}

        print(f"  🤖 Generating reply for {name}...")
        reply = generate_reply(messages, profile)
        if not reply:
            print(f"  ⚠️  Could not generate reply for {name}.")
            continue

        data = st.load()
        total_sent = data.get("total_sent", 0)

        if total_sent >= AUTO_THRESHOLD:
            print(f"  🚀 Auto-sending to {name}...")
            success = await browser.send_message(thread_id, reply)
            if success:
                data = st.load()
                data["total_sent"] += 1
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
            }
            st.save(data)
            remaining = AUTO_THRESHOLD - total_sent
            print(f"  📱 Sent to Telegram for approval ({remaining} approvals left until auto-mode).")
            actioned = True

    return actioned


async def main():
    print("🚀 LinkedIn Appointment Setter — starting up...")

    tg_app = build_app()
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(drop_pending_updates=True)
    print("✅ Telegram bot running.")

    browser = LinkedInBrowser()
    await browser.start()
    await browser.ensure_logged_in()
    print("✅ LinkedIn browser ready.\n")

    print(f"🔄 Polling every {POLL_INTERVAL}s. Auto-mode after {AUTO_THRESHOLD} sent. Stops after {IDLE_STOP_AFTER} empty polls.\n")

    idle_count = 0

    try:
        while True:
            print("─── Tick ───────────────────────────────")
            await flush_approved_queue(browser)
            found = await process_inbox(browser, tg_app)

            if found:
                idle_count = 0
            else:
                idle_count += 1
                print(f"  Idle poll {idle_count}/{IDLE_STOP_AFTER}")
                if idle_count >= IDLE_STOP_AFTER:
                    print("\n💤 No activity for 3 polls — shutting down automatically.")
                    break

            print(f"Sleeping {POLL_INTERVAL}s...\n")
            await asyncio.sleep(POLL_INTERVAL)
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
