from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    api_id: int
    api_hash: str
    bot_token: str
    session_string: str | None
    session_account_name: str
    developer_url: str
    channel_url: str
    download_dir: Path
    max_file_size_mb: int
    log_level: str

    # Instagram module
    instagram_enabled: bool
    instagram_max_file_size_mb: int
    instagram_max_concurrent_downloads: int
    instagram_timeout: int
    instagram_max_retries: int
    instagram_enable_metadata: bool
    instagram_cookies: str | None
    instagram_username: str | None
    instagram_password: str | None

    @classmethod
    def from_env(cls) -> "Config":
        api_id = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")
        bot_token = os.getenv("BOT_TOKEN")

        if not api_id or not api_hash or not bot_token:
            raise RuntimeError(
                "Missing required environment variables: API_ID, API_HASH, BOT_TOKEN"
            )

        session_string = os.getenv("SESSION_STRING") or None
        if session_string is not None and not session_string.strip():
            session_string = None

        download_dir = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
        download_dir.mkdir(parents=True, exist_ok=True)

        cookies = (os.getenv("INSTAGRAM_COOKIES") or "").strip() or None
        ig_user = (os.getenv("INSTAGRAM_USERNAME") or "").strip() or None
        ig_pass = (os.getenv("INSTAGRAM_PASSWORD") or "").strip() or None

        return cls(
            api_id=int(api_id),
            api_hash=api_hash.strip(),
            bot_token=bot_token.strip(),
            session_string=session_string,
            session_account_name=os.getenv("SESSION_ACCOUNT_NAME", "session_account"),
            developer_url=os.getenv("DEVELOPER_URL", "https://t.me/DevGit"),
            channel_url=os.getenv("CHANNEL_URL", "https://t.me/PyCodz"),
            download_dir=download_dir,
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "2000")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            instagram_enabled=os.getenv("INSTAGRAM_ENABLED", "true").strip().lower() == "true",
            instagram_max_file_size_mb=int(os.getenv("INSTAGRAM_MAX_FILE_SIZE_MB", "2000")),
            instagram_max_concurrent_downloads=int(os.getenv("INSTAGRAM_MAX_CONCURRENT_DOWNLOADS", "3")),
            instagram_timeout=int(os.getenv("INSTAGRAM_TIMEOUT", "30")),
            instagram_max_retries=int(os.getenv("INSTAGRAM_MAX_RETRIES", "2")),
            instagram_enable_metadata=os.getenv("INSTAGRAM_ENABLE_METADATA", "true").strip().lower() == "true",
            instagram_cookies=cookies,
            instagram_username=ig_user,
            instagram_password=ig_pass,
        )


settings = Config.from_env()
