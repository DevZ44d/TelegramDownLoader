"""
Instagram URL detection & parsing.

Uses proper URL parsing (urllib.parse) instead of fragile string
splitting, so query strings, trailing slashes, and locale/share-link
prefixes don't break detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

_ALLOWED_HOSTS = {"instagram.com", "www.instagram.com"}

# Path segments that are Instagram's own routes, never a username.
_RESERVED_SEGMENTS = {
    "p",
    "reel",
    "reels",
    "tv",
    "stories",
    "explore",
    "accounts",
    "direct",
    "about",
    "developer",
    "legal",
    "privacy",
    "terms",
    "web",
    "api",
    "ads",
    "highlights",
    "s",
}

_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]+$")
# Story media id is usually a long numeric string
_STORY_ID_RE = re.compile(r"^\d{10,}$")


class InstagramURLType(str, Enum):
    POST = "post"
    REEL = "reel"
    TV = "tv"
    PROFILE = "profile"
    STORY = "story"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class InstagramURL:
    url_type: InstagramURLType
    raw: str
    shortcode: str | None = None
    username: str | None = None
    story_id: str | None = None

    @property
    def is_media(self) -> bool:
        return self.url_type in (
            InstagramURLType.POST,
            InstagramURLType.REEL,
            InstagramURLType.TV,
            InstagramURLType.STORY,
        )


def _segments(url: str) -> list[str] | None:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        return None

    return [seg for seg in parsed.path.split("/") if seg]


def is_instagram_url(url: str) -> bool:
    """Return True if `url` points at instagram.com / www.instagram.com."""
    return _segments(url) is not None


def parse_instagram_url(url: str) -> InstagramURL:
    """
    Parse an Instagram URL into a structured InstagramURL.

    Supported forms:
        /p/<shortcode>/                              -> POST
        /reel/<shortcode>/                           -> REEL
        /reels/<shortcode>/                          -> REEL
        /tv/<shortcode>/                             -> TV
        /stories/<username>/<story_id>/              -> STORY
        /stories/<username>/                         -> STORY (latest / all)
        /<username>/                                 -> PROFILE (profile picture only)
    """
    raw = url.strip()
    segments = _segments(raw)

    if segments is None:
        return InstagramURL(url_type=InstagramURLType.UNKNOWN, raw=raw)

    # /stories/<username>/<story_id>  or  /stories/<username>
    if len(segments) >= 2 and segments[0].lower() == "stories":
        username = segments[1]
        if username.startswith("@"):
            username = username[1:]
        if not _USERNAME_RE.fullmatch(username):
            return InstagramURL(url_type=InstagramURLType.UNKNOWN, raw=raw)

        story_id = None
        if len(segments) >= 3 and _STORY_ID_RE.fullmatch(segments[2]):
            story_id = segments[2]

        return InstagramURL(
            url_type=InstagramURLType.STORY,
            raw=raw,
            username=username,
            story_id=story_id,
            shortcode=story_id,
        )

    # /p|reel|reels|tv/<shortcode>
    if len(segments) >= 2 and segments[0].lower() in ("p", "reel", "reels", "tv"):
        kind = segments[0].lower()
        shortcode = segments[1]
        if _SHORTCODE_RE.fullmatch(shortcode):
            url_type = {
                "p": InstagramURLType.POST,
                "reel": InstagramURLType.REEL,
                "reels": InstagramURLType.REEL,
                "tv": InstagramURLType.TV,
            }[kind]
            return InstagramURL(url_type=url_type, raw=raw, shortcode=shortcode)
        return InstagramURL(url_type=InstagramURLType.UNKNOWN, raw=raw)

    # /<username>
    if len(segments) == 1:
        username = segments[0]
        if username.startswith("@"):
            username = username[1:]
        if username.lower() not in _RESERVED_SEGMENTS and _USERNAME_RE.fullmatch(username):
            return InstagramURL(url_type=InstagramURLType.PROFILE, raw=raw, username=username)

    return InstagramURL(url_type=InstagramURLType.UNKNOWN, raw=raw)