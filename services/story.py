from __future__ import annotations

from core.exceptions import DownloaderError
from core.logger import logger
from models.media import DownloadResult
from services.parser import ParsedLink
from tg.story import fetch_story


async def download_story(parsed: ParsedLink) -> DownloadResult:
    if not parsed.peer or parsed.story_id is None:
        return DownloadResult(
            success=False,
            error="The story link is invalid",
            source_link=parsed.raw,
        )

    try:
        items = await fetch_story(parsed.peer, parsed.story_id)
        return DownloadResult(success=True, items=items, source_link=parsed.raw)
    except DownloaderError as exc:
        logger.warning("Story download failed: %s", exc.message)
        return DownloadResult(success=False, error=exc.message, source_link=parsed.raw)
    except Exception as exc:
        logger.exception("Unexpected story error")
        return DownloadResult(success=False, error=str(exc), source_link=parsed.raw)
