"""Business profile settings and FAQ management."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BusinessSetting
from app.utils.logger import logger

# Default business profile – admins can override via /settings command
DEFAULT_SETTINGS: dict[str, str] = {
    "business_name": "Firomsa Business",
    "business_description": "A professional business providing top-quality services to customers.",
    "services": "• Consultation\n• Customer Support\n• Product Information\n• Order Processing",
    "working_hours": "Monday – Friday: 9:00 AM – 6:00 PM\nSaturday: 10:00 AM – 4:00 PM\nSunday: Closed",
    "location": "Addis Ababa, Ethiopia",
    "phone": "+251 911 000 000",
    "email": "contact@firomsa.com",
    "website": "https://firomsa.com",
    "faq": (
        "Q: How do I place an order?\n"
        "A: Simply describe what you need and our team will assist you.\n\n"
        "Q: What are your payment methods?\n"
        "A: We accept bank transfer, mobile money, and cash on delivery.\n\n"
        "Q: How long does delivery take?\n"
        "A: Standard delivery is 2-5 business days depending on your location."
    ),
    "support_rules": (
        "Be professional and empathetic. "
        "Always greet users warmly. "
        "Provide accurate information. "
        "Escalate complex issues to human support. "
        "Never make promises the business cannot keep."
    ),
}


async def ensure_defaults(session: AsyncSession) -> None:
    """Insert default settings if they don't exist."""
    for key, value in DEFAULT_SETTINGS.items():
        result = await session.execute(
            select(BusinessSetting).where(BusinessSetting.key == key)
        )
        if result.scalar_one_or_none() is None:
            session.add(BusinessSetting(key=key, value=value))
    await session.flush()
    logger.info("business_settings.defaults_ensured")


async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(
        select(BusinessSetting).where(BusinessSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row:
        return row.value
    return DEFAULT_SETTINGS.get(key)


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(
        select(BusinessSetting).where(BusinessSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        session.add(BusinessSetting(key=key, value=value))
    await session.flush()
    logger.info("business_settings.updated", key=key)


async def get_business_profile(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(BusinessSetting))
    rows = result.scalars().all()
    profile = dict(DEFAULT_SETTINGS)
    for row in rows:
        profile[row.key] = row.value
    return profile
