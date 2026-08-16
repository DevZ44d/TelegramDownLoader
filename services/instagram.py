from __future__ import annotations

import time
from typing import Awaitable, Callable, Optional

from config import settings
from core.logger import logger
from instagram.downloader import download_instagram_media
from instagram.exceptions import (
    InstagramAuthRequiredError,
    InstagramError,
    InstagramFileTooLargeError,
    InstagramMediaNotFoundError,
    InstagramPrivateContentError,
    InstagramRateLimitedError,
    InvalidInstagramURLError,
    UnsupportedInstagramURLError,
)
from instagram.manager import InstagramExtractorManager
from instagram.parser import InstagramURLType, is_instagram_url, parse_instagram_url
from instagram.profile import InstagramProfile, fetch_instagram_profile, format_profile_message
from models.media import DownloadResult, MediaItem, MediaType

ProgressCallback = Callable[[str], Awaitable[None]]

_manager = InstagramExtractorManager()

_ERROR_MESSAGES: dict[type[InstagramError], str] = {
    InvalidInstagramURLError: "❌ Invalid Instagram link.",
    UnsupportedInstagramURLError: "❌ Unsupported Instagram link. Send a reel, post, story, or profile URL.",
    InstagramAuthRequiredError: "❌ Instagram requires login for this content.\n💡 Add INSTAGRAM_COOKIES=path/to/cookies.txt in .env (optional but recommended for stories & profiles).",
    InstagramPrivateContentError: "❌ This Instagram content is not publicly accessible.",
    InstagramMediaNotFoundError: "❌ The media could not be found.",
    InstagramRateLimitedError: "❌ Instagram temporarily blocked the request.\n💡 Wait a few minutes, or add INSTAGRAM_COOKIES=path/to/cookies.txt in .env to reduce rate limits.",
    InstagramFileTooLargeError: "❌ This Instagram media is too large to send through the bot.",
}


def _friendly_error(exc: InstagramError) -> str:
    for exc_type, message in _ERROR_MESSAGES.items():
        if isinstance(exc, exc_type):
            return message
    return f"❌ {exc.message}"


async def get_instagram_profile(url: str) -> tuple[Optional[InstagramProfile], Optional[str]]:
    """
    Resolve a profile URL -> InstagramProfile.
    Returns (profile, error_message).
    """
    if not settings.instagram_enabled:
        return None, "❌ Instagram downloads are currently disabled."

    if not is_instagram_url(url):
        return None, "❌ Invalid Instagram link."

    parsed = parse_instagram_url(url)
    if parsed.url_type != InstagramURLType.PROFILE or not parsed.username:
        return None, "❌ Not an Instagram profile URL."

    try:
        profile = await fetch_instagram_profile(parsed.username)
        return profile, None
    except InstagramError as exc:
        logger.info("Instagram profile fetch failed for %s: %s", url, exc.message)
        return None, _friendly_error(exc)
    except Exception as exc:
        logger.exception("Unhandled profile error for %s", url)
        return None, "❌ Could not fetch this Instagram profile."


async def download_instagram(url: str, progress: Optional[ProgressCallback] = None) -> DownloadResult:
    """
    URL parsing -> extractor selection -> fallback -> download -> media
    normalization into the project's existing MediaItem/DownloadResult.
    """
    if not settings.instagram_enabled:
        return DownloadResult(success=False, error="❌ Instagram downloads are currently disabled.", source_link=url)

    if not is_instagram_url(url):
        return DownloadResult(success=False, error="❌ Invalid Instagram link.", source_link=url)

    parsed = parse_instagram_url(url)
    if parsed.url_type == InstagramURLType.UNKNOWN:
        return DownloadResult(success=False, error="❌ Invalid Instagram link.", source_link=url)

    # Profile links are handled separately (info card, not media download)
    if parsed.url_type == InstagramURLType.PROFILE:
        return DownloadResult(
            success=False,
            error="PROFILE",  # sentinel — handler will call get_instagram_profile
            source_link=url,
        )

    started_at = time.monotonic()

    try:
        extract_result = await _manager.extract(url)
    except InstagramError as exc:
        logger.info("Instagram extraction failed for %s: %s", url, exc.message)
        return DownloadResult(success=False, error=_friendly_error(exc), source_link=url)

    media = extract_result.media
    assert media is not None

    logger.info(
        "Instagram extraction succeeded for %s via %s (%s item(s))",
        url,
        extract_result.extractor,
        len(media.items),
    )

    if progress is not None:
        try:
            await progress("⬇️ Downloading Instagram media...")
        except Exception:
            logger.debug("Progress callback failed", exc_info=True)

    try:
        download_result = await download_instagram_media(media, source_url=url)
    except InstagramError as exc:
        logger.info("Instagram download failed for %s: %s", url, exc.message)
        return DownloadResult(success=False, error=_friendly_error(exc), source_link=url)

    duration = time.monotonic() - started_at
    logger.info(
        "Instagram download complete for %s: %s file(s) in %.1fs (extractor=%s)",
        url,
        len(download_result.files),
        duration,
        extract_result.extractor,
    )

    items: list[MediaItem] = []
    for idx, downloaded in enumerate(download_result.files):
        is_last = idx == len(download_result.files) - 1
        items.append(
            MediaItem(
                media_type=MediaType.VIDEO if downloaded.item.media_type == "video" else MediaType.PHOTO,
                file_path=downloaded.path,
                mime_type=downloaded.item.mime_type,
                file_size=downloaded.path.stat().st_size if downloaded.path.exists() else None,
                width=downloaded.item.width,
                height=downloaded.item.height,
                duration=int(downloaded.item.duration) if downloaded.item.duration else None,
                caption=media.caption if is_last else None,
            )
        )

    return DownloadResult(success=True, items=items, source_link=url)


__all__ = [
    "download_instagram",
    "get_instagram_profile",
    "format_profile_message",
    "InstagramProfile",
]