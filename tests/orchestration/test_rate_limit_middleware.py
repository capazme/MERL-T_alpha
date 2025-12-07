"""
Rate Limiting Middleware Tests
===============================

Tests for Redis-based rate limiting with sliding window algorithm (Week 8 Day 4).

Test Coverage:
- Sliding window rate limiting
- Per-tier quotas (unlimited, premium, standard, limited)
- Redis operations (zadd, zcard, zremrangebyscore)
- Rate limit headers (X-RateLimit-*)
- HTTP 429 Too Many Requests
- Graceful degradation (Redis unavailable)
- Edge cases and concurrency

Author: Claude Code
Date: Week 8 Day 4
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status, Request, Response

from merlt.orchestration.api.middleware.rate_limit import (
    get_rate_limit_quota,
    check_rate_limit_redis,
    add_rate_limit_headers,
    check_rate_limit,
    RATE_LIMIT_QUOTAS,
    RATE_LIMIT_WINDOW,
)
from merlt.orchestration.api.models import ApiKey


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url.path = "/query/execute"
    request.method = "POST"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_response():
    """Create mock FastAPI response."""
    response = MagicMock(spec=Response)
    response.headers = {}
    return response


@pytest.fixture
def standard_api_key():
    """Create API key with standard tier (100 req/hour)."""
    return ApiKey(
        key_id="standard-key-001",
        api_key_hash="hash123",
        role="user",
        rate_limit_tier="standard",
        is_active=True,
    )


@pytest.fixture
def premium_api_key():
    """Create API key with premium tier (1000 req/hour)."""
    return ApiKey(
        key_id="premium-key-001",
        api_key_hash="hash456",
        role="user",
        rate_limit_tier="premium",
        is_active=True,
    )


@pytest.fixture
def unlimited_api_key():
    """Create API key with unlimited tier (999999 req/hour)."""
    return ApiKey(
        key_id="unlimited-key-001",
        api_key_hash="hash789",
        role="admin",
        rate_limit_tier="unlimited",
        is_active=True,
    )


@pytest.fixture
def limited_api_key():
    """Create API key with limited tier (10 req/hour)."""
    return ApiKey(
        key_id="limited-key-001",
        api_key_hash="hash999",
        role="guest",
        rate_limit_tier="limited",
        is_active=True,
    )


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.zadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


# ============================================================================
# Test: get_rate_limit_quota()
# ============================================================================

def test_get_rate_limit_quota_all_tiers():
    """Test quota retrieval for all tiers."""
    assert get_rate_limit_quota("unlimited") == 999999
    assert get_rate_limit_quota("premium") == 1000
    assert get_rate_limit_quota("standard") == 100
    assert get_rate_limit_quota("limited") == 10


def test_get_rate_limit_quota_unknown_tier():
    """Test unknown tier defaults to standard."""
    assert get_rate_limit_quota("unknown_tier") == 100  # Default


def test_get_rate_limit_quota_none():
    """Test None tier defaults to standard."""
    assert get_rate_limit_quota(None) == 100


# ============================================================================
# Test: check_rate_limit_redis() - Under Quota
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_first_request(mock_redis_client):
    """Test first request is allowed."""
    # Mock cache_service to return our mock Redis
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # First request: zcard returns 0
        mock_redis_client.zcard = AsyncMock(return_value=0)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key-001",
            tier="standard"
        )

        assert is_allowed is True
        assert current_count == 1
        assert quota == 100

        # Verify Redis operations
        mock_redis_client.zremrangebyscore.assert_called_once()  # Clean old entries
        mock_redis_client.zcard.assert_called_once()  # Count requests
        mock_redis_client.zadd.assert_called_once()  # Add current request
        mock_redis_client.expire.assert_called_once()  # Set expiration


@pytest.mark.asyncio
async def test_check_rate_limit_redis_under_quota(mock_redis_client):
    """Test request under quota is allowed."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # 50 requests already (under standard quota of 100)
        mock_redis_client.zcard = AsyncMock(return_value=50)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key-002",
            tier="standard"
        )

        assert is_allowed is True
        assert current_count == 51
        assert quota == 100


@pytest.mark.asyncio
async def test_check_rate_limit_redis_just_under_quota(mock_redis_client):
    """Test request at quota-1 is allowed."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # 99 requests (just under quota of 100)
        mock_redis_client.zcard = AsyncMock(return_value=99)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key-003",
            tier="standard"
        )

        assert is_allowed is True
        assert current_count == 100
        assert quota == 100


# ============================================================================
# Test: check_rate_limit_redis() - At/Over Quota
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_at_quota(mock_redis_client):
    """Test request at quota is denied."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # Exactly at quota (100 requests)
        mock_redis_client.zcard = AsyncMock(return_value=100)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key-004",
            tier="standard"
        )

        assert is_allowed is False
        assert current_count == 100
        assert quota == 100

        # Should NOT add new request
        mock_redis_client.zadd.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_redis_over_quota(mock_redis_client):
    """Test request over quota is denied."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # Over quota (150 > 100)
        mock_redis_client.zcard = AsyncMock(return_value=150)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key-005",
            tier="standard"
        )

        assert is_allowed is False
        assert current_count == 150


# ============================================================================
# Test: check_rate_limit_redis() - Different Tiers
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_limited_tier(mock_redis_client):
    """Test limited tier (10 req/hour)."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # 9 requests (under limited quota of 10)
        mock_redis_client.zcard = AsyncMock(return_value=9)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="limited-key",
            tier="limited"
        )

        assert is_allowed is True
        assert quota == 10


@pytest.mark.asyncio
async def test_check_rate_limit_redis_premium_tier(mock_redis_client):
    """Test premium tier (1000 req/hour)."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # 999 requests (under premium quota of 1000)
        mock_redis_client.zcard = AsyncMock(return_value=999)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="premium-key",
            tier="premium"
        )

        assert is_allowed is True
        assert quota == 1000


@pytest.mark.asyncio
async def test_check_rate_limit_redis_unlimited_tier(mock_redis_client):
    """Test unlimited tier (999999 req/hour)."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)

        # Even with 100,000 requests, still under unlimited quota
        mock_redis_client.zcard = AsyncMock(return_value=100000)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="unlimited-key",
            tier="unlimited"
        )

        assert is_allowed is True
        assert quota == 999999


# ============================================================================
# Test: check_rate_limit_redis() - Graceful Degradation
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_unavailable():
    """Test graceful degradation when Redis is unavailable."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=None)  # Redis not available

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key",
            tier="standard"
        )

        # Should allow request when Redis unavailable
        assert is_allowed is True
        assert current_count == 0
        assert quota == 100


@pytest.mark.asyncio
async def test_check_rate_limit_redis_error():
    """Test graceful degradation when Redis raises exception."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(side_effect=Exception("Redis connection error"))
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis)

        is_allowed, current_count, quota = await check_rate_limit_redis(
            key_id="test-key",
            tier="standard"
        )

        # Should allow request on error (fail open)
        assert is_allowed is True


# ============================================================================
# Test: add_rate_limit_headers()
# ============================================================================

@pytest.mark.asyncio
async def test_add_rate_limit_headers_standard():
    """Test rate limit headers for standard tier."""
    response = MagicMock(spec=Response)
    response.headers = {}

    await add_rate_limit_headers(
        response=response,
        current_count=50,
        quota=100,
        window_end=datetime(2025, 11, 6, 12, 0, 0)
    )

    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "50"
    assert response.headers["X-RateLimit-Used"] == "50"
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_add_rate_limit_headers_at_limit():
    """Test headers when at rate limit."""
    response = MagicMock(spec=Response)
    response.headers = {}

    await add_rate_limit_headers(
        response=response,
        current_count=100,
        quota=100
    )

    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert response.headers["X-RateLimit-Used"] == "100"


@pytest.mark.asyncio
async def test_add_rate_limit_headers_over_limit():
    """Test headers when over limit (remaining capped at 0)."""
    response = MagicMock(spec=Response)
    response.headers = {}

    await add_rate_limit_headers(
        response=response,
        current_count=150,
        quota=100
    )

    # Remaining should be 0 (max(0, 100 - 150))
    assert response.headers["X-RateLimit-Remaining"] == "0"


# ============================================================================
# Test: check_rate_limit() - Full Dependency
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_allows_request(
    mock_request, mock_response, standard_api_key, mock_redis_client
):
    """Test check_rate_limit allows request under quota."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=50)  # Under quota

        # Should not raise exception
        await check_rate_limit(
            request=mock_request,
            response=mock_response,
            api_key=standard_api_key
        )

        # Verify headers were added
        assert "X-RateLimit-Limit" in mock_response.headers
        assert mock_response.headers["X-RateLimit-Limit"] == "100"


@pytest.mark.asyncio
async def test_check_rate_limit_denies_request(
    mock_request, mock_response, standard_api_key, mock_redis_client
):
    """Test check_rate_limit raises 429 when quota exceeded."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=100)  # At quota

        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(
                request=mock_request,
                response=mock_response,
                api_key=standard_api_key
            )

        # Verify 429 response
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify error details
        detail = exc_info.value.detail
        assert detail["error"] == "Rate limit exceeded"
        assert detail["quota"] == 100
        assert detail["tier"] == "standard"
        assert "retry_after" in detail

        # Verify headers
        assert "Retry-After" in exc_info.value.headers
        assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_check_rate_limit_premium_higher_quota(
    mock_request, mock_response, premium_api_key, mock_redis_client
):
    """Test premium tier allows more requests."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=500)  # Would exceed standard, but not premium

        await check_rate_limit(
            request=mock_request,
            response=mock_response,
            api_key=premium_api_key
        )

        # Should succeed
        assert mock_response.headers["X-RateLimit-Limit"] == "1000"


@pytest.mark.asyncio
async def test_check_rate_limit_unlimited_never_blocks(
    mock_request, mock_response, unlimited_api_key, mock_redis_client
):
    """Test unlimited tier never blocks."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=50000)  # Very high usage

        await check_rate_limit(
            request=mock_request,
            response=mock_response,
            api_key=unlimited_api_key
        )

        # Should still allow
        assert mock_response.headers["X-RateLimit-Limit"] == "999999"


# ============================================================================
# Test: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_check_rate_limit_redis_key_format(mock_redis_client):
    """Test Redis key format is correct."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=0)

        await check_rate_limit_redis(
            key_id="my-api-key-123",
            tier="standard"
        )

        # Verify zadd was called with correct Redis key
        call_args = mock_redis_client.zadd.call_args
        assert "rate_limit:my-api-key-123" in str(call_args)


@pytest.mark.asyncio
async def test_check_rate_limit_redis_expiration_set(mock_redis_client):
    """Test Redis key expiration is set correctly."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis_client)
        mock_redis_client.zcard = AsyncMock(return_value=0)

        await check_rate_limit_redis(
            key_id="test-key",
            tier="standard"
        )

        # Verify expire was called with window + buffer
        mock_redis_client.expire.assert_called_once()
        call_args = mock_redis_client.expire.call_args[0]
        assert call_args[1] == RATE_LIMIT_WINDOW + 60  # 3600 + 60 seconds


@pytest.mark.asyncio
async def test_check_rate_limit_headers_added_even_on_error(
    mock_request, mock_response, standard_api_key
):
    """Test headers added even when rate limit check fails."""
    with patch("backend.orchestration.api.middleware.rate_limit.cache_service") as mock_cache:
        mock_redis = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=100)  # At quota
        mock_cache.get_redis_client = AsyncMock(return_value=mock_redis)

        try:
            await check_rate_limit(
                request=mock_request,
                response=mock_response,
                api_key=standard_api_key
            )
        except HTTPException:
            pass

        # Headers should still be added to response
        assert "X-RateLimit-Limit" in mock_response.headers


# ============================================================================
# Test Summary
# ============================================================================

"""
Rate Limiting Middleware Test Summary
======================================

Test Coverage:
- get_rate_limit_quota(): 3 tests
- check_rate_limit_redis(): 11 tests
  - Under quota: 3 tests
  - At/over quota: 2 tests
  - Different tiers: 4 tests
  - Graceful degradation: 2 tests
- add_rate_limit_headers(): 3 tests
- check_rate_limit(): 5 tests
- Edge cases: 3 tests

Total: 25 test cases

Run with:
    pytest tests/orchestration/test_rate_limit_middleware.py -v

Coverage target: 95%+

Note: These tests mock Redis. For integration testing with real Redis,
see test_api_authentication_integration.py
"""
