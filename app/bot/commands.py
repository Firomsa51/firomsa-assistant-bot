"""Telegram command handlers (/start, /help, /about, /contact, /services, admin commands)."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.ai.memory import clear_history
from app.ai.prompts import ADMIN_WELCOME, WELCOME_MESSAGE
from app.bot.keyboards import admin_menu_keyboard, main_menu_keyboard
from app.database.connection import AsyncSessionLocal
from app.database.models import Broadcast
from app.services.business_service import get_business_profile, get_setting, set_setting
from app.services.user_service import (
    block_user,
    get_all_active_users,
    get_user_by_telegram_id,
    get_user_stats,
    unblock_user,
)
from app.utils.logger import logger


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — greet the user and show the main menu."""
    if not update.effective_user or not update.message:
        return

    async with AsyncSessionLocal() as session:
        profile = await get_business_profile(session)

    welcome = WELCOME_MESSAGE.format(business_name=profile.get("business_name", "Firomsa"))
    await update.message.reply_text(
        welcome,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )

    if update.effective_user and update.effective_user.id in __import__(
        "app.config", fromlist=["settings"]
    ).settings.admin_ids_list:
        await update.message.reply_text(ADMIN_WELCOME, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show available commands."""
    if not update.message:
        return
    text = (
        "🤖 *Firomsa Assistant — Help*\n\n"
        "Here's what I can do for you:\n\n"
        "• Just type any question and I'll answer with AI\n"
        "• /services — List all our services\n"
        "• /about — About this business\n"
        "• /contact — Contact information\n"
        "• /clear — Clear your conversation history\n\n"
        "Need human support? Use /contact to reach our team."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about — show business description."""
    if not update.message:
        return
    async with AsyncSessionLocal() as session:
        name = await get_setting(session, "business_name")
        desc = await get_setting(session, "business_description")
        hours = await get_setting(session, "working_hours")

    text = (
        f"🏢 *{name}*\n\n"
        f"{desc}\n\n"
        f"🕐 *Working Hours*\n{hours}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /contact — show contact details."""
    if not update.message:
        return
    async with AsyncSessionLocal() as session:
        phone = await get_setting(session, "phone")
        email = await get_setting(session, "email")
        location = await get_setting(session, "location")
        website = await get_setting(session, "website")

    text = (
        "📞 *Contact Us*\n\n"
        f"📍 Location: {location}\n"
        f"📞 Phone: {phone}\n"
        f"📧 Email: {email}\n"
        f"🌐 Website: {website}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /services — list all services."""
    if not update.message:
        return
    async with AsyncSessionLocal() as session:
        name = await get_setting(session, "business_name")
        services = await get_setting(session, "services")

    text = f"📋 *Services offered by {name}*\n\n{services}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — erase conversation history for this user."""
    if not update.message or not update.effective_user:
        return
    from app.services.user_service import get_user_by_telegram_id  # local import to avoid circular

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, update.effective_user.id)
        if user:
            count = await clear_history(session, user)
            await session.commit()
            await update.message.reply_text(
                f"🗑️ Cleared {count} messages from your history. Fresh start!"
            )
        else:
            await update.message.reply_text("No history found to clear.")


# ─── Admin commands ────────────────────────────────────────────────────────────

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin — show admin panel (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("⛔ This command is for administrators only.")
        return
    await update.message.reply_text(
        "🔐 *Admin Panel*\nChoose an action:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="Markdown",
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats — display user statistics (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("⛔ Admins only.")
        return

    async with AsyncSessionLocal() as session:
        stats = await get_user_stats(session)

    text = (
        "📊 *User Statistics*\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"🚫 Blocked: {stats['blocked_users']}\n"
        f"🔐 Admins: {stats['admin_users']}\n"
        f"💬 Total messages: {stats['total_messages']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broadcast <message> — send a message to all active users (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("⛔ Admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast <your message>\n\nExample: /broadcast Hello everyone! 🎉"
        )
        return

    message_text = " ".join(context.args)
    broadcast_text = f"📢 *Broadcast Message*\n\n{message_text}"

    async with AsyncSessionLocal() as session:
        users = await get_all_active_users(session)
        sent = 0
        failed = 0
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=broadcast_text,
                    parse_mode="Markdown",
                )
                sent += 1
            except Exception as exc:
                logger.warning("broadcast.failed", telegram_id=user.telegram_id, error=str(exc))
                failed += 1

        session.add(
            Broadcast(
                admin_telegram_id=update.effective_user.id,
                message=message_text,
                recipients_count=sent,
            )
        )
        await session.commit()

    await update.message.reply_text(
        f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )


async def cmd_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /block <telegram_id> — block a user (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("⛔ Admins only.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /block <telegram_user_id>")
        return

    target_id = int(context.args[0])
    async with AsyncSessionLocal() as session:
        success = await block_user(session, target_id)
        await session.commit()

    if success:
        await update.message.reply_text(f"🚫 User {target_id} has been blocked.")
    else:
        await update.message.reply_text(f"User {target_id} not found in the database.")


async def cmd_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unblock <telegram_id> — unblock a user (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings
    if update.effective_user.id not in settings.admin_ids_list:
        await update.message.reply_text("⛔ Admins only.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /unblock <telegram_user_id>")
        return

    target_id = int(context.args[0])
    async with AsyncSessionLocal() as session:
        success = await unblock_user(session, target_id)
        await session.commit()

    if success:
        await update.message.reply_text(f"✅ User {target_id} has been unblocked.")
    else:
        await update.message.reply_text(f"User {target_id} not found in the database.")


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings [key] [value] — view or update business settings (admin-only)."""
    if not update.message or not update.effective_user:
        return
    from app.config import settings as app_settings
    if update.effective_user.id not in app_settings.admin_ids_list:
        await update.message.reply_text("⛔ Admins only.")
        return

    args = context.args or []

    if not args:
        # Show all settings
        async with AsyncSessionLocal() as session:
            profile = await get_business_profile(session)
        lines = ["⚙️ *Business Settings*\n"]
        for key, value in profile.items():
            short = value[:80].replace("\n", " ") + ("…" if len(value) > 80 else "")
            lines.append(f"• `{key}`: {short}")
        lines.append("\nTo update: /settings <key> <new value>")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /settings <key> <value>\nExample: /settings phone +251 900 000 000"
        )
        return

    key = args[0]
    value = " ".join(args[1:])
    from app.services.business_service import DEFAULT_SETTINGS
    if key not in DEFAULT_SETTINGS:
        valid_keys = ", ".join(f"`{k}`" for k in DEFAULT_SETTINGS)
        await update.message.reply_text(
            f"Unknown key. Valid keys: {valid_keys}", parse_mode="Markdown"
        )
        return

    async with AsyncSessionLocal() as session:
        await set_setting(session, key, value)
        await session.commit()

    await update.message.reply_text(f"✅ Setting `{key}` updated successfully.", parse_mode="Markdown")
