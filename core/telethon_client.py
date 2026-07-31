"""
Telethon user client – used for Stories + restricted content.
"""

from __future__ import annotations

from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import settings
from core.exceptions import ClientNotReadyError
from core.logger import logger

_client: Optional[TelegramClient] = None


def create_telethon() -> Optional[TelegramClient]:
    global _client

    if settings.session_string:
        try:
            _client = TelegramClient(
                StringSession(settings.session_string),
                settings.api_id,
                settings.api_hash,
            )
            logger.info("Telethon client created (StringSession)")
            return _client
        except Exception as exc:
            logger.error("Invalid SESSION_STRING: %s – falling back to file session", exc)

    _client = TelegramClient(
        settings.session_account_name,
        settings.api_id,
        settings.api_hash,
    )
    logger.info("Telethon client created (file session)")
    return _client


def get_telethon() -> TelegramClient:
    if _client is None:
        raise ClientNotReadyError("Telethon client is not initialized")
    return _client


telethon_client: Optional[TelegramClient] = create_telethon()
