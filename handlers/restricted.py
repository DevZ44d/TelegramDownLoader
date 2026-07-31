from __future__ import annotations

from telegram import Message, Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from core.logger import logger
from services.parser import LinkType, parse_link
from services.restricted import download_post
from services.sender import send_media_items
from utils.regex import is_private_invite


async def _safe_edit(message: Message, text: str) -> None:
    """Edit message text, ignore 'not modified' errors."""
    try:
        await message.edit_text(text)
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return
        raise


async def restricted_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if is_private_invite(text):
        await update.message.reply_text(
            "🔒 Private invite links are not supported.\n"
            "Use a direct post link if the account has access.",
        )
        return

    parsed = parse_link(text)

    if parsed.link_type != LinkType.PUBLIC_POST:
        await update.message.reply_text(
            "❌ Unsupported link. Send a Story or channel post link.",
        )
        return

    status = await update.message.reply_text("⏳ Fetching…")

    try:
        # Fast path: copy without re-uploading
        copied = await _try_fast_copy(context, parsed, update)
        if copied:
            try:
                await status.delete()
            except Exception:
                pass
            return

        # Slow path: download via Telethon + re-upload
        await _safe_edit(status, "⏳ Restricted content — downloading…")
        result = await download_post(parsed)

        if not result.success or not result.items:
            await _safe_edit(status, f"❌ {result.error or 'Download failed'}")
            return

        try:
            await status.delete()
        except Exception:
            pass

        await send_media_items(
            context=context,
            chat_id=update.effective_chat.id,
            items=result.items,
            reply_to=update.message.message_id,
        )
    except Exception as exc:
        logger.exception("Unhandled restricted error")
        try:
            await _safe_edit(status, f"❌ Error:\n{exc}")
        except Exception:
            pass


async def _try_fast_copy(
    context: ContextTypes.DEFAULT_TYPE,
    parsed,
    update: Update,
) -> bool:
    """
    Try to copy messages with the bot (instant, no bandwidth).
    Returns True if at least one message was copied successfully.
    """
    if not parsed.peer or parsed.message_id is None:
        return False

    from_id = parsed.message_id
    to_id = parsed.to_message_id or from_id
    if to_id < from_id:
        from_id, to_id = to_id, from_id

    if to_id - from_id > 30:
        return False

    from handlers.start import build_back_keyboard

    chat_id = update.effective_chat.id
    reply_to = update.message.message_id
    back_kb = build_back_keyboard()
    success = 0
    ids = list(range(from_id, to_id + 1))

    for i, msg_id in enumerate(ids):
        is_last = i == len(ids) - 1
        try:
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=parsed.peer,
                message_id=msg_id,
                reply_to_message_id=reply_to if success == 0 else None,
                reply_markup=back_kb if is_last else None,
                read_timeout=30,
                write_timeout=30,
            )
            success += 1
        except TelegramError as exc:
            logger.debug("copy_message failed for %s/%s: %s", parsed.peer, msg_id, exc)
            if success == 0:
                return False
            continue

    return success > 0