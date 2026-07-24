"""FastAPI Telegram webhook endpoint and health check."""
from __future__ import annotations

import hmac
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from telegram import Update

from app.config import settings
from app.utils.logger import logger

router = APIRouter()

# Will be set by main.py after the Application is initialised
_telegram_app = None


def set_telegram_app(app: Any) -> None:
    global _telegram_app
    _telegram_app = app


@router.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint used by Render and load balancers."""
    return {"status": "ok", "service": settings.app_name}


@router.post("/telegram/webhook", tags=["Telegram"])
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Receive Telegram updates via webhook.

    Telegram sends the secret token in the X-Telegram-Bot-Api-Secret-Token header.
    We verify it using a constant-time comparison to prevent timing attacks.
    """
    # Verify the secret token
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "",
        settings.telegram_webhook_secret,
    ):
        logger.warning(
            "webhook.invalid_secret",
            provided=bool(x_telegram_bot_api_secret_token),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    if _telegram_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot not initialised",
        )

    body = await request.json()
    update = Update.de_json(body, _telegram_app.bot)

    await _telegram_app.process_update(update)

    return {"status": "processed"}
