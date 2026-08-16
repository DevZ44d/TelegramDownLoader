from __future__ import annotations

import asyncio

from core.exceptions import AccessDeniedError, MediaNotFoundError
from core.logger import logger
from models.media import DownloadResult, MediaItem
from services.parser import ParsedLink
from tg.messages import download_telethon_media, get_telethon_message


async def download_post(parsed: ParsedLink) -> DownloadResult:
    if not parsed.peer or parsed.message_id is None:
        return DownloadResult(
            success=False,
            error="Invalid post link",
            source_link=parsed.raw,
        )

    from_id = parsed.message_id
    to_id = parsed.to_message_id or from_id
    if to_id < from_id:
        from_id, to_id = to_id, from_id

    if to_id - from_id > 50:
        return DownloadResult(
            success=False,
            error="Maximum range is 50 messages",
            source_link=parsed.raw,
        )

    msg_ids = list(range(from_id, to_id + 1))

    # Parallel download (max 5 concurrent)
    sem = asyncio.Semaphore(5)

    async def _one(msg_id: int) -> tuple[int, list[MediaItem] | str]:
        async with sem:
            try:
                msg = await get_telethon_message(parsed.peer, msg_id)
                items = await download_telethon_media(msg)
                return msg_id, items
            except AccessDeniedError:
                return msg_id, f"Message {msg_id}: Access denied"
            except MediaNotFoundError:
                return msg_id, f"Message {msg_id}: No media found"
            except Exception as exc:
                logger.exception("Error on message %s", msg_id)
                return msg_id, f"Message {msg_id}: {exc}"

    results = await asyncio.gather(*[_one(mid) for mid in msg_ids])

    all_items: list[MediaItem] = []
    errors: list[str] = []

    for msg_id, payload in results:
        if isinstance(payload, list):
            all_items.extend(payload)
        else:
            errors.append(payload)

    if all_items:
        return DownloadResult(
            success=True,
            items=all_items,
            source_link=parsed.raw,
            error="; ".join(errors) if errors else None,
        )

    return DownloadResult(
        success=False,
        error=errors[0] if errors else "No downloadable content found",
        source_link=parsed.raw,
    )
