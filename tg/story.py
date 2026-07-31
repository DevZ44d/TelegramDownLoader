from __future__ import annotations

from pathlib import Path
from typing import Optional

from telethon.tl import functions
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto, StoryItem

from core.exceptions import AccessDeniedError, DownloadFailedError, StoryNotFoundError
from core.logger import logger
from core.telethon_client import get_telethon
from models.media import MediaItem, MediaType
from utils.files import extension_from_mime, safe_remove, unique_filename


async def fetch_story(peer: str, story_id: int) -> list[MediaItem]:
    client = get_telethon()

    try:
        result = await client(
            functions.stories.GetStoriesByIDRequest(peer=peer, id=[story_id])
        )
    except Exception as exc:
        logger.exception("GetStoriesByID failed for %s/%s", peer, story_id)
        raise AccessDeniedError(f"Cannot access story: {exc}") from exc

    if not result.stories:
        raise StoryNotFoundError("Story not found or already expired.")

    items: list[MediaItem] = []

    for story in result.stories:
        if not isinstance(story, StoryItem) or story.media is None:
            continue

        media = story.media
        file_path: Optional[Path] = None
        media_type = MediaType.STORY_PHOTO
        mime: Optional[str] = None

        try:
            if isinstance(media, MessageMediaPhoto):
                media_type = MediaType.STORY_PHOTO
                file_path = unique_filename(".jpg", prefix=f"story_{story_id}_")
                await client.download_media(media, file=str(file_path))

            elif isinstance(media, MessageMediaDocument):
                doc = media.document
                mime = getattr(doc, "mime_type", None) or ""
                if mime.startswith("video/"):
                    media_type = MediaType.STORY_VIDEO
                    ext = extension_from_mime(mime, ".mp4")
                else:
                    media_type = MediaType.STORY_PHOTO
                    ext = extension_from_mime(mime, ".jpg")
                file_path = unique_filename(ext, prefix=f"story_{story_id}_")
                await client.download_media(media, file=str(file_path))
            else:
                continue

            if file_path and file_path.exists():
                items.append(
                    MediaItem(
                        media_type=media_type,
                        file_path=file_path,
                        mime_type=mime,
                        is_story=True,
                        story_id=story_id,
                        peer=peer,
                        caption=getattr(story, "caption", None),
                    )
                )
            else:
                raise DownloadFailedError("Downloaded file is missing")
        except Exception as exc:
            if file_path:
                safe_remove(file_path)
            logger.exception("Failed to download story media")
            raise DownloadFailedError(str(exc)) from exc

    if not items:
        raise StoryNotFoundError("No downloadable media in this story.")
    return items
