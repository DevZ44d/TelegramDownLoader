from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "gif"
    VOICE = "voice"
    AUDIO = "audio"
    STICKER = "sticker"
    DOCUMENT = "document"
    ANIMATION = "animation"
    STORY_PHOTO = "story_photo"
    STORY_VIDEO = "story_video"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class MediaItem:
    media_type: MediaType
    file_path: Optional[Path] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None
    is_story: bool = False
    story_id: Optional[int] = None
    peer: Optional[str] = None


@dataclass(slots=True)
class DownloadResult:
    success: bool
    items: list[MediaItem] = field(default_factory=list)
    error: Optional[str] = None
    source_link: Optional[str] = None

    @property
    def has_media(self) -> bool:
        return bool(self.items)
