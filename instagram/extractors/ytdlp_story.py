"""
Instagram Stories extractor via yt-dlp.
Optional cookies via INSTAGRAM_COOKIES improve success rate.
"""

from __future__ import annotations

import asyncio

from config import settings
from core.logger import logger
from instagram.exceptions import (
    InstagramExtractionError,
    InstagramMediaNotFoundError,
    InstagramNetworkError,
    InstagramRateLimitedError,
)
from instagram.extractors.base import BaseInstagramExtractor
from instagram.models import ExtractorResult, InstagramMedia, InstagramMediaItem
from instagram.parser import InstagramURLType, parse_instagram_url


def _map_error(message: str) -> Exception:
    """Login/auth is TRANSIENT so other extractors still run."""
    lowered = message.lower()
    if "429" in lowered or "too many requests" in lowered or "rate" in lowered:
        return InstagramRateLimitedError(message)
    if "login" in lowered or "cookie" in lowered or "auth" in lowered:
        return InstagramExtractionError(message)
    if "private" in lowered or "403" in lowered or "forbidden" in lowered:
        return InstagramExtractionError(message)
    if "not found" in lowered or "404" in lowered or "expired" in lowered:
        return InstagramMediaNotFoundError(message)
    if "network" in lowered or "timeout" in lowered or "http error" in lowered:
        return InstagramNetworkError(message)
    return InstagramExtractionError(message)


class YtDlpStoryExtractor(BaseInstagramExtractor):
    name = "yt-dlp-story"

    async def can_handle(self, url: str) -> bool:
        parsed = parse_instagram_url(url)
        return parsed.url_type == InstagramURLType.STORY

    async def extract(self, url: str) -> ExtractorResult:
        try:
            info = await asyncio.to_thread(self._extract_sync, url)
        except Exception as exc:
            mapped = _map_error(str(exc))
            logger.debug("yt-dlp story extraction failed for %s: %s", url, mapped.message)
            raise mapped from exc

        entries = []
        if info.get("_type") == "playlist" or info.get("entries"):
            entries = [e for e in (info.get("entries") or []) if e]
        else:
            entries = [info]

        items: list[InstagramMediaItem] = []
        author = info.get("uploader") or info.get("channel") or info.get("creator")
        caption = info.get("description") or info.get("title")
        shortcode = info.get("id") or info.get("display_id")

        for entry in entries:
            if not entry:
                continue
            media_url = entry.get("url")
            if not media_url and entry.get("formats"):
                formats = entry["formats"]
                video_fmts = [f for f in formats if f.get("vcodec") != "none" and f.get("url")]
                pool = video_fmts or [f for f in formats if f.get("url")]
                if pool:
                    best = max(pool, key=lambda f: (f.get("height") or 0, f.get("width") or 0))
                    media_url = best.get("url")

            if not media_url:
                continue

            is_video = (
                entry.get("ext") in ("mp4", "mov", "webm", "m4v")
            ) or bool(
                entry.get("vcodec") and entry.get("vcodec") != "none"
            ) or (entry.get("duration") is not None)

            if not is_video and any(x in media_url.lower() for x in (".mp4", ".mov", "video")):
                is_video = True

            items.append(
                InstagramMediaItem(
                    url=media_url,
                    media_type="video" if is_video else "image",
                    width=entry.get("width"),
                    height=entry.get("height"),
                    duration=entry.get("duration"),
                )
            )
            author = author or entry.get("uploader")
            shortcode = shortcode or entry.get("id")

        if not items:
            raise InstagramMediaNotFoundError("yt-dlp found no downloadable story media.")

        media = InstagramMedia(
            shortcode=str(shortcode) if shortcode else None,
            author=author,
            caption=caption,
            media_type="carousel" if len(items) > 1 else items[0].media_type,
            items=items,
        )
        return ExtractorResult(success=True, media=media, extractor=self.name)

    @staticmethod
    def _extract_sync(url: str) -> dict:
        import yt_dlp

        class _Quiet:
            def debug(self, *a, **k): pass
            def info(self, *a, **k): pass
            def warning(self, *a, **k): pass
            def error(self, *a, **k): pass

        opts = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "logger": _Quiet(),
        }
        # Optional cookies
        cookies = getattr(settings, "instagram_cookies", None)
        if cookies:
            from pathlib import Path as _P
            if _P(cookies).is_file():
                opts["cookiefile"] = str(_P(cookies).resolve())
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise InstagramMediaNotFoundError("yt-dlp returned empty result.")
        return info