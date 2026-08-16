"""
Download Pinterest media WITHOUT ffmpeg.

1) Scrape progressive .mp4 / images from the pin page (best, usually has audio)
2) yt-dlp with simple format "best" (no merge)
3) gallery-dl fallback (no format restrictions)
Never send separate silent-video + pure-audio pair.
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from config import settings
from core.logger import logger
from pinterest.exceptions import (
    PinterestMediaNotFoundError,
    PinterestNetworkError,
)


@dataclass(slots=True)
class DownloadedFile:
    path: Path
    media_type: str  # "video" | "image"
    mime_type: Optional[str] = None
    caption: Optional[str] = None


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _work_dir() -> Path:
    d = settings.download_dir / "temp" / "pinterest" / uuid.uuid4().hex[:12]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mime_for(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov", ".m4v"}


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _pick_files(files: list[Path]) -> list[DownloadedFile]:
    """Keep one best video OR one best image. Drop pure-audio files."""
    videos = sorted(
        [f for f in files if _is_video(f)],
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    images = sorted(
        [f for f in files if _is_image(f)],
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    result: list[DownloadedFile] = []
    if videos:
        v = videos[0]
        result.append(DownloadedFile(path=v, media_type="video", mime_type=_mime_for(v)))
    elif images:
        img = images[0]
        result.append(DownloadedFile(path=img, media_type="image", mime_type=_mime_for(img)))
    return result


def _download_http(url: str, dest: Path) -> Path:
    url = url.replace("\\u002F", "/").replace("\\/", "/").replace("&amp;", "&")
    with httpx.Client(
        timeout=90,
        follow_redirects=True,
        headers={
            "User-Agent": _UA,
            "Referer": "https://www.pinterest.com/",
            "Accept": "*/*",
        },
    ) as client:
        with client.stream("GET", url) as r:
            if r.status_code >= 400:
                raise PinterestNetworkError(f"HTTP {r.status_code} for media")
            with dest.open("wb") as f:
                for chunk in r.iter_bytes(65536):
                    f.write(chunk)
    if not dest.exists() or dest.stat().st_size < 500:
        raise PinterestMediaNotFoundError("Downloaded file is empty")
    return dest


def _clean_url(u: str) -> str:
    u = u.replace("\\u002F", "/").replace("\\/", "/").replace("\\u0026", "&")
    u = u.replace("&amp;", "&").rstrip("\\")
    return u


def _extract_pin_media_urls(url: str) -> tuple[list[str], list[str], Optional[str]]:
    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pinterest.com/",
    }
    video_urls: list[str] = []
    image_urls: list[str] = []
    caption: Optional[str] = None

    def add_video(u: str) -> None:
        u = _clean_url(u)
        if u.startswith("http") and u not in video_urls:
            video_urls.append(u)

    def add_image(u: str) -> None:
        u = _clean_url(u)
        if u.startswith("http") and u not in image_urls:
            image_urls.append(u)

    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        if r.status_code >= 400:
            raise PinterestNetworkError(f"Pin page HTTP {r.status_code}")
        html = r.text
        final_url = str(r.url)

        # Direct progressive MP4 / WEBM links in HTML (most reliable for audio)
        for m in re.finditer(
            r'https://(?:v\d*\.)?pinimg\.com/[^"\'\\\s<>]+?\.(?:mp4|webm)[^"\'\\\s<>]*',
            html,
            re.I,
        ):
            add_video(m.group(0))
        for m in re.finditer(
            r'https://[^"\'\\\s<>]*pinimg\.com/[^"\'\\\s<>]+\.(?:mp4|webm)[^"\'\\\s<>]*',
            html,
            re.I,
        ):
            add_video(m.group(0))

        def score(u: str) -> int:
            u = u.lower()
            s = 0
            for tag, pts in (
                ("1080", 100),
                ("720", 80),
                ("630", 60),
                ("480", 40),
                ("360", 20),
                ("expmp4", 10),
            ):
                if tag in u:
                    s += pts
            return s

        video_urls.sort(key=score, reverse=True)

        for m in re.finditer(
            r'https://i\.pinimg\.com/[^"\'\\\s<>]+\.(?:jpg|jpeg|png|webp)[^"\'\\\s<>]*',
            html,
            re.I,
        ):
            add_image(m.group(0))

        for script_id in ("__PWS_DATA__", "__PWS_INITIAL_PROPS__"):
            m = re.search(
                rf'<script id="{script_id}"[^>]*>(\{{.*?\}})</script>',
                html,
                re.DOTALL,
            )
            if not m:
                continue
            try:
                blob = json.loads(m.group(1))
            except Exception:
                continue

            def walk(obj, depth=0):
                if depth > 20:
                    return
                if isinstance(obj, dict):
                    if "video_list" in obj and isinstance(obj["video_list"], dict):
                        ranked = []
                        for k, v in obj["video_list"].items():
                            if isinstance(v, dict) and v.get("url"):
                                ranked.append(
                                    (v.get("height") or v.get("width") or 0, v["url"])
                                )
                        ranked.sort(reverse=True)
                        for _, u in ranked:
                            add_video(u)
                    for key in ("video_url", "contentUrl", "url"):
                        u = obj.get(key)
                        if isinstance(u, str) and any(
                            x in u.lower()
                            for x in (".mp4", ".webm", "pinimg.com/videos")
                        ):
                            add_video(u)
                    images = obj.get("images")
                    if isinstance(images, dict):
                        for prefer in ("orig", "originals", "736x", "564x", "474x"):
                            block = images.get(prefer)
                            if isinstance(block, dict) and block.get("url"):
                                add_image(block["url"])
                    for v in obj.values():
                        walk(v, depth + 1)
                elif isinstance(obj, list):
                    for v in obj:
                        walk(v, depth + 1)

            walk(blob)

        ogv = re.search(r'property="og:video(?::url)?"\s+content="([^"]+)"', html)
        if ogv:
            add_video(ogv.group(1))
        ogi = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if ogi:
            add_image(ogi.group(1))

        # ===== استخراج الكابشن (وصف الـ pin) =====
        # 1) من og:description
        ogd = re.search(r'property="og:description"\s+content="([^"]+)"', html)
        if ogd:
            caption = ogd.group(1).strip()

        # 2) من الـ JSON blobs
        if not caption:
            for script_id in ("__PWS_DATA__", "__PWS_INITIAL_PROPS__"):
                m = re.search(
                    rf'<script id="{script_id}"[^>]*>(\{{.*?\}})</script>',
                    html,
                    re.DOTALL,
                )
                if not m:
                    continue
                try:
                    blob = json.loads(m.group(1))
                except Exception:
                    continue

                def find_caption(obj, depth=0):
                    if depth > 18:
                        return None
                    if isinstance(obj, dict):
                        for key in (
                            "closeup_description",
                            "description",
                            "seo_description",
                            "grid_title",
                            "title",
                            "alt_text",
                            "rich_summary",
                        ):
                            val = obj.get(key)
                            if isinstance(val, str) and val.strip():
                                return val.strip()
                        for v in obj.values():
                            found = find_caption(v, depth + 1)
                            if found:
                                return found
                    elif isinstance(obj, list):
                        for v in obj:
                            found = find_caption(v, depth + 1)
                            if found:
                                return found
                    return None

                caption = find_caption(blob)
                if caption:
                    break

        # تنظيف بسيط
        if caption:
            caption = (
                caption.replace("&amp;", "&")
                .replace("&quot;", '"')
                .replace("&#39;", "'")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .strip()
            )
            if len(caption) > 1024:
                caption = caption[:1021] + "..."

        logger.debug(
            "Pinterest scrape %s → %s video(s), %s image(s), caption=%s",
            final_url,
            len(video_urls),
            len(image_urls),
            bool(caption),
        )

    return video_urls, image_urls, caption


def _download_via_page_sync(url: str, out_dir: Path) -> tuple[list[Path], Optional[str]]:
    video_urls, image_urls, caption = _extract_pin_media_urls(url)
    files: list[Path] = []

    for i, vurl in enumerate(video_urls[:3]):
        try:
            ext = ".webm" if ".webm" in vurl.lower() else ".mp4"
            dest = out_dir / f"pin_video_{i}{ext}"
            _download_http(vurl, dest)
            files.append(dest)
            logger.info(
                "Pinterest progressive video saved (%s bytes)", dest.stat().st_size
            )
            break
        except Exception as exc:
            logger.warning("Pinterest video URL failed: %s", exc)

    if not files:
        # صورة واحدة بس (الأولى الناجحة)
        for i, iurl in enumerate(image_urls[:3]):
            try:
                low = iurl.lower()
                ext = (
                    ".png"
                    if ".png" in low
                    else ".webp"
                    if ".webp" in low
                    else ".jpg"
                )
                dest = out_dir / f"pin_img_{i}{ext}"
                _download_http(iurl, dest)
                files.append(dest)
                break
            except Exception as exc:
                logger.debug("image url failed: %s", exc)

    return files, caption


def _download_ytdlp_sync(url: str, out_dir: Path) -> list[Path]:
    import yt_dlp

    class _Quiet:
        def debug(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "format": "best",
        "socket_timeout": 30,
        "logger": _Quiet(),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return sorted(
        [p for p in out_dir.iterdir() if p.is_file() and p.stat().st_size > 0],
        key=lambda p: p.stat().st_mtime,
    )


def _download_gallery_dl_sync(url: str, out_dir: Path) -> list[Path]:
    from gallery_dl import config as gdl_config
    from gallery_dl import job as gdl_job

    gdl_config.clear()
    gdl_config.set(("extractor",), "base-directory", str(out_dir))
    gdl_config.set(("extractor",), "directory", [])
    gdl_config.set(("extractor",), "filename", "{id}.{extension}")

    job = gdl_job.DownloadJob(url)
    job.run()

    return sorted(
        [p for p in out_dir.rglob("*") if p.is_file() and p.stat().st_size > 0],
        key=lambda p: p.stat().st_mtime,
    )


async def download_pinterest(url: str) -> list[DownloadedFile]:
    out_dir = _work_dir()
    last_err: Exception | None = None
    files: list[Path] = []
    caption: Optional[str] = None

    # أول حاجة نجرب الـ page-scrape (كويس جدًا للفيديوهات + بيجيب الكابشن)
    try:
        files, caption = await asyncio.to_thread(_download_via_page_sync, url, out_dir)
        if files:
            has_video = any(_is_video(f) for f in files)
            if has_video:
                logger.info("Pinterest page-scrape got %s file(s) for %s", len(files), url)
            else:
                # لو صور بس → نمسح اللي نزل ونروح على gallery-dl (بس نحتفظ بالكابشن)
                for f in files:
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        pass
                files = []
    except Exception as exc:
        last_err = exc
        logger.warning("Pinterest page-scrape failed for %s: %s", url, exc)

    # لو مفيش فيديو (أو فشل) → استخدم gallery-dl (ممتاز للصور)
    if not files:
        try:
            files = await asyncio.to_thread(_download_gallery_dl_sync, url, out_dir)
            if files:
                logger.info("Pinterest gallery-dl got %s file(s) for %s", len(files), url)
        except Exception as exc:
            last_err = exc
            logger.warning("Pinterest gallery-dl failed for %s: %s", url, exc)

    # آخر محاولة yt-dlp لو الاتنين فشلوا
    if not files:
        try:
            files = await asyncio.to_thread(_download_ytdlp_sync, url, out_dir)
            if files:
                logger.info("Pinterest yt-dlp got %s file(s) for %s", len(files), url)
        except Exception as exc:
            last_err = exc
            logger.warning("Pinterest yt-dlp failed for %s: %s", url, exc)

    if not files:
        msg = str(last_err) if last_err else "No media found"
        if "network" in msg.lower() or "http" in msg.lower():
            raise PinterestNetworkError(msg)
        raise PinterestMediaNotFoundError(msg)

    processed = _pick_files(files)
    if not processed:
        raise PinterestMediaNotFoundError(
            "Downloaded files were empty or unsupported."
        )

    # حط الكابشن على آخر ملف (زي إنستجرام بالظبط)
    if caption and processed:
        processed[-1].caption = caption

    return processed