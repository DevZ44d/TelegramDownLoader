"""
Primary Instagram extractor, backed by the `parth-dl` library.

parth-dl already implements public (logged-out) extraction for posts,
reels, tv, carousels, and profile pictures via `get_info()`. We only
use `get_info()` here — actual file downloading goes through our own
download engine (instagram/downloader.py) so every backend feeds the
same download/validation/cleanup pipeline.
"""

from __future__ import annotations

import asyncio

from core.logger import logger
from instagram.exceptions import (
    InstagramAuthRequiredError,
    InstagramExtractionError,
    InstagramMediaNotFoundError,
    InstagramNetworkError,
    InstagramPrivateContentError,
    InstagramRateLimitedError,
)
from instagram.extractors.base import BaseInstagramExtractor
from instagram.models import ExtractorResult, InstagramMedia, InstagramMediaItem
from instagram.parser import InstagramURLType, parse_instagram_url

_AUTH_HINTS = ("login", "private", "forbidden", "not publicly")


def _select_best_format(formats: list[dict]) -> dict | None:
    if not formats:
        return None
    with_dims = [f for f in formats if f.get("width") and f.get("height")]
    pool = with_dims or formats
    return max(pool, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))


def _map_error(exc: Exception) -> Exception:
    """Map a parth_dl exception onto our own exception hierarchy."""
    try:
        from parth_dl import NetworkError as PDLNetworkError
        from parth_dl import RateLimitError as PDLRateLimitError
    except ImportError:  # pragma: no cover - defensive
        PDLNetworkError = PDLRateLimitError = ()  # type: ignore[assignment]

    message = str(exc) or exc.__class__.__name__

    if PDLRateLimitError and isinstance(exc, PDLRateLimitError):
        return InstagramRateLimitedError(message)
    if PDLNetworkError and isinstance(exc, PDLNetworkError):
        return InstagramNetworkError(message)

    lowered = message.lower()
    if any(hint in lowered for hint in _AUTH_HINTS):
        if "private" in lowered:
            return InstagramPrivateContentError(message)
        return InstagramAuthRequiredError(message)
    if "not found" in lowered or "deleted" in lowered:
        return InstagramMediaNotFoundError(message)

    return InstagramExtractionError(message)


class ParthExtractor(BaseInstagramExtractor):
    name = "parth-dl"

    async def can_handle(self, url: str) -> bool:
        parsed = parse_instagram_url(url)
        return parsed.url_type != InstagramURLType.UNKNOWN

    async def extract(self, url: str) -> ExtractorResult:
        try:
            info = await asyncio.to_thread(self._get_info_sync, url)
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed InstagramError below
            mapped = _map_error(exc)
            logger.debug("parth-dl extraction failed for %s: %s", url, mapped.message)
            raise mapped from exc

        entries = info.get("entries") or []
        if not entries:
            raise InstagramMediaNotFoundError("No downloadable media found in this post.")

        items: list[InstagramMediaItem] = []
        for entry in entries:
            fmt = _select_best_format(entry.get("formats") or [])
            if not fmt or not fmt.get("url"):
                continue
            items.append(
                InstagramMediaItem(
                    url=fmt["url"],
                    media_type="video" if entry.get("kind") == "video" else "image",
                    width=fmt.get("width"),
                    height=fmt.get("height"),
                    duration=info.get("duration") if entry.get("kind") == "video" else None,
                )
            )

        if not items:
            raise InstagramMediaNotFoundError("No usable media format found for this post.")

        media = InstagramMedia(
            shortcode=info.get("id"),
            author=info.get("uploader"),
            caption=info.get("title"),
            media_type=info.get("type", "post"),
            thumbnail_url=info.get("thumbnail"),
            items=items,
        )
        return ExtractorResult(success=True, media=media, extractor=self.name)

    @staticmethod
    def _get_info_sync(url: str) -> dict:
        import parth_dl

        return parth_dl.get_info(url)
