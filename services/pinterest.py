from __future__ import annotations

import time
from typing import Awaitable, Callable, Optional

from core.logger import logger
from models.media import DownloadResult, MediaItem, MediaType
from pinterest.downloader import download_pinterest
from pinterest.exceptions import (
    InvalidPinterestURLError,
    PinterestError,
    PinterestExtractionError,
    PinterestMediaNotFoundError,
    PinterestNetworkError,
)
from pinterest.parser import is_pinterest_url

ProgressCallback = Callable[[str], Awaitable[None]]

_ERROR_MESSAGES: dict[type[PinterestError], str] = {
    InvalidPinterestURLError: "❌ Invalid Pinterest link.",
    PinterestMediaNotFoundError: "❌ Could not find media on this Pinterest pin.",
    PinterestNetworkError: "❌ Network error while contacting Pinterest. Try again later.",
    PinterestExtractionError: "❌ Failed to extract Pinterest media.",
}


def _friendly_error(exc: PinterestError) -> str:
    for t, msg in _ERROR_MESSAGES.items():
        if isinstance(exc, t):
            return msg
    return f"❌ {exc.message}"


async def download_pinterest_media(
    url: str,
    progress: Optional[ProgressCallback] = None,
) -> DownloadResult:
    if not is_pinterest_url(url):
        return DownloadResult(success=False, error="❌ Invalid Pinterest link.", source_link=url)

    started = time.monotonic()
    if progress:
        try:
            await progress("⬇️ Downloading from Pinterest...")
        except Exception:
            pass

    try:
        files = await download_pinterest(url)
    except PinterestError as exc:
        logger.info("Pinterest download failed for %s: %s", url, exc.message)
        return DownloadResult(success=False, error=_friendly_error(exc), source_link=url)
    except Exception:
        logger.exception("Unhandled Pinterest error for %s", url)
        return DownloadResult(
            success=False,
            error="❌ Something went wrong downloading from Pinterest.",
            source_link=url,
        )

    items: list[MediaItem] = []
    for idx, f in enumerate(files):
        if f.media_type == "video":
            mt = MediaType.VIDEO
        elif f.media_type == "audio":
            mt = MediaType.AUDIO
        else:
            mt = MediaType.PHOTO
        items.append(
            MediaItem(
                media_type=mt,
                file_path=f.path,
                mime_type=f.mime_type,
                file_size=f.path.stat().st_size if f.path.exists() else None,
                caption=f.caption if idx == len(files) - 1 else None,
            )
        )

    logger.info(
        "Pinterest download complete for %s: %s file(s) in %.1fs",
        url,
        len(items),
        time.monotonic() - started,
    )
    return DownloadResult(success=True, items=items, source_link=url)