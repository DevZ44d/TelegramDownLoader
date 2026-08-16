"""
Instagram module exception hierarchy.

Extends the project's existing exception hierarchy (core.exceptions)
so Instagram errors interoperate cleanly with the rest of the app.

Errors are split into two families that the extractor manager uses to
decide whether to fall back to the next extractor:

  * "permanent" errors mean trying another extractor is pointless
    (invalid link, content requires login, private content, media
    genuinely not found) — these propagate immediately.
  * "transient" errors mean the extractor itself failed but another
    extractor might still succeed (rate limiting, network issues,
    an extractor-specific parsing failure).
"""

from __future__ import annotations

from core.exceptions import DownloaderError


class InstagramError(DownloaderError):
    """Base class for all Instagram-module errors."""


# --- Permanent errors: stop the fallback chain -----------------------------


class InvalidInstagramURLError(InstagramError):
    """The given text is not a valid Instagram URL."""


class UnsupportedInstagramURLError(InstagramError):
    """A valid Instagram URL, but not a supported operation (e.g. bare profile)."""


class InstagramAuthRequiredError(InstagramError):
    """Instagram is asking for a login to view this content."""


class InstagramPrivateContentError(InstagramError):
    """The content belongs to a private account and cannot be fetched."""


class InstagramMediaNotFoundError(InstagramError):
    """The media does not exist (deleted, wrong shortcode, expired)."""


class InstagramFileTooLargeError(InstagramError):
    """The media exceeds the configured/Telegram upload size limit."""


# --- Transient errors: worth trying the next extractor ----------------------


class InstagramRateLimitedError(InstagramError):
    """Instagram is rate-limiting requests."""


class InstagramNetworkError(InstagramError):
    """A network-level failure occurred while talking to Instagram."""


class InstagramExtractionError(InstagramError):
    """A generic, extractor-specific extraction failure."""


PERMANENT_ERRORS: tuple[type[InstagramError], ...] = (
    InvalidInstagramURLError,
    UnsupportedInstagramURLError,
    InstagramAuthRequiredError,
    InstagramPrivateContentError,
    InstagramMediaNotFoundError,
    InstagramFileTooLargeError,
)
