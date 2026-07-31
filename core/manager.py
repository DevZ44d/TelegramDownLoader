from __future__ import annotations

from telegram.ext import Application

from config import settings
from core.logger import logger
from core.telethon_client import telethon_client
from handlers import register_handlers


def build_application() -> Application:
    # Higher timeouts for large media uploads (default is too short)
    app = (
        Application.builder()
        .token(settings.bot_token)
        .concurrent_updates(True)
        .connect_timeout(30.0)
        .read_timeout(120.0)
        .write_timeout(120.0)
        .pool_timeout(30.0)
        .get_updates_read_timeout(60.0)
        .build()
    )
    register_handlers(app)
    return app


async def on_startup(app: Application) -> None:
    logger.info("Starting Telegram Downloader…")
    logger.info("Download directory: %s", settings.download_dir)

    if telethon_client is not None:
        await telethon_client.start()
        me = await telethon_client.get_me()
        name = me.first_name if me else "unknown"
        logger.info("Telethon user client started as %s", name)
        if not settings.session_string:
            logger.warning(
                "SESSION_STRING is empty – using file session. "
                "Stories & restricted content need a logged-in account."
            )
    else:
        logger.warning("Telethon client not available")

    bot_info = await app.bot.get_me()
    logger.info("Bot started as @%s (id=%s)", bot_info.username, bot_info.id)
    logger.info("Handlers registered. Bot is ready.")


async def on_shutdown(app: Application) -> None:
    if telethon_client is not None and telethon_client.is_connected():
        await telethon_client.disconnect()
        logger.info("Telethon client disconnected")
    logger.info("Shutdown complete")