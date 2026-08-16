"""Detect and normalize Pinterest URLs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

_PIN_IT = re.compile(r"https?://(www\.)?pin\.it/[\w-]+", re.I)
_PINTEREST = re.compile(
    r"https?://([a-z]{2}\.)?(www\.)?pinterest\.[a-z.]+/"
    r"(pin/\d+|[\w.-]+/[\w.-]+|[\w.-]+)",
    re.I,
)


class PinterestURLType(str, Enum):
    PIN = "pin"
    BOARD = "board"
    PROFILE = "profile"
    SHORT = "short"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParsedPinterestURL:
    url: str
    url_type: PinterestURLType
    pin_id: str | None = None


def is_pinterest_url(text: str) -> bool:
    text = (text or "").strip()
    if not text.startswith("http"):
        return False
    return bool(_PIN_IT.search(text) or _PINTEREST.search(text))


def parse_pinterest_url(url: str) -> ParsedPinterestURL:
    url = (url or "").strip()
    if _PIN_IT.search(url):
        return ParsedPinterestURL(url=url, url_type=PinterestURLType.SHORT)

    m = re.search(r"pinterest\.[a-z.]+/pin/(\d+)", url, re.I)
    if m:
        return ParsedPinterestURL(url=url, url_type=PinterestURLType.PIN, pin_id=m.group(1))

    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0] not in ("pin", "search"):
        return ParsedPinterestURL(url=url, url_type=PinterestURLType.BOARD)
    if len(parts) == 1:
        return ParsedPinterestURL(url=url, url_type=PinterestURLType.PROFILE)

    return ParsedPinterestURL(url=url, url_type=PinterestURLType.UNKNOWN)