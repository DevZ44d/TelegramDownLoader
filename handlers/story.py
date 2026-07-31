from __future__ import annotations

from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from core.logger import logger
from services.parser import LinkType, parse_link
from services.sender import send_media_items
from services.story import download_story


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return
        raise


async def story_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    parsed = parse_link(text)

    if parsed.link_type != LinkType.STORY:
        return

    status = await update.message.reply_text("⏳ Downloading story…")

    try:
        result = await download_story(parsed)

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
        logger.exception("Unhandled story error")
        try:
            await _safe_edit(status, f"❌ Error:\n{exc}")
        except Exception:
            pass