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
CUSTOM_ADDITIONS_FILE = Path("custom_additions.json")
MAX_HISTORY = 10
MAX_ADDITION_LENGTH = 2000

claude = Anthropic(api_key=ANTHROPIC_API_KEY)


def load_custom_additions() -> dict:
    if CUSTOM_ADDITIONS_FILE.exists():
        return json.loads(CUSTOM_ADDITIONS_FILE.read_text())
    return {"additions": [], "updated_at": ""}


def save_custom_additions(data: dict):
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    CUSTOM_ADDITIONS_FILE.write_text(json.dumps(data, indent=2))


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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"Hey! I'm your personalised LinkedIn agent support assistant.\n\n"
        f"*I can help you with:*\n"
        f"• Questions about your agent (is it running? how do I restart?)\n"
        f"• Terminal errors and logs (send a screenshot)\n"
        f"• Agent status and approvals\n"
        f"• Troubleshooting any issues\n\n"
        f"*Customize your agent:*\n"
        f"• /add_prompt [instruction] — Add custom instruction to your agent\n"
        f"• /view_prompt — See your custom additions\n"
        f"• /remove_prompt [number] — Remove a custom instruction\n\n"
        f"*Other commands:*\n"
        f"• /status — Check your live agent status\n\n"
        f"Just send me a message or screenshot and I'll answer to the best of my capabilities.\n\n"
        f"If something isn't working for a prolonged period of time, contact Savas."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await fetch_status()
    if status:
        await update.message.reply_text(status.strip())
    else:
        await update.message.reply_text("Could not fetch live status right now. Ask me any question and I will help.")


async def cmd_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage: /add_prompt [instruction to add to system prompt]")
        return

    if len(text) > MAX_ADDITION_LENGTH:
        await update.message.reply_text(f"Text is too long ({len(text)} chars). Max is {MAX_ADDITION_LENGTH} chars.")
        return

    msg = (
        f"Preview of what will be added to your system prompt:\n\n"
        f"\"{text}\"\n\n"
        f"Reply with ✅ to confirm or ❌ to cancel."
    )
    await update.message.reply_text(msg)
    context.user_data["pending_addition"] = text


async def cmd_view_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_custom_additions()
    if not data["additions"]:
        await update.message.reply_text("No custom additions to your system prompt yet.")
        return

    msg = "Your custom system prompt additions:\n\n"
    for i, add in enumerate(data["additions"], 1):
        msg += f"{i}. \"{add}\"\n\n"
    msg += "Use /remove_prompt [number] to remove one."
    await update.message.reply_text(msg)


async def cmd_remove_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /remove_prompt [number]\nUse /view_prompt to see the list.")
        return

    index = int(args[0]) - 1
    data = load_custom_additions()

    if index < 0 or index >= len(data["additions"]):
        await update.message.reply_text("Invalid number.")
        return

    removed = data["additions"].pop(index)
    save_custom_additions(data)
    await update.message.reply_text(f"Removed: \"{removed}\"\n\nRestart your agent for changes to take effect.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Handle confirmation of pending prompt addition
    if "pending_addition" in context.user_data:
        text = update.message.text.strip()
        if text == "✅":
            data = load_custom_additions()
            data["additions"].append(context.user_data["pending_addition"])
            save_custom_additions(data)
            await update.message.reply_text(
                f"✅ Added to system prompt!\n\n"
                f"Restart your agent for the change to take effect:\n\n"
                f"`launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.{CLIENT_NAME}.plist`\n"
                f"`sleep 2`\n"
                f"`launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.{CLIENT_NAME}.plist`"
            )
            del context.user_data["pending_addition"]
            return
        elif text == "❌":
            await update.message.reply_text("Cancelled.")
            del context.user_data["pending_addition"]
            return
        else:
            await update.message.reply_text("Please reply with ✅ to confirm or ❌ to cancel.")
            return

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
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("add_prompt", cmd_add_prompt))
    app.add_handler(CommandHandler("view_prompt", cmd_view_prompt))
    app.add_handler(CommandHandler("remove_prompt", cmd_remove_prompt))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    print(f"Support bot running for {CLIENT_NAME}...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
