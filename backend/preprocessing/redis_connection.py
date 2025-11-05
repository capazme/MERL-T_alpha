"""
Redis Connection Manager

Centralized singleton for managing Redis async client connections.
Provides connection pooling, health checks, retry logic, and graceful shutdown.

Usage:
    client = await RedisConnectionManager.get_client()
    await client.set("key", "value", ex=3600)
    value = await client.get("key")
"""

import os
import logging
from typing import Optional, Any
import asyncio
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """
    Singleton connection manager for Redis.

    Manages a single AsyncRedis instance shared across the application,
    with configurable connection pooling, retries, and automatic health checks.
    """

    _instance: Optional['RedisConnectionManager'] = None
    _client: Optional[AsyncRedis] = None
    _is_initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(
        cls,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True,
        decode_responses: bool = True,
        **kwargs
    ) -> AsyncRedis:
        """
        Initialize Redis client with connection pooling.

        Args:
            host: Redis host (default: from REDIS_HOST env var)
            port: Redis port (default: from REDIS_PORT env var)
            db: Redis database number (default: from REDIS_DB env var)
            password: Redis password (default: from REDIS_PASSWORD env var)
            max_connections: Maximum connections in pool
            socket_connect_timeout: Connection timeout in seconds
            socket_timeout: Socket timeout in seconds
            retry_on_timeout: Retry on timeout errors
            decode_responses: Decode responses to strings
            **kwargs: Additional Redis configuration options

        Returns:
            AsyncRedis instance

        Raises:
            ConnectionError: If unable to connect to Redis
        """
        if cls._is_initialized and cls._client is not None:
            logger.info("Redis client already initialized, returning existing client")
            return cls._client

        # Load configuration from environment variables
        host = host or os.getenv("REDIS_HOST", "localhost")
        port = port or int(os.getenv("REDIS_PORT", 6379))
        db = db if db is not None else int(os.getenv("REDIS_DB", 1))
        password = password or os.getenv("REDIS_PASSWORD")

        logger.info(f"Initializing Redis client: {host}:{port} (database: {db})")

        try:
            cls._client = AsyncRedis(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_connect_timeout=socket_connect_timeout,
                socket_timeout=socket_timeout,
                retry_on_timeout=retry_on_timeout,
                decode_responses=decode_responses,
                **kwargs
            )

            # Verify connectivity with ping
            await cls._client.ping()

            cls._is_initialized = True
            logger.info("Redis client initialized successfully")

            return cls._client

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}", exc_info=True)
            cls._client = None
            cls._is_initialized = False
            raise

    @classmethod
    async def get_client(cls) -> AsyncRedis:
        """
        Get the Redis client instance.

        Returns:
            AsyncRedis instance

        Raises:
            RuntimeError: If client not initialized
        """
        if not cls._is_initialized or cls._client is None:
            raise RuntimeError(
                "Redis client not initialized. "
                "Call RedisConnectionManager.initialize() first."
            )

        return cls._client

    @classmethod
    async def close(cls):
        """
        Close the Redis client and cleanup resources.

        Should be called during application shutdown.
        """
        if cls._client is not None:
            logger.info("Closing Redis client...")
            await cls._client.aclose()
            cls._client = None
            cls._is_initialized = False
            logger.info("Redis client closed")
        else:
            logger.debug("Redis client not initialized, nothing to close")

    @classmethod
    async def health_check(cls) -> dict:
        """
        Perform health check on Redis connection.

        Returns:
            dict with status, message, and optional details
        """
        if not cls._is_initialized or cls._client is None:
            return {
                "status": "unhealthy",
                "message": "Redis client not initialized",
                "details": None
            }

        try:
            # Ping Redis
            ping_result = await cls._client.ping()

            if ping_result:
                # Get server info
                info = await cls._client.info("server")

                return {
                    "status": "healthy",
                    "message": "Redis connection is healthy",
                    "details": {
                        "redis_version": info.get("redis_version", "unknown"),
                        "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                        "connected_clients": info.get("connected_clients", 0)
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis ping failed",
                    "details": None
                }

        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "message": f"Redis health check failed: {str(e)}",
                "details": {"error": str(e)}
            }

    @classmethod
    async def get_cache_stats(cls) -> dict:
        """
        Get cache statistics from Redis.

        Returns:
            dict with cache statistics
        """
        try:
            client = await cls.get_client()

            # Get all keys matching KG enrichment pattern
            kg_keys = await client.keys("kg_enrich:*")

            # Get memory stats
            info = await client.info("memory")

            return {
                "kg_cache_keys_count": len(kg_keys),
                "memory_used_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "memory_peak_mb": round(info.get("used_memory_peak", 0) / (1024 * 1024), 2),
                "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0)
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}", exc_info=True)
            return {
                "kg_cache_keys_count": -1,
                "memory_used_mb": -1,
                "error": str(e)
            }

    @classmethod
    async def set_with_retry(
        cls,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
        max_retries: int = 3,
        retry_delay: float = 0.5
    ) -> bool:
        """
        Set a value in Redis with retry logic.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
            px: Expiration time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            bool indicating success
        """
        client = await cls.get_client()

        for attempt in range(max_retries):
            try:
                result = await client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
                return bool(result)

            except (ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Redis set failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Redis set failed after {max_retries} attempts: {str(e)}")
                    raise

            except RedisError as e:
                logger.error(f"Redis error during set: {str(e)}", exc_info=True)
                raise

    @classmethod
    async def get_with_retry(
        cls,
        key: str,
        max_retries: int = 3,
        retry_delay: float = 0.5
    ) -> Optional[Any]:
        """
        Get a value from Redis with retry logic.

        Args:
            key: Redis key
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            Value or None if not found
        """
        client = await cls.get_client()

        for attempt in range(max_retries):
            try:
                return await client.get(key)

            except (ConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Redis get failed (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                        f"Retrying in {retry_delay}s..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Redis get failed after {max_retries} attempts: {str(e)}")
                    # Return None instead of raising for cache miss
                    return None

            except RedisError as e:
                logger.error(f"Redis error during get: {str(e)}", exc_info=True)
                return None

    @classmethod
    async def invalidate_pattern(cls, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "kg_enrich:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await cls.get_client()

            # Find all matching keys
            keys = await client.keys(pattern)

            if not keys:
                logger.info(f"No keys found matching pattern: {pattern}")
                return 0

            # Delete all matching keys
            deleted = await client.delete(*keys)
            logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to invalidate pattern '{pattern}': {str(e)}", exc_info=True)
            return 0

    @classmethod
    async def flush_db(cls) -> bool:
        """
        Flush all keys in the current database.

        WARNING: This will delete ALL data in the configured database.

        Returns:
            bool indicating success
        """
        try:
            client = await cls.get_client()
            await client.flushdb()
            logger.warning("Redis database flushed (all keys deleted)")
            return True

        except Exception as e:
            logger.error(f"Failed to flush Redis database: {str(e)}", exc_info=True)
            return False


# Convenience function for simple usage
async def get_redis_client() -> AsyncRedis:
    """
    Get the initialized Redis client.

    Convenience function wrapping RedisConnectionManager.get_client()

    Returns:
        AsyncRedis instance
    """
    return await RedisConnectionManager.get_client()
