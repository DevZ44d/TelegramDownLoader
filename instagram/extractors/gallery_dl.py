"""
Fallback Instagram extractor, backed by `gallery-dl`.

Optional INSTAGRAM_COOKIES in .env — used when present (stories work much better).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from config import settings
from core.logger import logger
from instagram.exceptions import (
    InstagramAuthRequiredError,
    InstagramExtractionError,
    InstagramMediaNotFoundError,
    InstagramNetworkError,
    InstagramPrivateContentError,
    InstagramRateLimitedError,
    UnsupportedInstagramURLError,
)
from instagram.extractors.base import BaseInstagramExtractor
from instagram.models import ExtractorResult, InstagramMedia, InstagramMediaItem
from instagram.parser import InstagramURLType, parse_instagram_url

_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "m4v"}


def _map_exception(exc: BaseException) -> Exception:
    from gallery_dl import exception as gdl_exc

    message = str(exc) or exc.__class__.__name__

    if isinstance(exc, (gdl_exc.AuthenticationError, gdl_exc.AuthRequired)):
        return InstagramAuthRequiredError(message)
    if isinstance(exc, gdl_exc.AuthorizationError):
        return InstagramPrivateContentError(message)
    if isinstance(exc, gdl_exc.NotFoundError):
        return InstagramMediaNotFoundError(message)
    if isinstance(exc, gdl_exc.NoExtractorError):
        return UnsupportedInstagramURLError(message)
    if isinstance(exc, gdl_exc.HttpError):
        status = getattr(exc, "status", None)
        if status == 429:
            return InstagramRateLimitedError(message)
        if status in (401, 403):
            return InstagramAuthRequiredError(
                "Instagram requires login cookies for this content (stories/highlights). "
                "Add INSTAGRAM_COOKIES=path/to/cookies.txt in .env"
            )
        return InstagramNetworkError(message)
    if isinstance(exc, gdl_exc.GalleryDLException):
        if "401" in message or "unauthorized" in message.lower():
            return InstagramAuthRequiredError(
                "Instagram requires login cookies for this content (stories/highlights). "
                "Add INSTAGRAM_COOKIES=path/to/cookies.txt in .env"
            )
        return InstagramExtractionError(message)

    return InstagramExtractionError(message)


class GalleryDLExtractor(BaseInstagramExtractor):
    name = "gallery-dl"

    async def can_handle(self, url: str) -> bool:
        parsed = parse_instagram_url(url)
        if parsed.url_type == InstagramURLType.UNKNOWN:
            return False
        try:
            return await asyncio.to_thread(self._can_handle_sync, url)
        except Exception:
            return False

    async def extract(self, url: str) -> ExtractorResult:
        try:
            urls, metas, exc = await asyncio.to_thread(self._run_data_job, url)
        except Exception as exc:
            mapped = _map_exception(exc)
            logger.debug("gallery-dl extraction failed for %s: %s", url, mapped.message)
            raise mapped from exc

        if exc is not None:
            mapped = _map_exception(exc)
            logger.debug("gallery-dl extraction failed for %s: %s", url, mapped.message)
            raise mapped

        if not urls:
            raise InstagramMediaNotFoundError("gallery-dl found no downloadable media.")

        items: list[InstagramMediaItem] = []
        author = None
        shortcode = None
        caption = None

        for media_url, meta in zip(urls, metas):
            meta = meta or {}
            author = author or meta.get("username") or meta.get("uploader")
            shortcode = shortcode or meta.get("shortcode") or meta.get("post_shortcode") or meta.get("media_id")
            caption = caption or meta.get("description") or meta.get("caption")

            extension = (meta.get("extension") or "").lower()
            is_video = extension in _VIDEO_EXTENSIONS or bool(meta.get("video_url"))

            items.append(
                InstagramMediaItem(
                    url=media_url,
                    media_type="video" if is_video else "image",
                    width=meta.get("width"),
                    height=meta.get("height"),
                    duration=meta.get("duration"),
                )
            )

        if not items:
            raise InstagramMediaNotFoundError("gallery-dl found no usable media.")

        media = InstagramMedia(
            shortcode=shortcode,
            author=author,
            caption=caption,
            media_type="carousel" if len(items) > 1 else items[0].media_type,
            items=items,
        )
        return ExtractorResult(success=True, media=media, extractor=self.name)

    @staticmethod
    def _can_handle_sync(url: str) -> bool:
        from gallery_dl import extractor as gdl_extractor

        return gdl_extractor.find(url) is not None

    @staticmethod
    def _run_data_job(url: str):
        """Run gallery-dl DataJob with optional Instagram cookies."""
        from gallery_dl import config as gdl_config
        from gallery_dl import job as gdl_job

        cookies_path = getattr(settings, "instagram_cookies", None)
        if cookies_path:
            path = Path(cookies_path)
            if path.is_file():
                gdl_config.set(("extractor", "instagram"), "cookies", str(path.resolve()))
                logger.debug("gallery-dl using cookies from %s", path)
            else:
                logger.warning("INSTAGRAM_COOKIES path does not exist: %s", path)

        data_job = gdl_job.DataJob(url, file=None)
        data_job.run()
        return data_job.data_urls, data_job.data_meta, data_job.exception