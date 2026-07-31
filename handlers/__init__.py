from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.restricted import restricted_handler
from handlers.start import CALLBACK_BACK_HOME, back_home_callback, start_handler
from handlers.story import story_handler


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(back_home_callback, pattern=f"^{CALLBACK_BACK_HOME}$"))

    # Stories first (more specific pattern)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.Regex(r"https?://t\.me/[\w\d_]+/s/\d+"),
            story_handler,
        )
    )

    # Public / restricted posts
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & filters.Regex(r"https?://t\.me/")
            & ~filters.Regex(r"https?://t\.me/[\w\d_]+/s/\d+"),
            restricted_handler,
        )
    )