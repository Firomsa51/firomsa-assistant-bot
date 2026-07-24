"""Register all Telegram handlers on the Application."""
from __future__ import annotations

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.commands import (
    cmd_about,
    cmd_admin,
    cmd_block,
    cmd_broadcast,
    cmd_clear,
    cmd_contact,
    cmd_help,
    cmd_services,
    cmd_settings,
    cmd_start,
    cmd_stats,
    cmd_unblock,
)
from app.bot.messages import handle_message
from app.utils.logger import logger


async def handle_callback_query(update, context) -> None:
    """Dispatch inline keyboard callback queries."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""

    if data == "admin:stats":
        # Reuse the stats command logic
        await cmd_stats(update, context)
    elif data == "admin:broadcast":
        await query.edit_message_text(
            "📢 To broadcast, use:\n`/broadcast Your message here`",
            parse_mode="Markdown",
        )
    elif data == "admin:settings":
        await query.edit_message_text(
            "⚙️ To view/edit settings, use:\n`/settings`",
            parse_mode="Markdown",
        )
    elif data == "admin:logs":
        await query.edit_message_text(
            "📝 Conversation logs are stored in the database.\nUse your database viewer or /stats for aggregates."
        )
    elif data == "cancel":
        await query.edit_message_text("❌ Action cancelled.")
    else:
        logger.warning("callback.unknown", data=data)


def register_handlers(app: Application) -> None:
    """Attach all handlers to the Telegram Application instance."""

    # Core commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("contact", cmd_contact))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("clear", cmd_clear))

    # Admin commands
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("block", cmd_block))
    app.add_handler(CommandHandler("unblock", cmd_unblock))
    app.add_handler(CommandHandler("settings", cmd_settings))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Free-text message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("handlers.registered")
