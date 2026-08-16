from __future__ import annotations

import pytest

from instagram.exceptions import (
    InstagramAuthRequiredError,
    InstagramExtractionError,
    InstagramNetworkError,
)
from instagram.extractors.base import BaseInstagramExtractor
from instagram.manager import InstagramExtractorManager
from instagram.models import ExtractorResult, InstagramMedia, InstagramMediaItem

POST_URL = "https://www.instagram.com/p/CzXyzAbC1/"


class DummyExtractor(BaseInstagramExtractor):
    """A fake extractor for testing fallback behaviour without hitting the network."""

    def __init__(self, name: str, *, handles: bool = True, error: Exception | None = None, media: InstagramMedia | None = None):
        self.name = name
        self._handles = handles
        self._error = error
        self._media = media
        self.calls = 0

    async def can_handle(self, url: str) -> bool:
        return self._handles

    async def extract(self, url: str) -> ExtractorResult:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return ExtractorResult(success=True, media=self._media, extractor=self.name)


def _sample_media() -> InstagramMedia:
    return InstagramMedia(
        shortcode="CzXyzAbC1",
        author="someuser",
        media_type="post",
        items=[InstagramMediaItem(url="https://cdn.example/a.jpg", media_type="image")],
    )


@pytest.mark.asyncio
async def test_first_extractor_success_short_circuits():
    first = DummyExtractor("first", media=_sample_media())
    second = DummyExtractor("second", media=_sample_media())
    manager = InstagramExtractorManager(extractors=[first, second])

    result = await manager.extract(POST_URL)

    assert result.success
    assert result.extractor == "first"
    assert first.calls == 1
    assert second.calls == 0


@pytest.mark.asyncio
async def test_transient_error_falls_back_to_next_extractor():
    first = DummyExtractor("first", error=InstagramNetworkError("boom"))
    second = DummyExtractor("second", media=_sample_media())
    manager = InstagramExtractorManager(extractors=[first, second])

    result = await manager.extract(POST_URL)

    assert result.success
    assert result.extractor == "second"
    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_permanent_error_stops_the_chain():
    first = DummyExtractor("first", error=InstagramAuthRequiredError("login required"))
    second = DummyExtractor("second", media=_sample_media())
    manager = InstagramExtractorManager(extractors=[first, second])

    with pytest.raises(InstagramAuthRequiredError):
        await manager.extract(POST_URL)

    assert first.calls == 1
    assert second.calls == 0


@pytest.mark.asyncio
async def test_all_extractors_fail_raises_last_error():
    first = DummyExtractor("first", error=InstagramNetworkError("network down"))
    second = DummyExtractor("second", error=InstagramExtractionError("parse failed"))
    manager = InstagramExtractorManager(extractors=[first, second])

    with pytest.raises(InstagramExtractionError):
        await manager.extract(POST_URL)


@pytest.mark.asyncio
async def test_extractor_that_cannot_handle_url_is_skipped():
    first = DummyExtractor("first", handles=False)
    second = DummyExtractor("second", media=_sample_media())
    manager = InstagramExtractorManager(extractors=[first, second])

    result = await manager.extract(POST_URL)

    assert result.extractor == "second"
    assert first.calls == 0


@pytest.mark.asyncio
async def test_invalid_url_never_reaches_extractors():
    first = DummyExtractor("first", media=_sample_media())
    manager = InstagramExtractorManager(extractors=[first])

    with pytest.raises(InstagramExtractionError):
        await manager.extract("https://t.me/somechannel/10")

    assert first.calls == 0
