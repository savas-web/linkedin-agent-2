import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

SUPPORT_BOT_TOKEN = os.environ["SUPPORT_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "https://rooney-control-tower.up.railway.app")
DASHBOARD_API_KEY = os.environ.get("DASHBOARD_API_KEY", "rd-secret-2026")
CLIENT_NAME = os.environ.get("CLIENT_NAME", "")
DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "")

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.txt").read_text()
HISTORY_FILE = Path("history.json")
MAX_HISTORY = 10

claude = Anthropic(api_key=ANTHROPIC_API_KEY)


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {}


def save_history(data: dict):
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


async def fetch_status() -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{DASHBOARD_URL}/status",
                params={"token": DASHBOARD_TOKEN},
                headers={"x-api-key": DASHBOARD_API_KEY},
            )
            if r.status_code == 200:
                data = r.json()
                sent = data.get("total_sent", "?")
                pending = data.get("pending_approvals", "?")
                last_seen = data.get("last_seen", "")
                agent = data.get("agent_name", "your agent")
                age = ""
                if last_seen:
                    try:
                        dt = datetime.fromisoformat(last_seen)
                        mins = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
                        age = f", last active {mins} min ago"
                    except Exception:
                        pass
                return f"\n\n[Agent status for {agent}: {sent} messages sent, {pending} pending approvals{age}]"
    except Exception:
        pass
    return ""


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await fetch_status()
    if status:
        await update.message.reply_text(status.strip())
    else:
        await update.message.reply_text("Could not fetch live status right now. Ask me any question and I will help.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    history = load_history()
    user_history = history.get(user_id, [])

    # Build new message content
    content = []

    # Handle photo
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        img_bytes = await file.download_as_bytearray()
        b64 = base64.standard_b64encode(img_bytes).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}
        })
        caption = update.message.caption or ""
        if caption:
            content.append({"type": "text", "text": caption})
        else:
            content.append({"type": "text", "text": "What does this show? What should I do?"})
    elif update.message.text:
        content.append({"type": "text", "text": update.message.text})
    else:
        await update.message.reply_text("Please send text or a screenshot.")
        return

    # Build system with live status
    system = SYSTEM_PROMPT
    status = await fetch_status()
    if status:
        system += status

    # Append to history and call Claude
    user_history.append({"role": "user", "content": content})
    if len(user_history) > MAX_HISTORY * 2:
        user_history = user_history[-(MAX_HISTORY * 2):]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=user_history,
        )
        reply_text = response.content[0].text.strip()
    except Exception as e:
        reply_text = f"Sorry, I hit an error: {e}"

    user_history.append({"role": "assistant", "content": reply_text})
    history[user_id] = user_history
    save_history(history)

    # Send reply (split if too long)
    if len(reply_text) > 4000:
        for i in range(0, len(reply_text), 4000):
            await update.message.reply_text(reply_text[i:i+4000])
    else:
        await update.message.reply_text(reply_text)


def main():
    if not CLIENT_NAME or not DASHBOARD_TOKEN:
        print("ERROR: CLIENT_NAME and DASHBOARD_TOKEN environment variables are required")
        return

    app = ApplicationBuilder().token(SUPPORT_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    print(f"Support bot running for {CLIENT_NAME}...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
