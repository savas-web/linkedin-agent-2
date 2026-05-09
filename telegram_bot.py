from datetime import datetime, timezone
import os
import signal
import state as st
import examples as ex
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.helpers import escape_markdown


def _esc(text: str) -> str:
    return escape_markdown(str(text), version=2)


def _allowed(update: Update, cfg: dict) -> bool:
    allowed = {cfg["telegram_chat_id"], cfg.get("billing_chat_id")}
    return update.effective_chat.id in allowed


def build_app(cfg: dict) -> Application:
    app = Application.builder().token(cfg["telegram_bot_token"]).build()
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.bot_data["cfg"] = cfg
    return app


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    if not _allowed(update, cfg):
        return
    data = st.load()
    pending = len(data.get("pending_approvals", {}))
    total = data.get("total_sent", 0)
    names = [v["name"] for v in data.get("pending_approvals", {}).values()]
    pending_str = "\n".join(f"  • {n}" for n in names) if names else "  None"
    await update.message.reply_text(
        f"🎖 *{cfg['agent_name']} Status*\n\n"
        f"Total sent: *{total}*\n"
        f"Pending approvals: *{pending}*\n{pending_str}",
        parse_mode="MarkdownV2",
    )


async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    if not _allowed(update, cfg):
        return
    await update.message.reply_text("🔄 Restarting agent, back in ~30 seconds...")
    os.kill(os.getpid(), signal.SIGTERM)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    if not _allowed(update, cfg):
        return
    await update.message.reply_text("🛑 Stopping agent. Send /restart from the Mac to start it again.")
    client_name = cfg["client_name"]
    plist = os.path.expanduser(f"~/Library/LaunchAgents/digital.rooney.{client_name}.plist")
    os.system(f"launchctl unload {plist}")


def _approval_keyboard(approval_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{approval_id}"),
        InlineKeyboardButton("✏️ Edit",    callback_data=f"edit:{approval_id}"),
        InlineKeyboardButton("⏭️ Skip",    callback_data=f"skip:{approval_id}"),
    ]])


async def send_approval(app: Application, approval_id: str, name: str, their_msg: str, draft: str) -> int:
    cfg = app.bot_data["cfg"]
    text = (
        f"🎖 *{_esc(cfg['agent_name'])}*\n"
        f"📩 *New LinkedIn DM*\n"
        f"From: *{_esc(name)}*\n\n"
        f"*Their message:*\n{_esc(their_msg)}\n\n"
        f"*Proposed reply:*\n{_esc(draft)}"
    )
    msg = await app.bot.send_message(
        chat_id=cfg["telegram_chat_id"],
        text=text,
        parse_mode="MarkdownV2",
        reply_markup=_approval_keyboard(approval_id),
    )
    return msg.message_id


def _approval_text(item: dict, agent_name: str) -> str:
    return (
        f"🎖 *{_esc(agent_name)}*\n"
        f"📩 *New LinkedIn DM*\n"
        f"From: *{_esc(item['name'])}*\n\n"
        f"*Their message:*\n{_esc(item['their_message'])}\n\n"
        f"*Proposed reply:*\n{_esc(item['proposed_reply'])}"
    )


def _sent_text(item: dict, agent_name: str) -> str:
    return (
        f"🎖 *{_esc(agent_name)}*\n"
        f"📩 *LinkedIn DM*\n"
        f"From: *{_esc(item['name'])}*\n\n"
        f"*Their message:*\n{_esc(item['their_message'])}\n\n"
        f"*Reply sent:*\n{_esc(item['proposed_reply'])}"
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, approval_id = query.data.split(":", 1)
    data = st.load()
    pending = data.get("pending_approvals", {})
    cfg = context.bot_data["cfg"]
    agent_name = cfg["agent_name"]

    if approval_id not in pending:
        await query.edit_message_text("⚠️ Already handled.")
        return

    item = pending[approval_id]

    if action == "approve":
        data["approved_queue"].append({
            "thread_id": item["thread_id"],
            "message": item["proposed_reply"],
            "approved_at": datetime.now(timezone.utc).isoformat()
        })
        del data["pending_approvals"][approval_id]
        st.save(data)
        await query.edit_message_text(
            _sent_text(item, agent_name) + "\n\n✅ *Approved*",
            parse_mode="MarkdownV2"
        )

    elif action == "edit":
        data["awaiting_edit"] = approval_id
        st.save(data)
        cancel_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{approval_id}"),
        ]])
        await query.edit_message_text(
            _approval_text(item, agent_name) + "\n\n✏️ *Type your edited reply in this chat:*",
            parse_mode="MarkdownV2",
            reply_markup=cancel_keyboard,
        )

    elif action == "skip":
        data.setdefault("mark_unread_queue", []).append(item["thread_id"])
        del data["pending_approvals"][approval_id]
        st.save(data)
        await query.edit_message_text(
            _sent_text(item, agent_name) + "\n\n⏭️ *Skipped — marked as unread*",
            parse_mode="MarkdownV2"
        )

    elif action == "cancel":
        data["awaiting_edit"] = None
        st.save(data)
        await query.edit_message_text(
            _approval_text(item, agent_name),
            parse_mode="MarkdownV2",
            reply_markup=_approval_keyboard(approval_id)
        )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    if update.effective_chat.id != cfg["telegram_chat_id"]:
        return

    data = st.load()
    awaiting = data.get("awaiting_edit")
    if not awaiting:
        return

    pending = data.get("pending_approvals", {})
    if awaiting not in pending:
        data["awaiting_edit"] = None
        st.save(data)
        return

    item = pending[awaiting]
    edited = update.message.text.strip()

    if edited.lower() == "/cancel":
        data["awaiting_edit"] = None
        st.save(data)
        await update.message.reply_text(
            "❌ Edit cancelled.",
            parse_mode="MarkdownV2"
        )
        return

    data["approved_queue"].append({
        "thread_id": item["thread_id"],
        "message": edited,
        "approved_at": datetime.now(timezone.utc).isoformat()
    })
    del data["pending_approvals"][awaiting]
    data["awaiting_edit"] = None
    st.save(data)

    ex.save_edit(
        their_message=item["their_message"],
        ai_draft=item["proposed_reply"],
        max_sent=edited
    )

    await update.message.reply_text(
        f"✅ Edited reply queued for *{item['name']}*! 🧠 Saved as learning example.",
        parse_mode="MarkdownV2"
    )
