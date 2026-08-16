from __future__ import annotations

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from core.logger import logger
from handlers.start import build_back_keyboard
from instagram.parser import InstagramURLType, parse_instagram_url
from services.instagram import download_instagram, format_profile_message, get_instagram_profile
from services.sender import send_media_items


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except BadRequest as exc:
        if "not modified" in str(exc).lower():
            return
        logger.debug("Could not edit status message: %s", exc)


async def instagram_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status = await update.message.reply_text("🔎 Processing Instagram link...")

    async def _progress(text: str) -> None:
        await _safe_edit(status, text)

    try:
        parsed = parse_instagram_url(url)

        # Profile page → info card
        if parsed.url_type == InstagramURLType.PROFILE:
            await _safe_edit(status, "👤 Fetching profile info...")
            profile, err = await get_instagram_profile(url)
            if err or not profile:
                await _safe_edit(status, err or "❌ Could not fetch profile.")
                return

            text = format_profile_message(profile)
            try:
                await status.delete()
            except Exception:
                pass

            if profile.profile_pic_url:
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=profile.profile_pic_url,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_to_message_id=update.message.message_id,
                        reply_markup=build_back_keyboard(),
                    )
                    return
                except Exception as exc:
                    logger.warning("Could not send profile pic by URL: %s", exc)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_to_message_id=update.message.message_id,
                reply_markup=build_back_keyboard(),
            )
            return

        # Media (post / reel / story / tv)
        result = await download_instagram(url, progress=_progress)

        if not result.success or not result.items:
            await _safe_edit(status, result.error or "❌ Download failed")
            return

        await _safe_edit(status, "📤 Uploading to Telegram...")

        await send_media_items(
            context=context,
            chat_id=update.effective_chat.id,
            items=result.items,
            reply_to=update.message.message_id,
        )

        try:
            await status.delete()
        except Exception:
            pass

    except Exception:
        logger.exception("Unhandled Instagram error")
        try:
            await _safe_edit(status, "❌ Something went wrong processing that Instagram link.")
        except Exception:
            pass