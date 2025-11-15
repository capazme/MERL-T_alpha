"""
Database configuration for MERL-T Orchestration API.

This module provides async SQLAlchemy engine, session management, and
database initialization for the orchestration layer.

Supports:
- PostgreSQL (production, via asyncpg)
- SQLite (development/testing, via aiosqlite)
"""

import os
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# ============================================================================
# Database URL Configuration
# ============================================================================

# Get database URL from environment variable
# Default to SQLite for development (change to PostgreSQL in production)
DATABASE_URL = os.getenv(
    "ORCHESTRATION_DATABASE_URL",
    "sqlite+aiosqlite:///./orchestration.db"
)

# ============================================================================
# Engine Configuration
# ============================================================================

# Determine database type
is_sqlite = DATABASE_URL.startswith("sqlite")
is_postgres = DATABASE_URL.startswith("postgresql")

# Convert SQLite URL to async version if needed
if is_sqlite and "aiosqlite" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

# Create async engine with appropriate settings
if is_sqlite:
    # SQLite doesn't support pool_size/max_overflow
    engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        future=True,
    )
else:
    # PostgreSQL with connection pooling
    engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        future=True,
    )

# ============================================================================
# SQLite-Specific Event Listeners
# ============================================================================

if is_sqlite:
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """
        Enable foreign keys and performance settings for SQLite.

        - foreign_keys=ON: Enforce FK constraints
        - journal_mode=WAL: Write-Ahead Logging for better concurrency
        - synchronous=NORMAL: Balance between safety and performance
        """
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# ============================================================================
# Session Factory
# ============================================================================

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Don't expire objects after commit (for async)
)

# ============================================================================
# Declarative Base
# ============================================================================

Base = declarative_base()

# ============================================================================
# Database Initialization
# ============================================================================

async def init_db() -> None:
    """
    Initialize database: create all tables defined in models.

    This should be called on application startup.
    For production, use migrations instead (001_create_orchestration_tables.sql).
    """
    async with engine.begin() as conn:
        # Import models to register them with Base
        from . import models  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """
    Drop all tables (useful for testing).

    WARNING: This will delete all data!
    Only use in development/testing environments.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_db() -> None:
    """
    Close database connections.

    This should be called on application shutdown.
    """
    await engine.dispose()


# ============================================================================
# Dependency Injection for FastAPI
# ============================================================================

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Yields:
        AsyncSession: Database session

    Usage:
        @app.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            # Use session here
            pass
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ============================================================================
# Session Dependency
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Usage in FastAPI:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session
            ...

    Yields:
        AsyncSession: Database session
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ============================================================================
# Database Info
# ============================================================================

def get_database_info() -> dict:
    """
    Get database configuration information.

    Returns:
        dict: Database type, URL (sanitized), pool settings
    """
    # Sanitize URL (hide password)
    sanitized_url = DATABASE_URL
    if "@" in DATABASE_URL:
        parts = DATABASE_URL.split("@")
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            sanitized_url = DATABASE_URL.replace(user_pass, f"{user}:***")

    return {
        "database_type": "sqlite" if is_sqlite else "postgresql",
        "database_url": sanitized_url,
        "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
        "max_overflow": engine.pool._max_overflow if hasattr(engine.pool, '_max_overflow') else None,
        "is_async": True,
        "sqlalchemy_version": "2.0+",
    }
