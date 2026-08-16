"""
Small helpers for the Instagram module: safe filenames, temp file
paths, and best-format selection. Kept separate from utils/files.py
because these are Instagram-specific (temp subdirectory, extension
guessing from mime/url) while utils/files.py stays generic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from config import settings

# Anything that is not a plain filename character is stripped. This blocks
# path traversal ("../"), absolute paths, and invalid Windows characters in
# one pass — nothing derived from Instagram-provided data is ever trusted
# to build a path directly.
_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')

_MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}


def sanitize_component(text: Optional[str], fallback: str = "instagram") -> str:
    """Turn arbitrary text into a safe, single path component."""
    if not text:
        return fallback
    cleaned = _UNSAFE_CHARS.sub("_", text).strip(" ._")
    cleaned = cleaned[:80]
    return cleaned or fallback


def guess_extension(url: Optional[str], mime_type: Optional[str], media_type: str) -> str:
    """Best-effort extension guess: mime type first, then URL path, then a safe default."""
    if mime_type and mime_type.lower() in _MIME_EXTENSIONS:
        return _MIME_EXTENSIONS[mime_type.lower()]

    if url:
        try:
            path = urlparse(url).path
        except ValueError:
            path = ""
        suffix = Path(path).suffix.lower()
        if suffix and len(suffix) <= 5 and re.fullmatch(r"\.[a-z0-9]+", suffix):
            return suffix

    return ".mp4" if media_type == "video" else ".jpg"


def instagram_temp_dir() -> Path:
    """downloads/temp/instagram — created on demand, never left behind full of stale files."""
    temp_dir = settings.download_dir / "temp" / "instagram"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def unique_instagram_path(
    extension: str,
    *,
    author: Optional[str] = None,
    shortcode: Optional[str] = None,
    index: Optional[int] = None,
) -> Path:
    """Build a safe, unique destination path inside downloads/temp/instagram/."""
    temp_dir = instagram_temp_dir()

    parts = [sanitize_component(author, "ig")]
    if shortcode:
        parts.append(sanitize_component(shortcode, "post"))
    if index is not None:
        parts.append(f"{index:02d}")
    parts.append(uuid4().hex[:8])

    ext = extension if extension.startswith(".") else f".{extension}"
    filename = "_".join(parts) + ext

    # Final safety net: resolve and confirm the path never escapes temp_dir.
    candidate = (temp_dir / filename).resolve()
    if temp_dir.resolve() not in candidate.parents:
        candidate = temp_dir.resolve() / f"{uuid4().hex}{ext}"
    return candidate
