"""Async database engine and session dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

# Engine is created lazily-connecting: import is safe, no connection until first use.
engine = create_async_engine(
    _settings.sqlalchemy_url,
    pool_pre_ping=True,
    future=True,
    echo=False,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with SessionLocal() as session:
        yield session
