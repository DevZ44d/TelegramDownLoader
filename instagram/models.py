"""
Unified Instagram media models.

These are independent of any specific extractor library (parth-dl,
gallery-dl, Instaloader) so the rest of the app never depends on a
third-party extractor's own data shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class InstagramMediaItem:
    """A single downloadable file (one image/video, possibly part of a carousel)."""

    url: str
    media_type: str  # "image" | "video"
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None  # known ahead of download, if the extractor reports it


@dataclass(slots=True)
class InstagramMedia:
    """Normalized metadata for one Instagram post/reel/tv/profile-picture."""

    shortcode: Optional[str] = None
    author: Optional[str] = None
    caption: Optional[str] = None
    media_type: str = "post"  # "post" | "reel" | "carousel" | "profile_picture"
    thumbnail_url: Optional[str] = None
    items: list[InstagramMediaItem] = field(default_factory=list)


@dataclass(slots=True)
class ExtractorResult:
    """Result of a single extractor's attempt to extract metadata."""

    success: bool
    media: Optional[InstagramMedia] = None
    extractor: Optional[str] = None
    error: Optional[str] = None


@dataclass(slots=True)
class DownloadedInstagramItem:
    """One InstagramMediaItem after it has been downloaded to a local file."""

    item: InstagramMediaItem
    path: Path


@dataclass(slots=True)
class InstagramDownloadResult:
    """Final result of the extract + download pipeline for one Instagram URL."""

    success: bool
    source_url: str
    files: list[DownloadedInstagramItem] = field(default_factory=list)
    media: Optional[InstagramMedia] = None
    extractor: Optional[str] = None
    error: Optional[str] = None
