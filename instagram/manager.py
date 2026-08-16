"""
Extractor manager: tries backends in order, stopping on the first success
or on a permanent error that no other backend could plausibly fix.
"""

from __future__ import annotations

from core.logger import logger
from instagram.exceptions import PERMANENT_ERRORS, InstagramError, InstagramExtractionError
from instagram.extractors.anon_story import AnonStoryExtractor
from instagram.extractors.base import BaseInstagramExtractor
from instagram.extractors.gallery_dl import GalleryDLExtractor
from instagram.extractors.instaloader import InstaloaderExtractor
from instagram.extractors.parth import ParthExtractor
from instagram.extractors.ytdlp_story import YtDlpStoryExtractor
from instagram.models import ExtractorResult
from instagram.parser import InstagramURLType, is_instagram_url, parse_instagram_url


class InstagramExtractorManager:
    def __init__(self, extractors: list[BaseInstagramExtractor] | None = None) -> None:
        # Order matters. Stories prefer yt-dlp / anon APIs first (no cookies).
        self.extractors: list[BaseInstagramExtractor] = extractors or [
            YtDlpStoryExtractor(),
            AnonStoryExtractor(),
            ParthExtractor(),
            GalleryDLExtractor(),
            InstaloaderExtractor(),
        ]

    async def extract(self, url: str) -> ExtractorResult:
        if not is_instagram_url(url):
            raise InstagramExtractionError("Not an Instagram URL.")

        parsed = parse_instagram_url(url)
        if parsed.url_type == InstagramURLType.UNKNOWN:
            raise InstagramExtractionError("Unrecognized Instagram link format.")

        last_error: Exception | None = None

        for extractor in self.extractors:
            try:
                handles = await extractor.can_handle(url)
            except Exception:  # noqa: BLE001
                continue
            if not handles:
                continue

            try:
                result = await extractor.extract(url)
            except PERMANENT_ERRORS:
                raise
            except InstagramError as exc:
                logger.warning("%s failed for %s: %s", extractor.name, url, exc.message)
                last_error = exc
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("%s raised an unexpected error", extractor.name)
                last_error = InstagramExtractionError(str(exc))
                continue

            if result.success and result.media and result.media.items:
                return result

            last_error = InstagramExtractionError(result.error or "Extractor returned no media.")

        if last_error is not None:
            raise last_error
        raise InstagramExtractionError("No extractor could handle this Instagram link.")