"""
Instagram public-media downloader module.

Integrated feature of the TelegramDownLoader bot — NOT a standalone
package, CLI, or library. Only publicly accessible Instagram content
(reels, posts, videos, images, carousels, public profile pictures) is
supported. No login, cookies, sessions, or authentication bypass of
any kind is implemented or attempted.
"""

from __future__ import annotations

from instagram.parser import InstagramURL, InstagramURLType, is_instagram_url, parse_instagram_url

__all__ = [
    "InstagramURL",
    "InstagramURLType",
    "is_instagram_url",
    "parse_instagram_url",
]
