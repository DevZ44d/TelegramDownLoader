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
        )


settings = Config.from_env()
