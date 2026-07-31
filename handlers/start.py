from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import KeyboardButtonStyle, ParseMode
from telegram.ext import ContextTypes

from config import settings

CALLBACK_BACK_HOME = "back_home"


def build_home_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                "Developer 👨‍💻",
                url=settings.developer_url,
                style=KeyboardButtonStyle.PRIMARY,
            )
        ],
    ]
    if settings.channel_url:
        rows.append(
            [
                InlineKeyboardButton(
                    "🧚‍♀️",
                    url=settings.channel_url,
                    style=KeyboardButtonStyle.SUCCESS,
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def build_home_text(user: User | None) -> str:
    if user:
        safe_name = escape(user.first_name or "User")
        mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'
    else:
        mention = "User"

    return (
        f"👋 Hello ¦ {mention} !\n\n"
        "— Drop any Telegram link — Stories, public posts, or restricted media — "
        "— and I'll pull it for you in seconds."
    )


def build_back_keyboard() -> InlineKeyboardMarkup:
    """Red Back button attached to delivered media."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=CALLBACK_BACK_HOME,
                    style=KeyboardButtonStyle.DANGER,
                )
            ]
        ]
    )


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    await update.message.reply_text(
        build_home_text(update.effective_user),
        reply_markup=build_home_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def back_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Back button → delete media message, then show main interface."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    chat_id = (
        query.message.chat_id
        if query.message
        else (update.effective_chat.id if update.effective_chat else None)
    )
    if chat_id is None:
        return

    # Delete the media message that had the Back button
    if query.message:
        try:
            await query.message.delete()
        except Exception:
            # Fallback: remove keyboard if delete is not allowed
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=build_home_text(update.effective_user),
        reply_markup=build_home_keyboard(),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )