"""
Database configuration for RLCF Framework.

Provides SQLAlchemy base class and session management for
RLCF models (Tasks, Feedback, Users, etc.).

Supports both sync and async sessions:
- Sync: get_session() for simple scripts
- Async: get_async_session() for production/async code

References:
    RLCF.md Section 4 - Data Storage
    docs/02-methodology/rlcf/technical/database-schema.md
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import os

# SQLAlchemy declarative base for all RLCF models
Base = declarative_base()

# Default database URLs
DEFAULT_DATABASE_URL = "sqlite:///rlcf.db"
DEFAULT_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///rlcf.db"
DEFAULT_POSTGRES_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/merl_t_rlcf"

# Module-level engine and session factory (sync)
_engine = None
_SessionLocal = None

# Module-level async engine and session factory
_async_engine = None
_AsyncSessionLocal = None


def get_database_url() -> str:
    """
    Get database URL from environment or use default.

    Returns:
        Database connection URL
    """
    return os.environ.get("RLCF_DATABASE_URL", DEFAULT_DATABASE_URL)


def get_async_database_url() -> str:
    """
    Get async database URL from environment or use default.

    For PostgreSQL: postgresql+asyncpg://user:pass@host:port/db
    For SQLite: sqlite+aiosqlite:///path/to/db.sqlite

    Returns:
        Async database connection URL
    """
    url = os.environ.get("RLCF_ASYNC_DATABASE_URL")
    if url:
        return url

    # Check if PostgreSQL is configured
    pg_url = os.environ.get("RLCF_POSTGRES_URL")
    if pg_url:
        return pg_url

    return DEFAULT_ASYNC_DATABASE_URL


def init_db(database_url: Optional[str] = None) -> None:
    """
    Initialize database engine and create all tables.

    Args:
        database_url: Optional database URL override
    """
    global _engine, _SessionLocal

    url = database_url or get_database_url()
    _engine = create_engine(url, echo=False)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    # Create all tables
    Base.metadata.create_all(bind=_engine)


async def init_async_db(database_url: Optional[str] = None) -> None:
    """
    Initialize async database engine and create all tables.

    Args:
        database_url: Optional async database URL override

    Example:
        >>> await init_async_db("postgresql+asyncpg://user:pass@localhost/db")
    """
    global _async_engine, _AsyncSessionLocal

    url = database_url or get_async_database_url()

    _async_engine = create_async_engine(url, echo=False)
    _AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create all tables (need to run sync for metadata)
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session():
    """
    Get a sync database session.

    Yields:
        Database session that auto-closes

    Raises:
        RuntimeError: If database not initialized
    """
    if _SessionLocal is None:
        init_db()

    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Example:
        >>> async with get_async_session() as session:
        ...     result = await session.execute(select(User))

    Yields:
        AsyncSession that auto-closes

    Raises:
        RuntimeError: If async database not initialized
    """
    global _AsyncSessionLocal

    if _AsyncSessionLocal is None:
        await init_async_db()

    async with _AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine():
    """
    Get the database engine.

    Returns:
        SQLAlchemy engine

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        init_db()
    return _engine


def get_async_engine():
    """
    Get the async database engine.

    Returns:
        SQLAlchemy async engine

    Note:
        Call init_async_db() first if not yet initialized
    """
    return _async_engine
