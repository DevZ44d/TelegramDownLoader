from __future__ import annotations

from typing import Optional


def human_size(num_bytes: Optional[int]) -> str:
    if num_bytes is None:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def truncate(text: Optional[str], max_len: int = 200) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
