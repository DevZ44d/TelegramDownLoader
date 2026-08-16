"""
Third-choice Instagram extractor, backed by `Instaloader`.

Used only for metadata/URL extraction (no login, no session) — actual
file downloading always goes through our own download engine.
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


def _map_exception(exc: Exception) -> Exception:
    import instaloader.exceptions as ilx

    message = str(exc) or exc.__class__.__name__

    if isinstance(exc, (ilx.LoginRequiredException, ilx.LoginException)):
        return InstagramAuthRequiredError(message)
    if isinstance(exc, (ilx.PrivateProfileNotFollowedException, ilx.QueryReturnedForbiddenException)):
        return InstagramPrivateContentError(message)
    if isinstance(exc, (ilx.ProfileNotExistsException, ilx.QueryReturnedNotFoundException)):
        return InstagramMediaNotFoundError(message)
    if isinstance(exc, ilx.TooManyRequestsException):
        return InstagramRateLimitedError(message)
    if isinstance(exc, (ilx.ConnectionException, ilx.BadResponseException)):
        return InstagramNetworkError(message)
    if isinstance(exc, ilx.InstaloaderException):
        return InstagramExtractionError(message)

    return InstagramExtractionError(message)


class InstaloaderExtractor(BaseInstagramExtractor):
    name = "instaloader"

    async def can_handle(self, url: str) -> bool:
        parsed = parse_instagram_url(url)
        # Instaloader is only used here for post/reel/tv metadata; profile
        # pictures are already well covered by parth-dl/gallery-dl and
        # Instaloader's profile API needs an extra network round trip just
        # to check reachability, so we don't spend a fallback attempt there.
        return parsed.url_type in (InstagramURLType.POST, InstagramURLType.REEL, InstagramURLType.TV)

    async def extract(self, url: str) -> ExtractorResult:
        parsed = parse_instagram_url(url)
        if not parsed.shortcode:
            raise InstagramExtractionError("Could not determine the Instagram shortcode.")

        try:
            media = await asyncio.to_thread(self._extract_sync, parsed.shortcode)
        except Exception as exc:  # noqa: BLE001
            mapped = _map_exception(exc)
            logger.debug("instaloader extraction failed for %s: %s", url, mapped.message)
            raise mapped from exc

        if not media.items:
            raise InstagramMediaNotFoundError("Instaloader found no usable media.")

        return ExtractorResult(success=True, media=media, extractor=self.name)

    @staticmethod
    def _extract_sync(shortcode: str) -> InstagramMedia:
        import instaloader

        loader = instaloader.Instaloader(
            quiet=True,
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
        post = instaloader.Post.from_shortcode(loader.context, shortcode)

        items: list[InstagramMediaItem] = []

        if post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                url = node.video_url if node.is_video else node.display_url
                if not url:
                    continue
                items.append(InstagramMediaItem(url=url, media_type="video" if node.is_video else "image"))
        else:
            url = post.video_url if post.is_video else post.url
            if url:
                items.append(
                    InstagramMediaItem(
                        url=url,
                        media_type="video" if post.is_video else "image",
                        duration=getattr(post, "video_duration", None) if post.is_video else None,
                    )
                )

        return InstagramMedia(
            shortcode=post.shortcode,
            author=post.owner_username,
            caption=post.caption,
            media_type="carousel" if len(items) > 1 else ("video" if post.is_video else "image"),
            items=items,
        )
