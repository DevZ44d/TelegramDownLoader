#!/usr/bin/env python3
"""
Telegram Downloader – Entry point (python-telegram-bot + Telethon).

Features:
  • Telegram Stories (photo / video)
  • Public channel posts
  • Restricted content (when user account has access)
  • Photos, Videos, Documents, Voice, Audio, Animations, Stickers
  • Colored InlineKeyboardButton styles (primary / success / danger)
"""

from __future__ import annotations

import sys

from core.logger import logger
from core.manager import build_application, on_shutdown, on_startup


def main() -> None:
    app = build_application()
    app.post_init = on_startup
    app.post_shutdown = on_shutdown

    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Shutting down by user request")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
