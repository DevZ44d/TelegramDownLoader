from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from handlers.instagram import instagram_handler
from handlers.restricted import restricted_handler
from handlers.start import (
    CALLBACK_BACK_HOME,
    CALLBACK_FEATURES,
    back_home_callback,
    features_callback,
    start_handler,
)
from handlers.story import story_handler
from handlers.pinterest import pinterest_handler


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(back_home_callback, pattern=f"^{CALLBACK_BACK_HOME}$"))
    app.add_handler(CallbackQueryHandler(features_callback, pattern=f"^{CALLBACK_FEATURES}$"))

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

    # Instagram public media (reels, posts, tv, profile pictures)
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & filters.Regex(r"https?://(www\.)?instagram\.com/"),
            instagram_handler,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.TEXT
            & filters.Regex(
                r"https?://((www|[a-z]{2})\.)?(pin\.it/|pinterest\.[a-z.]+/)"
            ),
            pinterest_handler,
        )
    )
