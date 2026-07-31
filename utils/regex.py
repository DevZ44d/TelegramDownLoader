from __future__ import annotations

import re
from typing import Match, Optional

STORY_PATTERN = re.compile(
    r"^https?://t\.me/(?P<peer>[\w\d_]+)/s/(?P<story_id>\d+)/?$",
    re.IGNORECASE,
)

PUBLIC_POST_PATTERN = re.compile(
    r"^https?://t\.me/(?P<username>[\w\d_]+)/(?P<msg_id>\d+)(?:-(?P<to_id>\d+))?/?$",
    re.IGNORECASE,
)

PRIVATE_INVITE_PATTERN = re.compile(
    r"^https?://t\.me/(?:\+|joinchat/)[\w\d_-]+/?$",
    re.IGNORECASE,
)

ANY_TME_PATTERN = re.compile(r"https?://t\.me/", re.IGNORECASE)


def match_story(url: str) -> Optional[Match[str]]:
    return STORY_PATTERN.match(url.strip())


def match_public_post(url: str) -> Optional[Match[str]]:
    return PUBLIC_POST_PATTERN.match(url.strip())


def is_private_invite(url: str) -> bool:
    return bool(PRIVATE_INVITE_PATTERN.match(url.strip()))


def is_telegram_link(text: str) -> bool:
    return bool(ANY_TME_PATTERN.search(text))
