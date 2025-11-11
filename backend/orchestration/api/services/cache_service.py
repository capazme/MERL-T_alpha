"""
Cache Service for MERL-T Orchestration API.

This module provides Redis caching operations for:
- Query status caching
- User session management
- Rate limiting
- General key-value caching

All operations are async using redis-py.
"""

import json
import os
from datetime import timedelta
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis


class CacheService:
    """
    Singleton service for Redis caching operations.

    Provides async caching methods for orchestration API.
    """

    _instance: Optional["CacheService"] = None
    _redis_client: Optional[Redis] = None

    def __new__(cls) -> "CacheService":
        """Singleton pattern: ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize cache service."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    async def _get_redis_client(self) -> Optional[Redis]:
        """
        Get or create Redis client.

        Returns:
            Redis client or None if disabled
        """
        if not self._enabled:
            return None

        if self._redis_client is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD", None)

            self._redis_client = await aioredis.from_url(
                f"redis://{redis_host}:{redis_port}/{redis_db}",
                password=redis_password,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

        return self._redis_client

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

    # ========================================================================
    # Query Status Cache
    # ========================================================================

    async def set_query_status(
        self,
        trace_id: str,
        status_data: Dict[str, Any],
        ttl_hours: int = 24,
    ) -> bool:
        """
        Cache query status.

        Args:
            trace_id: Query trace identifier
            status_data: Status data to cache
            ttl_hours: Time-to-live in hours (default: 24h)

        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            key = f"query_status:{trace_id}"
            value = json.dumps(status_data)
            ttl = timedelta(hours=ttl_hours)

            await redis.setex(key, ttl, value)
            return True

        except Exception as e:
            print(f"Redis error in set_query_status: {e}")
            return False

    async def get_query_status(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached query status.

        Args:
            trace_id: Query trace identifier

        Returns:
            Status data dict or None if not found
        """
        if not self._enabled:
            return None

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return None

            key = f"query_status:{trace_id}"
            value = await redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            print(f"Redis error in get_query_status: {e}")
            return None

    async def delete_query_status(self, trace_id: str) -> bool:
        """
        Delete cached query status.

        Args:
            trace_id: Query trace identifier

        Returns:
            bool: True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            key = f"query_status:{trace_id}"
            await redis.delete(key)
            return True

        except Exception as e:
            print(f"Redis error in delete_query_status: {e}")
            return False

    # ========================================================================
    # User Session Management
    # ========================================================================

    async def set_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl_days: int = 7,
    ) -> bool:
        """
        Cache user session.

        Args:
            session_id: Session identifier
            session_data: Session data to cache
            ttl_days: Time-to-live in days (default: 7d)

        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            key = f"session:{session_id}"
            value = json.dumps(session_data)
            ttl = timedelta(days=ttl_days)

            await redis.setex(key, ttl, value)
            return True

        except Exception as e:
            print(f"Redis error in set_session: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user session.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        if not self._enabled:
            return None

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return None

            key = f"session:{session_id}"
            value = await redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            print(f"Redis error in get_session: {e}")
            return None

    # ========================================================================
    # Rate Limiting
    # ========================================================================

    async def increment_rate_limit(
        self,
        identifier: str,
        window_seconds: int = 3600,
    ) -> int:
        """
        Increment rate limit counter for an identifier.

        Args:
            identifier: User/API key identifier
            window_seconds: Time window in seconds (default: 1 hour)

        Returns:
            int: Current count in window
        """
        if not self._enabled:
            return 0

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return 0

            key = f"rate_limit:{identifier}"

            # Increment counter
            count = await redis.incr(key)

            # Set expiration on first increment
            if count == 1:
                await redis.expire(key, window_seconds)

            return count

        except Exception as e:
            print(f"Redis error in increment_rate_limit: {e}")
            return 0

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 100,
    ) -> tuple[bool, int]:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: User/API key identifier
            max_requests: Maximum requests allowed

        Returns:
            Tuple of (allowed: bool, current_count: int)
        """
        if not self._enabled:
            return True, 0

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return True, 0

            key = f"rate_limit:{identifier}"
            count = await redis.get(key)

            current_count = int(count) if count else 0
            allowed = current_count < max_requests

            return allowed, current_count

        except Exception as e:
            print(f"Redis error in check_rate_limit: {e}")
            return True, 0

    async def reset_rate_limit(self, identifier: str) -> bool:
        """
        Reset rate limit counter for an identifier.

        Args:
            identifier: User/API key identifier

        Returns:
            bool: True if reset, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            key = f"rate_limit:{identifier}"
            await redis.delete(key)
            return True

        except Exception as e:
            print(f"Redis error in reset_rate_limit: {e}")
            return False

    # ========================================================================
    # General Cache Operations
    # ========================================================================

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set a cache value.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl_seconds: Optional TTL in seconds

        Returns:
            bool: True if set successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            serialized_value = json.dumps(value)

            if ttl_seconds:
                await redis.setex(key, ttl_seconds, serialized_value)
            else:
                await redis.set(key, serialized_value)

            return True

        except Exception as e:
            print(f"Redis error in set: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a cache value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._enabled:
            return None

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return None

            value = await redis.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            print(f"Redis error in get: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a cache value.

        Args:
            key: Cache key

        Returns:
            bool: True if deleted, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            await redis.delete(key)
            return True

        except Exception as e:
            print(f"Redis error in delete: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a cache key exists.

        Args:
            key: Cache key

        Returns:
            bool: True if exists, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            result = await redis.exists(key)
            return bool(result)

        except Exception as e:
            print(f"Redis error in exists: {e}")
            return False

    # ========================================================================
    # Health Check
    # ========================================================================

    async def ping(self) -> bool:
        """
        Ping Redis to check connection health.

        Returns:
            bool: True if connected, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis = await self._get_redis_client()
            if redis is None:
                return False

            await redis.ping()
            return True

        except Exception as e:
            print(f"Redis error in ping: {e}")
            return False


# ============================================================================
# Singleton Instance
# ============================================================================

# Global singleton instance
cache_service = CacheService()
