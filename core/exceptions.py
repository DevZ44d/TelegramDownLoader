"""
Custom exception hierarchy.
"""

from __future__ import annotations


class DownloaderError(Exception):
    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class InvalidLinkError(DownloaderError):
    pass


class StoryNotFoundError(DownloaderError):
    pass


class MediaNotFoundError(DownloaderError):
    pass


class AccessDeniedError(DownloaderError):
    pass


class DownloadFailedError(DownloaderError):
    pass


class ClientNotReadyError(DownloaderError):
    pass


class UnsupportedMediaError(DownloaderError):
    pass
