import state as st
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AGENT_NAME


def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app


async def send_approval(app: Application, approval_id: str, name: str, their_msg: str, draft: str) -> int:
    text = (
        f"🎖 *{AGENT_NAME}*\n"
        f"📩 *New LinkedIn DM*\n"
        f"From: *{name}*\n\n"
        f"*Their message:*\n{their_msg}\n\n"
        f"*Proposed reply:*\n{draft}"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{approval_id}"),
        InlineKeyboardButton("✏️ Edit",    callback_data=f"edit:{approval_id}"),
        InlineKeyboardButton("⏭️ Skip",    callback_data=f"skip:{approval_id}"),
    ]])
    msg = await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return msg.message_id


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, approval_id = query.data.split(":", 1)
    data = st.load()
    pending = data.get("pending_approvals", {})

    if approval_id not in pending:
        await query.edit_message_text("⚠️ Already handled.")
        return

    item = pending[approval_id]

    if action == "approve":
        data["approved_queue"].append({"thread_id": item["thread_id"], "message": item["proposed_reply"]})
        del data["pending_approvals"][approval_id]
        st.save(data)
        await query.edit_message_text(f"✅ Approved — queued for *{item['name']}*", parse_mode="Markdown")

    elif action == "edit":
        data["awaiting_edit"] = approval_id
        st.save(data)
        await query.edit_message_text(
            f"✏️ Type your edited reply for *{item['name']}*:", parse_mode="Markdown"
        )

    elif action == "skip":
        del data["pending_approvals"][approval_id]
        st.save(data)
        await query.edit_message_text(f"⏭️ Skipped *{item['name']}*", parse_mode="Markdown")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != TELEGRAM_CHAT_ID:
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

    data["approved_queue"].append({"thread_id": item["thread_id"], "message": edited})
    del data["pending_approvals"][awaiting]
    data["awaiting_edit"] = None
    st.save(data)

    await update.message.reply_text(f"✅ Edited reply queued for *{item['name']}*!", parse_mode="Markdown")
