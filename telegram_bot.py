from datetime import datetime, timezone
import os
import signal
import uuid
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
    app.add_handler(CommandHandler("demo", cmd_demo))
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


async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cfg = context.bot_data["cfg"]
        if not _allowed(update, cfg):
            await update.message.reply_text("Not allowed.")
            return
        approval_id = f"demo_{uuid.uuid4().hex[:6]}"
        their_msg = "I know what I need to do but I just cannot seem to actually do it. Does your coaching help with that?"
        draft = "That is literally the gap most people are stuck in and it is exactly what we work on. Would you be open to a quick 20 minutes just to see if there is anything useful for where you are right now?"
        data = st.load()
        data.setdefault("pending_approvals", {})[approval_id] = {
            "thread_id": "demo_thread",
            "name": "Sarah Mitchell",
            "their_message": their_msg,
            "proposed_reply": draft,
            "is_followup": False,
            "is_demo": True,
        }
        st.save(data)
        text = (
            f"DEMO\n"
            f"New LinkedIn DM\n"
            f"From: Sarah Mitchell\n\n"
            f"Their message:\n{their_msg}\n\n"
            f"Proposed reply:\n{draft}"
        )
        msg = await update.message.reply_text(text, reply_markup=_approval_keyboard(approval_id))
        data2 = st.load()
        data2["pending_approvals"][approval_id]["tg_message_id"] = msg.message_id
        st.save(data2)
    except Exception as e:
        await update.message.reply_text(f"Demo error: {e}")


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


async def send_followup_approval(app: Application, approval_id: str, name: str, last_sent: str, draft: str) -> int:
    cfg = app.bot_data["cfg"]
    text = (
        f"🎖 *{_esc(cfg['agent_name'])}*\n"
        f"🔁 *Follow\\-up*\n"
        f"For: *{_esc(name)}*\n\n"
        f"*Our last message:*\n{_esc(last_sent)}\n\n"
        f"*Proposed follow\\-up:*\n{_esc(draft)}"
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
    if item.get("is_followup"):
        return (
            f"🎖 *{_esc(agent_name)}*\n"
            f"🔁 *Follow\\-up*\n"
            f"For: *{_esc(item['name'])}*\n\n"
            f"*Our last message:*\n{_esc(item['their_message'])}\n\n"
            f"*Follow\\-up sent:*\n{_esc(item['proposed_reply'])}"
        )
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
        if item.get("is_demo"):
            del data["pending_approvals"][approval_id]
            st.save(data)
            await query.edit_message_text(
                f"DEMO\nFrom: {item['name']}\n\nReply that would be sent:\n{item['proposed_reply']}\n\nApproved (nothing actually sent)"
            )
            return
        data["approved_queue"].append({
            "thread_id": item["thread_id"],
            "message": item["proposed_reply"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "is_followup": item.get("is_followup", False),
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
        if not item.get("is_followup"):
            data.setdefault("mark_unread_queue", []).append(item["thread_id"])
        del data["pending_approvals"][approval_id]
        st.save(data)
        label = "⏭️ *Follow\\-up skipped*" if item.get("is_followup") else "⏭️ *Skipped — marked as unread*"
        await query.edit_message_text(
            _sent_text(item, agent_name) + f"\n\n{label}",
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
        await update.message.reply_text("❌ Edit cancelled.")
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

    # edit the original approval message to remove the Cancel button
    tg_msg_id = item.get("tg_message_id")
    agent_name = cfg["agent_name"]
    edited_item = {**item, "proposed_reply": edited}
    if tg_msg_id:
        try:
            await context.bot.edit_message_text(
                chat_id=cfg["telegram_chat_id"],
                message_id=tg_msg_id,
                text=_sent_text(edited_item, agent_name) + "\n\n✅ *Sent \\(edited\\)*",
                parse_mode="MarkdownV2",
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ Edited reply queued for *{_esc(item['name'])}*\\! 🧠 Saved as learning example\\.",
        parse_mode="MarkdownV2"
    )
