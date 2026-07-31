from __future__ import annotations

from typing import Any, Optional

from telethon.tl.custom.message import Message as TelethonMessage

from core.exceptions import AccessDeniedError, MediaNotFoundError
from core.logger import logger
from core.telethon_client import get_telethon
from models.media import MediaItem, MediaType
from utils.files import extension_from_mime, safe_remove, unique_filename


async def get_telethon_message(peer: str, message_id: int) -> TelethonMessage:
    client = get_telethon()
    try:
        msg = await client.get_messages(peer, ids=message_id)
        if msg is None:
            raise AccessDeniedError("Message not found or inaccessible")
        return msg
    except AccessDeniedError:
        raise
    except Exception as exc:
        logger.exception("get_messages failed for %s/%s", peer, message_id)
        raise AccessDeniedError(str(exc)) from exc


async def download_telethon_media(msg: TelethonMessage) -> list[MediaItem]:
    """Download media from a Telethon message to a local file."""
    if not msg.media:
        if msg.message:
            return [
                MediaItem(
                    media_type=MediaType.DOCUMENT,
                    caption=msg.message,
                )
            ]
        raise MediaNotFoundError("No media in this message")

    client = get_telethon()
    mime: Optional[str] = None
    media_type = MediaType.DOCUMENT

    # Detect type
    if msg.photo:
        media_type = MediaType.PHOTO
        ext = ".jpg"
    elif msg.video:
        media_type = MediaType.VIDEO
        mime = getattr(msg.video, "mime_type", None) or "video/mp4"
        ext = extension_from_mime(mime, ".mp4")
    elif msg.gif or (msg.document and getattr(msg.document, "mime_type", "").startswith("image/gif")):
        media_type = MediaType.ANIMATION
        ext = ".mp4"
    elif msg.voice:
        media_type = MediaType.VOICE
        ext = ".ogg"
    elif msg.audio:
        media_type = MediaType.AUDIO
        mime = getattr(msg.audio, "mime_type", None)
        ext = extension_from_mime(mime, ".mp3")
    elif msg.sticker:
        media_type = MediaType.STICKER
        ext = ".webp"
    elif msg.document:
        media_type = MediaType.DOCUMENT
        mime = getattr(msg.document, "mime_type", None)
        ext = extension_from_mime(mime, ".bin")
    else:
        raise MediaNotFoundError("Unsupported media type")

    path = unique_filename(ext, prefix=f"msg_{msg.id}_")
    try:
        await client.download_media(msg, file=str(path))
        if not path.exists():
            raise MediaNotFoundError("Download produced no file")

        item = MediaItem(
            media_type=media_type,
            file_path=path,
            mime_type=mime,
            caption=msg.message,
            file_size=path.stat().st_size,
        )
        return [item]
    except Exception as exc:
        safe_remove(path)
        logger.exception("Failed to download media from message %s", msg.id)
        raise
