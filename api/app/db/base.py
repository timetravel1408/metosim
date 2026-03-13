"""Database engine and session management (async SQLAlchemy).

Provides connection pool initialization, session factory, and
the declarative base for ORM models.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("metosim.api.db")


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> Optional[AsyncEngine]:
    """Return the current database engine."""
    return _engine


async def init_db() -> None:
    """Initialize the async database engine and session factory."""
    global _engine, _session_factory

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://metosim:password@localhost:5432/metosim",
    )

    pool_size = int(os.environ.get("DATABASE_POOL_SIZE", "5"))
    max_overflow = int(os.environ.get("DATABASE_MAX_OVERFLOW", "10"))

    try:
        _engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=os.environ.get("DEBUG", "false").lower() == "true",
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Database engine initialized", extra={"pool_size": pool_size})
    except Exception as e:
        logger.warning(f"Database initialization deferred: {e}")
        _engine = None
        _session_factory = None


async def close_db() -> None:
    """Close the database engine and release all connections."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    Yields:
        AsyncSession instance. Automatically closed after use.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
