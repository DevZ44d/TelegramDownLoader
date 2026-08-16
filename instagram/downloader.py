"""
Instagram download engine.

Instagram CDN -> temporary file -> validate -> (caller sends via the
existing Telegram sender) -> caller cleans up.

Every backend's extracted URLs flow through this single pipeline, so
size limits, safe filenames, and cleanup behave identically no matter
which extractor produced the metadata.
"""

from __future__ import annotations

import asyncio

import httpx

from config import settings
from core.logger import logger
from instagram.exceptions import InstagramFileTooLargeError, InstagramNetworkError, InstagramRateLimitedError
from instagram.models import DownloadedInstagramItem, InstagramDownloadResult, InstagramMedia, InstagramMediaItem
from instagram.utils import guess_extension, unique_instagram_path
from utils.files import safe_remove

_CHUNK_SIZE = 256 * 1024

# Magic bytes for common media formats
_IMAGE_MAGIC = (
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"RIFF",  # WebP starts with RIFF....WEBP
    b"GIF87a",
    b"GIF89a",
)


def _looks_like_media(path, expected: str) -> bool:
    """Quick header check so we don't try to send HTML error pages as images."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except OSError:
        return False

    if not head or len(head) < 4:
        return False

    # HTML / JSON error pages
    lower = head.lstrip()[:20].lower()
    if lower.startswith(b"<!doctype") or lower.startswith(b"<html") or lower.startswith(b"{") or lower.startswith(b"<"):
        return False

    if expected == "image":
        if any(head.startswith(m) for m in _IMAGE_MAGIC):
            return True
        # WebP: RIFF....WEBP
        if head.startswith(b"RIFF") and b"WEBP" in head[:16]:
            return True
        return False

    if expected == "video":
        # MP4/MOV usually have "ftyp" within the first 12 bytes
        if b"ftyp" in head[:16]:
            return True
        if head.startswith(b"\x1a\x45\xdf\xa3"):  # WebM/Matroska
            return True
        return not (lower.startswith(b"<!doctype") or lower.startswith(b"<html"))

    return True


async def download_instagram_media(media: InstagramMedia, *, source_url: str) -> InstagramDownloadResult:
    max_bytes = settings.instagram_max_file_size_mb * 1024 * 1024
    semaphore = asyncio.Semaphore(max(1, settings.instagram_max_concurrent_downloads))
    downloaded: list[DownloadedInstagramItem] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=settings.instagram_timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Referer": "https://www.instagram.com/",
        },
    ) as client:

        async def _download_one(index: int, item: InstagramMediaItem) -> DownloadedInstagramItem:
            async with semaphore:
                return await _download_item(
                    client,
                    item,
                    index=index,
                    author=media.author,
                    shortcode=media.shortcode,
                    max_bytes=max_bytes,
                )

        tasks = [asyncio.ensure_future(_download_one(i, item)) for i, item in enumerate(media.items, 1)]

        try:
            results = await asyncio.gather(*tasks)
        except Exception:
            for task in tasks:
                if task.done() and not task.exception():
                    safe_remove(task.result().path)
                else:
                    task.cancel()
            raise

        downloaded.extend(results)

    return InstagramDownloadResult(success=True, source_url=source_url, files=downloaded, media=media)


async def _download_item(
    client: httpx.AsyncClient,
    item: InstagramMediaItem,
    *,
    index: int,
    author: str | None,
    shortcode: str | None,
    max_bytes: int,
) -> DownloadedInstagramItem:
    last_exc: Exception | None = None

    for attempt in range(settings.instagram_max_retries + 1):
        try:
            return await _attempt_download(client, item, index=index, author=author, shortcode=shortcode, max_bytes=max_bytes)
        except InstagramFileTooLargeError:
            raise
        except (InstagramNetworkError, InstagramRateLimitedError) as exc:
            last_exc = exc
            if attempt < settings.instagram_max_retries:
                backoff = 2**attempt
                logger.debug("Retrying Instagram download in %ss (attempt %s): %s", backoff, attempt + 1, exc)
                await asyncio.sleep(backoff)

    assert last_exc is not None
    raise last_exc


async def _attempt_download(
    client: httpx.AsyncClient,
    item: InstagramMediaItem,
    *,
    index: int,
    author: str | None,
    shortcode: str | None,
    max_bytes: int,
) -> DownloadedInstagramItem:
    extension = guess_extension(item.url, item.mime_type, item.media_type)
    dest = unique_instagram_path(extension, author=author, shortcode=shortcode, index=index)

    try:
        async with client.stream("GET", item.url) as response:
            if response.status_code == 429:
                raise InstagramRateLimitedError("Instagram CDN rate limited the download.")
            if response.status_code >= 400:
                raise InstagramNetworkError(f"Instagram CDN returned HTTP {response.status_code}.")

            content_type = (response.headers.get("content-type") or "").lower()
            if "text/html" in content_type or "application/json" in content_type:
                raise InstagramNetworkError(
                    f"CDN returned non-media content-type ({content_type}). "
                    "The media URL is likely expired or blocked."
                )

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                raise InstagramFileTooLargeError(
                    f"Media is {int(content_length) / (1024 * 1024):.1f} MB, "
                    f"which exceeds the {max_bytes / (1024 * 1024):.0f} MB limit."
                )

            written = 0
            with open(dest, "wb") as fh:
                async for chunk in response.aiter_bytes(_CHUNK_SIZE):
                    written += len(chunk)
                    if written > max_bytes:
                        raise InstagramFileTooLargeError(
                            f"Media exceeds the {max_bytes / (1024 * 1024):.0f} MB limit."
                        )
                    fh.write(chunk)

        if not dest.exists() or dest.stat().st_size == 0:
            raise InstagramNetworkError("Download produced an empty file.")

        # Reject HTML/error pages saved with a .jpg extension
        if not _looks_like_media(dest, item.media_type):
            size = dest.stat().st_size
            safe_remove(dest)
            raise InstagramNetworkError(
                f"Downloaded file is not valid {item.media_type} media "
                f"(size={size} bytes). URL may be expired or blocked by Instagram."
            )

        return DownloadedInstagramItem(item=item, path=dest)

    except httpx.TimeoutException as exc:
        safe_remove(dest)
        raise InstagramNetworkError(f"Timed out downloading media: {exc}") from exc
    except httpx.HTTPError as exc:
        safe_remove(dest)
        raise InstagramNetworkError(f"Network error downloading media: {exc}") from exc
    except InstagramFileTooLargeError:
        safe_remove(dest)
        raise
    except InstagramRateLimitedError:
        safe_remove(dest)
        raise
    except Exception:
        safe_remove(dest)
        raise