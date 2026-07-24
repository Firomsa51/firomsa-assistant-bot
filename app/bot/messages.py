"""Handle free-text messages and reply keyboard shortcuts."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.ai.assistant import generate_response
from app.ai.memory import load_history, save_message
from app.ai.prompts import (
    BLOCKED_MESSAGE,
    RATE_LIMIT_MESSAGE,
    build_system_prompt,
)
from app.bot.keyboards import main_menu_keyboard
from app.database.connection import AsyncSessionLocal
from app.services.business_service import get_business_profile
from app.services.user_service import get_or_create_user
from app.utils.logger import logger

# In-memory per-user rate-limit counter {telegram_id: (count, window_start)}
import time
_rate_counters: dict[int, tuple[int, float]] = {}


def _check_rate_limit(telegram_id: int, limit: int) -> bool:
    """Return True if the user is within the rate limit."""
    from app.config import settings

    now = time.monotonic()
    count, window_start = _rate_counters.get(telegram_id, (0, now))

    if now - window_start > 60:
        # New window
        _rate_counters[telegram_id] = (1, now)
        return True

    if count >= limit:
        return False

    _rate_counters[telegram_id] = (count + 1, window_start)
    return True


# Map reply-keyboard buttons to command text
_SHORTCUT_MAP = {
    "📋 Services": "/services",
    "ℹ️ About Us": "/about",
    "📞 Contact": "/contact",
    "❓ Help": "/help",
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route incoming text messages through AI or to shortcut commands."""
    if not update.effective_user or not update.message or not update.message.text:
        return

    tg_user = update.effective_user
    text = update.message.text.strip()

    # Handle reply-keyboard shortcuts
    if text in _SHORTCUT_MAP:
        cmd = _SHORTCUT_MAP[text]
        # Fake the command by calling the handler directly
        update.message.text = cmd
        if cmd == "/services":
            from app.bot.commands import cmd_services
            await cmd_services(update, context)
        elif cmd == "/about":
            from app.bot.commands import cmd_about
            await cmd_about(update, context)
        elif cmd == "/contact":
            from app.bot.commands import cmd_contact
            await cmd_contact(update, context)
        elif cmd == "/help":
            from app.bot.commands import cmd_help
            await cmd_help(update, context)
        return

    async with AsyncSessionLocal() as session:
        user, is_new = await get_or_create_user(
            session,
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
        )

        if user.is_blocked:
            await update.message.reply_text(BLOCKED_MESSAGE)
            return

        from app.config import settings
        if not _check_rate_limit(tg_user.id, settings.rate_limit_per_minute):
            await update.message.reply_text(RATE_LIMIT_MESSAGE)
            return

        # Load conversation history & business profile
        history = await load_history(session, user)
        profile = await get_business_profile(session)
        system_prompt = build_system_prompt(profile)

        # Generate AI response
        try:
            await update.message.chat.send_action("typing")
            reply = await generate_response(system_prompt, history, text)
        except Exception as exc:
            logger.error("ai.generation_failed", error=str(exc), telegram_id=tg_user.id)
            await update.message.reply_text(
                "⚠️ I'm having trouble right now. Please try again in a moment."
            )
            return

        # Persist both messages
        await save_message(session, user, "user", text)
        await save_message(session, user, "assistant", reply)
        await session.commit()

    await update.message.reply_text(
        reply,
        reply_markup=main_menu_keyboard(),
    )

    logger.info(
        "message.handled",
        telegram_id=tg_user.id,
        username=tg_user.username,
        input_length=len(text),
        output_length=len(reply),
    )
