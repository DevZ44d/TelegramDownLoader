from __future__ import annotations

from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from core.logger import logger
from services.pinterest import download_pinterest_media
from services.sender import send_media_items


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return
        logger.debug("Could not edit status message: %s", exc)


async def pinterest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status = await update.message.reply_text("🔎 Processing Pinterest link...")

    async def _progress(text: str) -> None:
        await _safe_edit(status, text)

    try:
        result = await download_pinterest_media(url, progress=_progress)

        if not result.success or not result.items:
            await _safe_edit(status, result.error or "❌ Download failed")
            return

        await _safe_edit(status, "📤 Uploading to Telegram...")

        await send_media_items(
            context=context,
            chat_id=update.effective_chat.id,
            items=result.items,
            reply_to=update.message.message_id,
        )

        try:
            await status.delete()
        except Exception:
            pass

    except Exception:
        logger.exception("Unhandled Pinterest error")
        try:
            await _safe_edit(status, "❌ Something went wrong processing that Pinterest link.")
        except Exception:
            pass