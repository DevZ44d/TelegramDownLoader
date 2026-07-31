from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from telegram.ext import ContextTypes

from core.logger import logger
from handlers.start import build_back_keyboard
from models.media import MediaItem, MediaType
from utils.files import safe_remove
from utils.helpers import truncate


async def send_media_items(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    items: Sequence[MediaItem],
    reply_to: Optional[int] = None,
    caption: Optional[str] = None,
) -> None:
    if not items:
        return

    final_caption = caption
    if not final_caption:
        for it in items:
            if it.caption:
                final_caption = truncate(it.caption, 1024)
                break

    back_kb = build_back_keyboard()

    for idx, item in enumerate(items):
        path = item.file_path
        is_last = idx == len(items) - 1
        cap = final_caption if is_last else None
        # Attach Back only on the last item so the keyboard sits under the final media
        markup = back_kb if is_last else None

        if path is None and item.caption:
            await context.bot.send_message(
                chat_id=chat_id,
                text=item.caption,
                reply_to_message_id=reply_to,
                reply_markup=markup,
            )
            continue

        if not path or not Path(path).exists():
            logger.warning("Skipping missing file for %s", item.media_type)
            continue

        try:
            await _send_one(context, chat_id, item, path, reply_to, cap, markup)
        except Exception as exc:
            logger.exception("Failed to send media")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Failed to send file: {exc}",
                reply_to_message_id=reply_to,
                reply_markup=markup if is_last else None,
            )
        finally:
            safe_remove(path)


async def _send_one(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    item: MediaItem,
    path: Path,
    reply_to: Optional[int],
    caption: Optional[str],
    reply_markup=None,
) -> None:
    kwargs: dict = {
        "chat_id": chat_id,
        "reply_to_message_id": reply_to,
        "read_timeout": 120,
        "write_timeout": 120,
        "connect_timeout": 30,
        "pool_timeout": 30,
    }
    if caption:
        kwargs["caption"] = caption
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup

    mt = item.media_type
    file_path = str(path)

    if mt in (MediaType.PHOTO, MediaType.STORY_PHOTO):
        await context.bot.send_photo(photo=file_path, **kwargs)
    elif mt in (MediaType.VIDEO, MediaType.STORY_VIDEO, MediaType.ANIMATION):
        await context.bot.send_video(
            video=file_path, supports_streaming=True, **kwargs
        )
    elif mt == MediaType.VOICE:
        await context.bot.send_voice(voice=file_path, **kwargs)
    elif mt == MediaType.AUDIO:
        await context.bot.send_audio(audio=file_path, **kwargs)
    elif mt == MediaType.STICKER:
        # Stickers: reply_markup supported, caption is not
        await context.bot.send_sticker(
            sticker=file_path,
            chat_id=chat_id,
            reply_to_message_id=reply_to,
            reply_markup=reply_markup,
            read_timeout=120,
            write_timeout=120,
        )
    else:
        await context.bot.send_document(document=file_path, **kwargs)