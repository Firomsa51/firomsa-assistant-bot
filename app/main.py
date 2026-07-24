"""FastAPI application factory and lifecycle management."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from telegram.ext import Application

from app.bot.handlers import register_handlers
from app.config import settings
from app.database.connection import close_db, init_db
from app.services.business_service import ensure_defaults
from app.database.connection import AsyncSessionLocal
from app.utils.logger import logger, setup_logging
from app.webhook import router as webhook_router, set_telegram_app

# Initialise logging immediately
setup_logging(debug=settings.debug)

# ─── Telegram Application (global, shared) ────────────────────────────────────
telegram_app: Application | None = None


async def _setup_telegram() -> Application:
    """
    Build and start the python-telegram-bot Application.

    Mode selection:
    - WEBHOOK_URL set  → webhook mode (production / Render)
    - WEBHOOK_URL unset → polling mode (local development / Replit)
    """
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    register_handlers(app)
    await app.initialize()
    await app.start()

    if settings.webhook_url:
        # ── Webhook mode ─────────────────────────────────────────────────────
        await app.bot.set_webhook(
            url=settings.webhook_endpoint,
            secret_token=settings.telegram_webhook_secret,
            allowed_updates=["message", "callback_query"],
        )
        logger.info("telegram.webhook_set", url=settings.webhook_endpoint)
    else:
        # ── Polling mode (development fallback) ───────────────────────────────
        # Delete any stale webhook so polling is not blocked
        await app.bot.delete_webhook(drop_pending_updates=False)
        await app.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=False,
        )
        logger.info(
            "telegram.polling_started",
            hint="Set WEBHOOK_URL to switch to webhook mode for production.",
        )

    return app


async def _teardown_telegram(app: Application) -> None:
    """Stop and shutdown the Telegram Application gracefully."""
    try:
        if settings.webhook_url:
            await app.bot.delete_webhook()
        elif app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("telegram.shutdown_complete")
    except Exception as exc:
        logger.error("telegram.shutdown_error", error=str(exc))


# ─── FastAPI lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):  # type: ignore[type-arg]
    global telegram_app

    logger.info("startup.begin", app=settings.app_name)

    # 1. Database
    await init_db()
    logger.info("startup.db_ready")

    # 2. Seed default business settings
    async with AsyncSessionLocal() as session:
        await ensure_defaults(session)
        await session.commit()
    logger.info("startup.settings_ready")

    # 3. Telegram bot
    telegram_app = await _setup_telegram()
    set_telegram_app(telegram_app)
    logger.info("startup.telegram_ready")

    logger.info("startup.complete", port=settings.port)
    yield

    # ─── Shutdown ───────────────────────────────────────────────────────────
    logger.info("shutdown.begin")
    if telegram_app:
        await _teardown_telegram(telegram_app)
    await close_db()
    logger.info("shutdown.complete")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered Telegram business assistant",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(webhook_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
