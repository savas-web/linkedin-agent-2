from datetime import datetime, timezone
import state as st
import examples as ex
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes


def build_app(cfg: dict) -> Application:
    app = Application.builder().token(cfg["telegram_bot_token"]).build()
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.bot_data["cfg"] = cfg
    return app


def _approval_keyboard(approval_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{approval_id}"),
        InlineKeyboardButton("✏️ Edit",    callback_data=f"edit:{approval_id}"),
        InlineKeyboardButton("⏭️ Skip",    callback_data=f"skip:{approval_id}"),
    ]])


async def send_approval(app: Application, approval_id: str, name: str, their_msg: str, draft: str) -> int:
    cfg = app.bot_data["cfg"]
    text = (
        f"🎖 *{cfg['agent_name']}*\n"
        f"📩 *New LinkedIn DM*\n"
        f"From: *{name}*\n\n"
        f"*Their message:*\n{their_msg}\n\n"
        f"*Proposed reply:*\n{draft}"
    )
    msg = await app.bot.send_message(
        chat_id=cfg["telegram_chat_id"],
        text=text,
        parse_mode="Markdown",
        reply_markup=_approval_keyboard(approval_id),
    )
    return msg.message_id


def _approval_text(item: dict, agent_name: str) -> str:
    return (
        f"🎖 *{agent_name}*\n"
        f"📩 *New LinkedIn DM*\n"
        f"From: *{item['name']}*\n\n"
        f"*Their message:*\n{item['their_message']}\n\n"
        f"*Proposed reply:*\n{item['proposed_reply']}"
    )


def _sent_text(item: dict, agent_name: str) -> str:
    return (
        f"🎖 *{agent_name}*\n"
        f"📩 *LinkedIn DM*\n"
        f"From: *{item['name']}*\n\n"
        f"*Their message:*\n{item['their_message']}\n\n"
        f"*Reply sent:*\n{item['proposed_reply']}"
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
            parse_mode="Markdown"
        )

    elif action == "edit":
        data["awaiting_edit"] = approval_id
        st.save(data)
        await query.edit_message_text(
            f"✏️ Type your edited reply for *{item['name']}*\.\n\nSend /cancel to go back\.",
            parse_mode="MarkdownV2"
        )

    elif action == "skip":
        data.setdefault("mark_unread_queue", []).append(item["thread_id"])
        del data["pending_approvals"][approval_id]
        st.save(data)
        await query.edit_message_text(
            _sent_text(item, agent_name) + "\n\n⏭️ *Skipped — marked as unread*",
            parse_mode="Markdown"
        )

    elif action == "cancel":
        data["awaiting_edit"] = None
        st.save(data)
        await query.edit_message_text(
            _approval_text(item, agent_name),
            parse_mode="Markdown",
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
            parse_mode="Markdown"
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
        parse_mode="Markdown"
    )
