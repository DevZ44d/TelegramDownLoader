from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from telegram import InputFile
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from core.logger import logger
from handlers.start import build_back_keyboard
from models.media import MediaItem, MediaType
from utils.files import safe_remove
from utils.helpers import truncate

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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

        converted_path: Path | None = None
        try:
            if item.media_type in (MediaType.PHOTO, MediaType.STORY_PHOTO):
                converted_path = _ensure_telegram_photo(path)
                send_path = converted_path or path
            else:
                send_path = path

            await _send_one(context, chat_id, item, send_path, reply_to, cap, markup)
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
            if converted_path and converted_path != path:
                safe_remove(converted_path)


def _ensure_telegram_photo(path: Path) -> Path | None:
    """
    Convert WebP / HEIC / odd formats to a clean JPEG that Telegram accepts.
    Returns the new path if conversion happened, otherwise None.
    """
    if not HAS_PIL:
        return None

    try:
        with Image.open(path) as img:
            # Convert to RGB (drops alpha) — Telegram photo endpoint hates RGBA/WebP
            if img.mode in ("RGBA", "LA", "P", "CMYK"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode in ("RGBA", "LA"):
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Limit very large dimensions
            max_side = 4096
            if max(img.size) > max_side:
                img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

            out = path.with_suffix(".tg.jpg")
            img.save(out, format="JPEG", quality=92, optimize=True)
            logger.debug("Converted %s → %s for Telegram photo", path.name, out.name)
            return out
    except Exception as exc:
        logger.warning("PIL conversion failed for %s: %s — will try original", path, exc)
        return None


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
        "read_timeout": 180,
        "write_timeout": 180,
        "connect_timeout": 60,
        "pool_timeout": 60,
    }
    if caption:
        kwargs["caption"] = caption
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup

    mt = item.media_type

    if mt in (MediaType.PHOTO, MediaType.STORY_PHOTO):
        await _send_photo_with_fallback(context, path, kwargs)
    elif mt in (MediaType.VIDEO, MediaType.STORY_VIDEO, MediaType.ANIMATION):
        video_kwargs = dict(kwargs)
        if item.duration is not None:
            video_kwargs["duration"] = item.duration
        if item.width is not None:
            video_kwargs["width"] = item.width
        if item.height is not None:
            video_kwargs["height"] = item.height
        try:
            with path.open("rb") as f:
                await context.bot.send_video(
                    video=InputFile(f, filename=path.name or "video.mp4"),
                    supports_streaming=True,
                    **video_kwargs,
                )
        except (BadRequest, TelegramError) as exc:
            logger.warning("send_video failed (%s), falling back to document", exc)
            with path.open("rb") as f:
                await context.bot.send_document(
                    document=InputFile(f, filename=path.name or "video.mp4"),
                    **kwargs,
                )
    elif mt == MediaType.VOICE:
        with path.open("rb") as f:
            await context.bot.send_voice(voice=InputFile(f, filename=path.name), **kwargs)
    elif mt == MediaType.AUDIO:
        with path.open("rb") as f:
            await context.bot.send_audio(audio=InputFile(f, filename=path.name), **kwargs)
    elif mt == MediaType.STICKER:
        with path.open("rb") as f:
            await context.bot.send_sticker(
                sticker=InputFile(f, filename=path.name),
                chat_id=chat_id,
                reply_to_message_id=reply_to,
                reply_markup=reply_markup,
                read_timeout=120,
                write_timeout=120,
            )
    else:
        with path.open("rb") as f:
            await context.bot.send_document(
                document=InputFile(f, filename=path.name),
                **kwargs,
            )


async def _send_photo_with_fallback(
    context: ContextTypes.DEFAULT_TYPE,
    path: Path,
    kwargs: dict,
) -> None:
    """
    Try send_photo. On Image_process_failed → fall back to document.
    """
    try:
        with path.open("rb") as f:
            await context.bot.send_photo(
                photo=InputFile(f, filename=(path.stem + ".jpg")),
                **kwargs,
            )
        return
    except BadRequest as exc:
        msg = str(exc).lower()
        if (
            "image_process_failed" not in msg
            and "wrong file identifier" not in msg
            and "failed to get http url content" not in msg
        ):
            raise
        logger.warning("send_photo failed (%s), retrying as document", exc)

    with path.open("rb") as f:
        await context.bot.send_document(
            document=InputFile(f, filename=path.name or "image.jpg"),
            **kwargs,
        )
