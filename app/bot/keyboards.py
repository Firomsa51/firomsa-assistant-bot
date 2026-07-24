"""Telegram reply and inline keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard shown to all users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            ["📋 Services", "ℹ️ About Us"],
            ["📞 Contact", "❓ Help"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Type a message or pick an option…",
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for the admin panel."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("📊 Stats", callback_data="admin:stats"),
                InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast"),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin:settings"),
                InlineKeyboardButton("📝 Logs", callback_data="admin:logs"),
            ],
        ]
    )


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Generic yes/no inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            ]
        ]
    )
