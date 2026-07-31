from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from utils.regex import is_private_invite, match_public_post, match_story


class LinkType(str, Enum):
    STORY = "story"
    PUBLIC_POST = "public_post"
    PRIVATE_INVITE = "private_invite"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ParsedLink:
    link_type: LinkType
    raw: str
    peer: Optional[str] = None
    story_id: Optional[int] = None
    message_id: Optional[int] = None
    to_message_id: Optional[int] = None


def parse_link(text: str) -> ParsedLink:
    text = text.strip()

    m = match_story(text)
    if m:
        return ParsedLink(
            link_type=LinkType.STORY,
            raw=text,
            peer=m.group("peer"),
            story_id=int(m.group("story_id")),
        )

    if is_private_invite(text):
        return ParsedLink(link_type=LinkType.PRIVATE_INVITE, raw=text)

    m = match_public_post(text)
    if m:
        msg_id = int(m.group("msg_id"))
        to_id = m.group("to_id")
        return ParsedLink(
            link_type=LinkType.PUBLIC_POST,
            raw=text,
            peer=m.group("username"),
            message_id=msg_id,
            to_message_id=int(to_id) if to_id else msg_id,
        )

    return ParsedLink(link_type=LinkType.UNKNOWN, raw=text)
