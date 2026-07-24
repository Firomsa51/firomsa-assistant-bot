"""Conversation memory: load and save message history per user."""
from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Conversation, User


async def load_history(session: AsyncSession, user: User) -> list[dict[str, str]]:
    """
    Load the last N messages for a user as a list of {role, content} dicts
    suitable for passing directly to the Groq chat completion API.
    """
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(settings.max_history_messages)
    )
    rows = list(reversed(result.scalars().all()))
    return [{"role": row.role, "content": row.content} for row in rows]


async def save_message(
    session: AsyncSession,
    user: User,
    role: str,
    content: str,
) -> None:
    """Persist a single message to the conversation history."""
    session.add(Conversation(user_id=user.id, role=role, content=content))
    await session.flush()

    # Prune oldest messages beyond the window to keep the table tidy
    keep_limit = settings.max_history_messages * 2
    subq = (
        select(Conversation.id)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(keep_limit)
        .scalar_subquery()
    )
    await session.execute(
        delete(Conversation).where(
            Conversation.user_id == user.id,
            Conversation.id.not_in(subq),
        )
    )


async def clear_history(session: AsyncSession, user: User) -> int:
    """Delete all conversation history for a user. Returns deleted count."""
    result = await session.execute(
        select(Conversation).where(Conversation.user_id == user.id)
    )
    rows = result.scalars().all()
    count = len(rows)
    await session.execute(
        delete(Conversation).where(Conversation.user_id == user.id)
    )
    return count
