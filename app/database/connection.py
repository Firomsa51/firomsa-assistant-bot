"""Async SQLAlchemy engine, session factory, and Base."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# asyncpg doesn't accept sslmode in the URL; pass it via connect_args instead
_ssl_mode = settings.db_ssl_mode
if _ssl_mode in (None, "disable", "allow"):
    _connect_args: dict = {"ssl": False}
else:
    # "require", "verify-ca", "verify-full"
    _connect_args = {"ssl": True}

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables that don't already exist."""
    async with engine.begin() as conn:
        from app.database import models  # noqa: F401 – registers all models
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine connection pool on shutdown."""
    await engine.dispose()
