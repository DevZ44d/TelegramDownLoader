"""
Anonymous Instagram story extractor via public downloader APIs.

Many Telegram bots use third-party sites that fetch public stories
without user cookies. We try a few known endpoints.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

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

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# (name, url, build_payload)
_ENDPOINTS = [
    (
        "snapins.ai",
        "https://snapins.ai/api/download",
        lambda u: {"url": u},
    ),
    (
        "fastdl.app",
        "https://fastdl.app/api/convert",
        lambda u: {"url": u},
    ),
]


def _collect_media_urls(obj: Any, found: list[dict]) -> None:
    """Recursively collect likely media URLs from nested JSON / HTML."""
    if isinstance(obj, dict):
        url = obj.get("url") or obj.get("download_url") or obj.get("src") or obj.get("video_url")
        if isinstance(url, str) and url.startswith("http") and any(
            x in url.lower()
            for x in (".mp4", ".jpg", ".jpeg", ".webp", ".png", "cdninstagram", "fbcdn")
        ):
            media_type = "video" if (
                ".mp4" in url.lower() or obj.get("type") in ("video", "mp4")
            ) else "image"
            found.append({"url": url, "media_type": media_type})
        for v in obj.values():
            _collect_media_urls(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _collect_media_urls(v, found)
    elif isinstance(obj, str):
        for m in re.finditer(
            r'https://[^"\'\s]+(?:cdninstagram|fbcdn)[^"\'\s]+',
            obj,
        ):
            link = m.group(0).rstrip("\\")
            media_type = "video" if ".mp4" in link.lower() else "image"
            found.append({"url": link, "media_type": media_type})


class AnonStoryExtractor(BaseInstagramExtractor):
    name = "anon-story"

    async def can_handle(self, url: str) -> bool:
        return parse_instagram_url(url).url_type == InstagramURLType.STORY

    async def extract(self, url: str) -> ExtractorResult:
        last_error: Exception | None = None

        for name, endpoint, payload_fn in _ENDPOINTS:
            try:
                items = await asyncio.to_thread(
                    self._try_endpoint, name, endpoint, payload_fn(url)
                )
                if items:
                    parsed = parse_instagram_url(url)
                    media = InstagramMedia(
                        shortcode=parsed.story_id,
                        author=parsed.username,
                        caption=None,
                        media_type="carousel" if len(items) > 1 else items[0].media_type,
                        items=items,
                    )
                    logger.info(
                        "anon-story succeeded via %s (%s item(s))", name, len(items)
                    )
                    return ExtractorResult(
                        success=True,
                        media=media,
                        extractor=f"{self.name}:{name}",
                    )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.debug("anon-story %s failed: %s", name, exc)
                continue

        if last_error:
            raise InstagramExtractionError(str(last_error)) from last_error
        raise InstagramMediaNotFoundError("No anonymous story API returned media.")

    @staticmethod
    def _try_endpoint(name: str, endpoint: str, payload: dict) -> list[InstagramMediaItem]:
        headers = {
            "User-Agent": _UA,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": endpoint.rsplit("/", 2)[0],
            "Referer": endpoint.rsplit("/", 2)[0] + "/",
        }
        with httpx.Client(timeout=25, follow_redirects=True, headers=headers) as client:
            r = client.post(endpoint, json=payload)
            if r.status_code >= 400:
                r = client.post(
                    endpoint,
                    data=payload,
                    headers={
                        **headers,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
            if r.status_code == 429:
                raise InstagramRateLimitedError(f"{name} rate limited")
            if r.status_code >= 400:
                raise InstagramNetworkError(f"{name} HTTP {r.status_code}")

            found: list[dict] = []
            try:
                data = r.json()
                _collect_media_urls(data, found)
            except Exception:
                _collect_media_urls(r.text, found)

            seen = set()
            items: list[InstagramMediaItem] = []
            for m in found:
                if m["url"] in seen:
                    continue
                seen.add(m["url"])
                items.append(
                    InstagramMediaItem(url=m["url"], media_type=m["media_type"])
                )
            return items