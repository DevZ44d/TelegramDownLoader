from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from config import settings
from core.logger import logger


def ensure_download_dir() -> Path:
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    return settings.download_dir


def unique_filename(extension: str, prefix: str = "") -> Path:
    ensure_download_dir()
    return settings.download_dir / f"{prefix}{uuid4().hex}{extension}"


def safe_remove(path: Optional[Path | str]) -> None:
    if not path:
        return
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            p.unlink()
            logger.debug("Removed temporary file: %s", p)
    except OSError as exc:
        logger.warning("Failed to remove %s: %s", path, exc)


def extension_from_mime(mime: Optional[str], fallback: str = ".bin") -> str:
    if not mime:
        return fallback
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/x-wav": ".wav",
        "application/pdf": ".pdf",
    }
    return mapping.get(mime.lower(), fallback)
