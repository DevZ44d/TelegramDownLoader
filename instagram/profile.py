"""
Fetch public Instagram profile metadata.
Uses INSTAGRAM_COOKIES from .env when available (optional).
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import httpx

from config import settings
from core.logger import logger
from instagram.exceptions import (
    InstagramExtractionError,
    InstagramMediaNotFoundError,
    InstagramNetworkError,
    InstagramPrivateContentError,
    InstagramRateLimitedError,
)


@dataclass(slots=True)
class InstagramProfile:
    username: str
    full_name: str = ""
    biography: str = ""
    external_url: Optional[str] = None
    followers: int = 0
    following: int = 0
    posts: int = 0
    is_private: bool = False
    is_verified: bool = False
    is_business: bool = False
    category: Optional[str] = None
    profile_pic_url: Optional[str] = None
    user_id: Optional[str] = None
    bio_links: list[str] = field(default_factory=list)
    pronouns: Optional[str] = None


def _fmt_count(n: int) -> str:
    """Human-readable count with full number in parentheses when abbreviated."""
    if n >= 1_000_000_000:
        short = f"{n / 1_000_000_000:.2f}B".rstrip("0").rstrip(".")
        return f"{short} ({n:,})"
    if n >= 1_000_000:
        short = f"{n / 1_000_000:.2f}M".rstrip("0").rstrip(".")
        return f"{short} ({n:,})"
    if n >= 1_000:
        short = f"{n / 1_000:.1f}K".rstrip("0").rstrip(".")
        return f"{short} ({n:,})"
    return f"{n:,}"


def format_profile_message(p: InstagramProfile) -> str:
    lines = [f"👤 <b>@{p.username}</b>"]
    if p.full_name:
        lines.append(f"📝 {p.full_name}")
    badges = []
    if p.is_verified:
        badges.append("✅ Verified")
    if p.is_business:
        badges.append("🏢 Business")
    if p.is_private:
        badges.append("🔒 Private")
    if badges:
        lines.append(" · ".join(badges))
    if p.category:
        lines.append(f"🏷️ {p.category}")
    if p.pronouns:
        lines.append(f"🗣️ {p.pronouns}")

    lines.append("")
    lines.append(f"👥 <b>{_fmt_count(p.followers)}</b> followers")
    lines.append(f"➡️ <b>{_fmt_count(p.following)}</b> following")
    lines.append(f"🖼️ <b>{_fmt_count(p.posts)}</b> posts")

    if p.biography:
        lines.append("")
        lines.append(f"💬 {p.biography}")

    links = list(p.bio_links)
    if p.external_url and p.external_url not in links:
        links.insert(0, p.external_url)
    if links:
        lines.append("")
        for link in links[:5]:
            lines.append(f"🔗 {link}")

    if p.user_id:
        lines.append("")
        lines.append(f"🆔 <code>{p.user_id}</code>")

    lines.append("")
    lines.append(f"🌐 https://www.instagram.com/{p.username}/")
    return "\n".join(lines)


def _upgrade_profile_pic(url: Optional[str]) -> Optional[str]:
    """Strip s150x150 / s320x320 size limits for higher quality."""
    if not url:
        return None
    url = re.sub(r"/s\d+x\d+", "", url)
    url = re.sub(r"/c\d+\.\d+\.\d+\.\d+", "", url)
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "stp" in qs:
            stp = qs["stp"][0]
            stp = re.sub(r"_s\d+x\d+", "", stp)
            stp = re.sub(r"s\d+x\d+", "", stp)
            qs["stp"] = [stp]
            new_query = urlencode({k: v[0] for k, v in qs.items()})
            url = urlunparse(parsed._replace(query=new_query))
    except Exception:
        pass
    return url


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        value = value.get("count", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_cookie_jar() -> Optional[MozillaCookieJar]:
    path = settings.instagram_cookies
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        logger.warning("INSTAGRAM_COOKIES path set but file not found: %s", path)
        return None
    try:
        jar = MozillaCookieJar(str(p))
        jar.load(ignore_discard=True, ignore_expires=True)
        logger.info("Loaded Instagram cookies from %s (%s cookies)", p.name, len(jar))
        return jar
    except Exception as exc:
        logger.warning("Failed to load cookies from %s: %s", path, exc)
        return None


def _client_headers(username: str) -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "359341",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://www.instagram.com/{username}/",
        "Origin": "https://www.instagram.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


async def fetch_instagram_profile(username: str) -> InstagramProfile:
    try:
        return await asyncio.to_thread(_fetch_via_web_api, username)
    except InstagramRateLimitedError:
        logger.warning("web_profile_info rate-limited for @%s — trying HTML", username)
    except Exception as exc:
        logger.debug("web_profile_info failed for @%s: %s", username, exc)

    try:
        return await asyncio.to_thread(_fetch_via_html, username)
    except InstagramRateLimitedError:
        raise
    except Exception as exc:
        logger.debug("HTML scrape failed for @%s: %s", username, exc)

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_via_instaloader, username),
            timeout=20.0,
        )
    except asyncio.TimeoutError as exc:
        raise InstagramRateLimitedError(
            "Instagram is rate-limiting. Wait a few minutes, or add INSTAGRAM_COOKIES in .env."
        ) from exc
    except InstagramRateLimitedError:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "429" in msg or "too many" in msg or "wait" in msg:
            raise InstagramRateLimitedError(
                "Instagram is rate-limiting. Wait a few minutes, or add INSTAGRAM_COOKIES in .env."
            ) from exc
        raise InstagramExtractionError(f"Could not fetch profile @{username}: {exc}") from exc


def _fetch_via_web_api(username: str) -> InstagramProfile:
    jar = _load_cookie_jar()
    headers = _client_headers(username)
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"

    with httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers=headers,
        cookies=jar,
    ) as client:
        r = client.get(url)
        if r.status_code == 429:
            raise InstagramRateLimitedError("Rate limited")
        if r.status_code == 404:
            raise InstagramMediaNotFoundError(f"Profile @{username} not found.")
        if r.status_code in (401, 403):
            raise InstagramPrivateContentError(f"Cannot access @{username}.")
        if r.status_code >= 400:
            raise InstagramNetworkError(f"Profile API HTTP {r.status_code}")

        user = ((r.json().get("data") or {}).get("user")) or {}
        if not user:
            raise InstagramMediaNotFoundError(f"Profile @{username} not found.")
        return _profile_from_user_dict(user, username)


def _fetch_via_html(username: str) -> InstagramProfile:
    jar = _load_cookie_jar()
    headers = {
        **_client_headers(username),
        "Accept": "text/html,application/xhtml+xml",
    }
    url = f"https://www.instagram.com/{username}/"

    with httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers=headers,
        cookies=jar,
    ) as client:
        r = client.get(url)
        if r.status_code == 429:
            raise InstagramRateLimitedError("Rate limited")
        if r.status_code == 404:
            raise InstagramMediaNotFoundError(f"Profile @{username} not found.")
        if r.status_code >= 400:
            raise InstagramNetworkError(f"HTML HTTP {r.status_code}")

        html = r.text

        m = re.search(r"window\._sharedData\s*=\s*(\{.+?\});</script>", html)
        if m:
            data = json.loads(m.group(1))
            user = (
                data.get("entry_data", {})
                .get("ProfilePage", [{}])[0]
                .get("graphql", {})
                .get("user")
            )
            if user:
                return _profile_from_user_dict(user, username)

        for m in re.finditer(
            r'<script type="application/json"[^>]*>(\{.*?\})</script>',
            html,
            re.DOTALL,
        ):
            try:
                blob = json.loads(m.group(1))
                user = _find_user_in_json(blob, username)
                if user:
                    return _profile_from_user_dict(user, username)
            except Exception:
                continue

        raise InstagramExtractionError(f"Could not parse profile page for @{username}")


def _find_user_in_json(obj, username: str, depth: int = 0):
    if depth > 14:
        return None
    if isinstance(obj, dict):
        uname = obj.get("username")
        has_counts = any(
            k in obj
            for k in (
                "edge_followed_by",
                "follower_count",
                "edge_follow",
                "biography",
                "profile_pic_url_hd",
            )
        )
        if uname == username and has_counts:
            return obj
        for v in obj.values():
            found = _find_user_in_json(v, username, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_user_in_json(v, username, depth + 1)
            if found:
                return found
    return None


def _extract_bio_links(user: dict) -> list[str]:
    links: list[str] = []
    for key in ("bio_links", "biography_with_entities"):
        raw = user.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    u = item.get("url") or item.get("link")
                    if u:
                        links.append(str(u))
                elif isinstance(item, str) and item.startswith("http"):
                    links.append(item)
        elif isinstance(raw, dict):
            entities = raw.get("entities") or []
            for ent in entities:
                if isinstance(ent, dict) and ent.get("url"):
                    links.append(str(ent["url"]))
    seen = set()
    out = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _profile_from_user_dict(user: dict, username: str) -> InstagramProfile:
    followers = _safe_int(
        user.get("edge_followed_by")
        or user.get("follower_count")
        or user.get("followers")
    )
    following = _safe_int(
        user.get("edge_follow")
        or user.get("following_count")
        or user.get("follows")
        or user.get("followees")
    )
    posts = _safe_int(
        user.get("edge_owner_to_timeline_media")
        or user.get("media_count")
        or user.get("posts")
        or user.get("total_posts")
    )

    pic = None
    hd_info = user.get("hd_profile_pic_url_info") or user.get("hd_profile_pic_versions")
    if isinstance(hd_info, dict) and hd_info.get("url"):
        pic = hd_info["url"]
    elif isinstance(hd_info, list) and hd_info:
        best = max(hd_info, key=lambda x: (x.get("width") or 0) if isinstance(x, dict) else 0)
        if isinstance(best, dict):
            pic = best.get("url")
    pic = (
        pic
        or user.get("profile_pic_url_hd")
        or user.get("profile_pic_url")
        or user.get("profile_pic")
    )
    pic = _upgrade_profile_pic(pic)

    category = (
        user.get("category_name")
        or user.get("business_category_name")
        or user.get("category")
    )
    pronouns = None
    if isinstance(user.get("pronouns"), list) and user["pronouns"]:
        pronouns = " / ".join(str(x) for x in user["pronouns"])
    elif isinstance(user.get("pronouns"), str):
        pronouns = user["pronouns"]

    return InstagramProfile(
        username=user.get("username") or username,
        full_name=user.get("full_name") or user.get("fullName") or "",
        biography=user.get("biography") or user.get("bio") or "",
        external_url=user.get("external_url") or user.get("externalUrl") or None,
        followers=followers,
        following=following,
        posts=posts,
        is_private=bool(user.get("is_private") or user.get("isPrivate")),
        is_verified=bool(user.get("is_verified") or user.get("isVerified")),
        is_business=bool(
            user.get("is_business_account")
            or user.get("is_business")
            or user.get("isBusinessAccount")
        ),
        category=str(category) if category else None,
        profile_pic_url=pic,
        user_id=str(user.get("id") or user.get("pk") or user.get("pk_id") or "") or None,
        bio_links=_extract_bio_links(user),
        pronouns=pronouns,
    )


def _fetch_via_instaloader(username: str) -> InstagramProfile:
    import instaloader
    import instaloader.exceptions as ilx

    loader = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=1,
    )

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except ilx.TooManyRequestsException as exc:
        raise InstagramRateLimitedError("Rate limited") from exc
    except ilx.ProfileNotExistsException as exc:
        raise InstagramMediaNotFoundError(f"Profile @{username} not found.") from exc
    except ilx.ConnectionException as exc:
        if "429" in str(exc) or "too many" in str(exc).lower():
            raise InstagramRateLimitedError("Rate limited") from exc
        raise InstagramNetworkError(str(exc)) from exc

    pic = _upgrade_profile_pic(profile.profile_pic_url)

    return InstagramProfile(
        username=profile.username,
        full_name=profile.full_name or "",
        biography=profile.biography or "",
        external_url=profile.external_url,
        followers=int(profile.followers),
        following=int(profile.followees),
        posts=int(profile.mediacount),
        is_private=bool(profile.is_private),
        is_verified=bool(profile.is_verified),
        is_business=bool(getattr(profile, "is_business_account", False)),
        category=getattr(profile, "business_category_name", None) or None,
        profile_pic_url=pic,
        user_id=str(profile.userid),
        bio_links=[],
        pronouns=None,
    )