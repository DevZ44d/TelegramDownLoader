from __future__ import annotations

from abc import ABC, abstractmethod

from instagram.models import ExtractorResult


class BaseInstagramExtractor(ABC):
    """
    Common interface every Instagram extraction backend implements.

    The rest of the app (manager, service, handler) only ever talks to
    this interface — never to parth-dl / gallery-dl / Instaloader
    objects directly — so backends can be added, removed, or reordered
    without touching anything else.
    """

    name: str = "base"

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """Return True if this backend supports the given Instagram URL."""
        raise NotImplementedError

    @abstractmethod
    async def extract(self, url: str) -> ExtractorResult:
        """
        Extract normalized metadata (not the media files themselves) for
        `url`. Raise an instagram.exceptions.InstagramError subclass on
        failure — never return a generic Exception uncaught.
        """
        raise NotImplementedError
