"""
Rate Limiting Middleware
=========================

Redis-based rate limiting with sliding window algorithm.

Features:
- Sliding window algorithm for accurate rate limiting
- Per-tier quotas (unlimited, premium, standard, limited)
- Graceful degradation if Redis unavailable
- HTTP 429 Too Many Requests responses
- Rate limit headers (X-RateLimit-*)

Tiers and Quotas (per hour):
- unlimited: 999,999 requests/hour (admin tier)
- premium: 1,000 requests/hour
- standard: 100 requests/hour (default)
- limited: 10 requests/hour (guest tier)

Usage:
    from backend.orchestration.api.middleware import check_rate_limit

    @app.post("/query/execute")
    async def execute_query(
        request: QueryRequest,
        api_key: ApiKey = Depends(verify_api_key),
        _rate_limit: None = Depends(check_rate_limit)
    ):
        # Endpoint logic here
        pass

Author: Claude Code
Date: Week 8 Day 4
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse

from ..models import ApiKey
from .auth import verify_api_key
from ..services.cache_service import cache_service

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limit Configuration
# ============================================================================

# Quotas per tier (requests per hour)
RATE_LIMIT_QUOTAS = {
    "unlimited": 999999,
    "premium": 1000,
    "standard": 100,
    "limited": 10,
}

# Time window in seconds (1 hour)
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


# ============================================================================
# Helper Functions
# ============================================================================

def get_rate_limit_quota(tier: str) -> int:
    """
    Get rate limit quota for a given tier.

    Args:
        tier: Rate limit tier (unlimited, premium, standard, limited)

    Returns:
        Requests per hour allowed for this tier
    """
    return RATE_LIMIT_QUOTAS.get(tier, RATE_LIMIT_QUOTAS["standard"])


async def check_rate_limit_redis(key_id: str, tier: str) -> tuple[bool, int, int]:
    """
    Check rate limit using Redis sliding window algorithm.

    Uses sorted set with timestamps to implement sliding window.

    Args:
        key_id: API key ID
        tier: Rate limit tier

    Returns:
        Tuple of (is_allowed, current_count, quota)
    """
    quota = get_rate_limit_quota(tier)
    redis_key = f"rate_limit:{key_id}"
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW

    try:
        # Get Redis client (async)
        redis = await cache_service.get_redis_client()
        if not redis:
            logger.warning("Redis not available for rate limiting - allowing request")
            return (True, 0, quota)

        # Remove old entries outside the window
        await redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests in window
        current_count = await redis.zcard(redis_key)

        # Check if under quota
        if current_count >= quota:
            logger.warning(f"Rate limit exceeded for key {key_id}: {current_count}/{quota}")
            return (False, current_count, quota)

        # Add current request to sorted set
        await redis.zadd(redis_key, {str(current_time): current_time})

        # Set expiry on the key (cleanup after window expires)
        await redis.expire(redis_key, RATE_LIMIT_WINDOW + 60)

        logger.debug(f"Rate limit check passed for key {key_id}: {current_count + 1}/{quota}")
        return (True, current_count + 1, quota)

    except Exception as e:
        logger.error(f"Redis error during rate limit check: {e}")
        # Graceful degradation: allow request if Redis fails
        return (True, 0, quota)


async def add_rate_limit_headers(
    response: Response,
    current_count: int,
    quota: int,
    window_end: Optional[datetime] = None
) -> None:
    """
    Add rate limit headers to response.

    Headers:
    - X-RateLimit-Limit: Total quota
    - X-RateLimit-Remaining: Requests remaining
    - X-RateLimit-Reset: Unix timestamp when window resets
    - X-RateLimit-Used: Requests used so far

    Args:
        response: FastAPI response object
        current_count: Current request count
        quota: Total quota
        window_end: When the current window ends (default: 1 hour from now)
    """
    if window_end is None:
        window_end = datetime.utcnow() + timedelta(seconds=RATE_LIMIT_WINDOW)

    response.headers["X-RateLimit-Limit"] = str(quota)
    response.headers["X-RateLimit-Remaining"] = str(max(0, quota - current_count))
    response.headers["X-RateLimit-Reset"] = str(int(window_end.timestamp()))
    response.headers["X-RateLimit-Used"] = str(current_count)


# ============================================================================
# Rate Limiting Dependency
# ============================================================================

async def check_rate_limit(
    request: Request,
    response: Response,
    api_key: ApiKey = Depends(verify_api_key)
) -> None:
    """
    Check rate limit for authenticated API key.

    Uses Redis sliding window algorithm to enforce per-tier quotas.
    Adds rate limit headers to response.
    Raises HTTPException 429 if quota exceeded.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        api_key: Authenticated API key

    Raises:
        HTTPException 429: If rate limit exceeded

    Usage:
        @app.post("/query/execute")
        async def execute_query(
            request: QueryRequest,
            api_key: ApiKey = Depends(verify_api_key),
            _rate_limit: None = Depends(check_rate_limit)  # Check rate limit
        ):
            # Endpoint logic here
            pass
    """
    # Check rate limit with Redis
    is_allowed, current_count, quota = await check_rate_limit_redis(
        key_id=api_key.key_id,
        tier=api_key.rate_limit_tier
    )

    # Add rate limit headers to response
    await add_rate_limit_headers(response, current_count, quota)

    # Raise 429 if rate limit exceeded
    if not is_allowed:
        logger.warning(
            f"Rate limit exceeded for key {api_key.key_id} "
            f"(tier={api_key.rate_limit_tier}, requests={current_count}/{quota})"
        )

        # Calculate retry_after in seconds
        retry_after = RATE_LIMIT_WINDOW

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"You have exceeded your {api_key.rate_limit_tier} tier quota of {quota} requests per hour.",
                "current_usage": current_count,
                "quota": quota,
                "tier": api_key.rate_limit_tier,
                "retry_after": retry_after,
                "reset_at": (datetime.utcnow() + timedelta(seconds=retry_after)).isoformat(),
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(quota),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((datetime.utcnow() + timedelta(seconds=retry_after)).timestamp())),
            }
        )

    logger.debug(
        f"Rate limit check passed for key {api_key.key_id}: "
        f"{current_count}/{quota} (tier={api_key.rate_limit_tier})"
    )


# ============================================================================
# Optional Rate Limiting (for public endpoints)
# ============================================================================

async def check_rate_limit_optional(
    request: Request,
    response: Response,
    api_key: Optional[ApiKey] = None
) -> None:
    """
    Optional rate limiting for public endpoints.

    If API key provided: Use tier-based quota
    If no API key: Use strict IP-based quota (10 req/hour)

    Args:
        request: FastAPI request object
        response: FastAPI response object
        api_key: Optional authenticated API key

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    if api_key:
        # Use tier-based rate limiting
        await check_rate_limit(request, response, api_key)
    else:
        # IP-based rate limiting for anonymous users
        client_ip = request.client.host if request.client else "unknown"
        redis_key = f"ip_rate_limit:{client_ip}"

        # Use limited tier quota for anonymous users
        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id=redis_key,
            tier="limited"
        )

        await add_rate_limit_headers(response, current_count, quota)

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {current_count}/{quota}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Anonymous users are limited to {quota} requests per hour. Please authenticate for higher limits.",
                    "current_usage": current_count,
                    "quota": quota,
                    "retry_after": RATE_LIMIT_WINDOW,
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
            )


# ============================================================================
# Rate Limit Statistics
# ============================================================================

async def get_rate_limit_stats(key_id: str) -> dict:
    """
    Get rate limit statistics for an API key.

    Args:
        key_id: API key ID

    Returns:
        Dict with current usage, quota, remaining, and reset time
    """
    redis_key = f"rate_limit:{key_id}"
    current_time = time.time()
    window_start = current_time - RATE_LIMIT_WINDOW

    try:
        redis = await cache_service.get_redis_client()
        if not redis:
            return {
                "current_usage": 0,
                "quota": 0,
                "remaining": 0,
                "reset_at": None,
                "redis_available": False
            }

        # Remove old entries
        await redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current requests
        current_count = await redis.zcard(redis_key)

        # Get quota (need to fetch API key tier from somewhere)
        # For now, return generic stats
        return {
            "current_usage": current_count,
            "redis_available": True,
            "window_seconds": RATE_LIMIT_WINDOW,
        }

    except Exception as e:
        logger.error(f"Error fetching rate limit stats: {e}")
        return {
            "current_usage": 0,
            "redis_available": False,
            "error": str(e)
        }
