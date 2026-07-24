"""User CRUD operations and statistics."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User
from app.utils.logger import logger


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> tuple[User, bool]:
    """
    Get an existing user or create a new one.
    Returns (user, created).
    """
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        is_admin = telegram_id in settings.admin_ids_list
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_admin=is_admin,
        )
        session.add(user)
        await session.flush()
        logger.info("user.created", telegram_id=telegram_id, username=username)
        return user, True

    # Update mutable fields
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.language_code = language_code
    user.last_seen = datetime.now(timezone.utc)
    user.message_count = (user.message_count or 0) + 1

    # Promote to admin if in config list and not already
    if telegram_id in settings.admin_ids_list and not user.is_admin:
        user.is_admin = True
        logger.info("user.promoted_to_admin", telegram_id=telegram_id)

    await session.flush()
    return user, False


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def block_user(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_blocked = True
    await session.flush()
    logger.info("user.blocked", telegram_id=telegram_id)
    return True


async def unblock_user(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return False
    user.is_blocked = False
    await session.flush()
    logger.info("user.unblocked", telegram_id=telegram_id)
    return True


async def get_all_active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.is_blocked == False)
    )
    return list(result.scalars().all())


async def get_user_stats(session: AsyncSession) -> dict:
    total = await session.execute(select(func.count(User.id)))
    blocked = await session.execute(
        select(func.count(User.id)).where(User.is_blocked == True)
    )
    admins = await session.execute(
        select(func.count(User.id)).where(User.is_admin == True)
    )
    total_messages = await session.execute(select(func.sum(User.message_count)))

    return {
        "total_users": total.scalar() or 0,
        "blocked_users": blocked.scalar() or 0,
        "admin_users": admins.scalar() or 0,
        "total_messages": total_messages.scalar() or 0,
    }
