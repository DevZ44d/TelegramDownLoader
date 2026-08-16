from __future__ import annotations

from core.exceptions import DownloaderError


class PinterestError(DownloaderError):
    pass


class InvalidPinterestURLError(PinterestError):
    pass


class PinterestMediaNotFoundError(PinterestError):
    pass


class PinterestNetworkError(PinterestError):
    pass


class PinterestExtractionError(PinterestError):
    pass