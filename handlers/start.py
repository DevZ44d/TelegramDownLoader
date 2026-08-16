from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import KeyboardButtonStyle, ParseMode
from telegram.ext import ContextTypes

from config import settings

CALLBACK_BACK_HOME = "back_home"
CALLBACK_FEATURES = "features"


def build_home_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                "Developer 👨‍💻",
                url=settings.developer_url,
                style=KeyboardButtonStyle.PRIMARY,
            ),
            InlineKeyboardButton(
                "Features 📚",
                callback_data=CALLBACK_FEATURES,
                style=KeyboardButtonStyle.DANGER,
            ),
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


def build_features_keyboard() -> InlineKeyboardMarkup:
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


def build_home_text(user: User | None) -> str:
    if user:
        safe_name = escape(user.first_name or "User")
        mention = f'<a href="tg://user?id={user.id}">{safe_name}</a>'
    else:
        mention = "User"

    return (
        f"👋 Hello ¦ <tg-spoiler>{mention}</tg-spoiler> !\n\n"
        "— Drop any link ( <strong>Telegram</strong>, <strong>Instagram</strong>, <strong>Pinterest</strong> ) — Stories, public posts, or restricted media.\n\n"
        "— and I'll pull it for you in <i>seconds</i>."
    )


def build_features_text() -> str:
    return ("""
💠 ¦ Download restricted content from Telegram:
🏷 Just send the message link.

💠 ¦ Download Telegram stories:
🏷 Send the story link.

💠 ¦ Download from Instagram:
🏷 Send a reel, post, story, or profile link.

💠 ¦ Download from Pinterest:
🏷 Send a pin.it or pinterest.com link (photos & videos).
    """)


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


async def features_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit the current message to the Features view (no delete)."""
    query = update.callback_query
    if not query or not query.message:
        return

    await query.answer()

    try:
        await query.edit_message_text(
            text=build_features_text(),
            reply_markup=build_features_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        # Fallback if edit fails
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=build_features_text(),
            reply_markup=build_features_keyboard(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )


async def back_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Back button behavior:
    - If pressed from Features view → edit message back to home.
    - If pressed from a media message → delete media, then send home.
    """
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

    # Try to edit back to home (works for Features text message)
    if query.message and query.message.text is not None:
        try:
            await query.edit_message_text(
                text=build_home_text(update.effective_user),
                reply_markup=build_home_keyboard(),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
        except Exception:
            pass

    # Media messages can't be edited to text → delete then send home
    if query.message:
        try:
            await query.message.delete()
        except Exception:
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
