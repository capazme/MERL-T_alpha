"""
Shared fixtures for orchestration tests.

This module provides shared pytest fixtures for testing the orchestration layer.
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment variables BEFORE importing app
os.environ["ORCHESTRATION_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["RATE_LIMITING_ENABLED"] = "false"  # Disable rate limiting for most tests

from merlt.orchestration.api.database import Base
from merlt.orchestration.api.models import ApiKey, ApiUsage


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine with in-memory SQLite."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,  # No connection pooling for SQLite
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted transactions


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client for rate limiting tests."""
    client = AsyncMock()
    client.zremrangebyscore = AsyncMock(return_value=0)
    client.zcard = AsyncMock(return_value=0)
    client.zadd = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_cache_service():
    """Mock cache service for tests."""
    service = MagicMock()
    service.get_redis_client = AsyncMock(return_value=None)  # Simulate Redis unavailable
    service.get = AsyncMock(return_value=None)
    service.set = AsyncMock(return_value=True)
    service.delete = AsyncMock(return_value=True)
    return service