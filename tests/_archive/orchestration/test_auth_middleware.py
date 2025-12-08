"""
Authentication Middleware Tests
================================

Tests for API key authentication middleware (Week 8 Day 4).

Test Coverage:
- API key verification (valid, invalid, missing, expired, inactive)
- Role-based authorization (admin, user, guest)
- Optional authentication
- SHA-256 key hashing
- Database error handling
- Security edge cases

Author: Claude Code
Date: Week 8 Day 4
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status, Request

from merlt.orchestration.api.middleware.auth import (
    hash_api_key,
    verify_api_key,
    get_current_api_key,
    require_role,
    optional_api_key,
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
    request.headers = {"user-agent": "pytest"}
    return request


@pytest.fixture
def valid_api_key():
    """Create valid API key model."""
    return ApiKey(
        key_id="test-key-001",
        user_id="user_123",
        api_key_hash=hash_api_key("valid-test-key"),
        role="user",
        rate_limit_tier="standard",
        is_active=True,
        description="Test user key",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),
        last_used_at=None,
    )


@pytest.fixture
def admin_api_key():
    """Create admin API key model."""
    return ApiKey(
        key_id="admin-key-001",
        user_id="admin_123",
        api_key_hash=hash_api_key("admin-test-key"),
        role="admin",
        rate_limit_tier="unlimited",
        is_active=True,
        description="Test admin key",
        created_at=datetime.utcnow(),
        expires_at=None,  # No expiration
        last_used_at=None,
    )


@pytest.fixture
def inactive_api_key():
    """Create inactive API key model."""
    return ApiKey(
        key_id="inactive-key-001",
        user_id="user_456",
        api_key_hash=hash_api_key("inactive-test-key"),
        role="user",
        rate_limit_tier="standard",
        is_active=False,  # Inactive
        description="Inactive test key",
        created_at=datetime.utcnow(),
        expires_at=None,
        last_used_at=None,
    )


@pytest.fixture
def expired_api_key():
    """Create expired API key model."""
    return ApiKey(
        key_id="expired-key-001",
        user_id="user_789",
        api_key_hash=hash_api_key("expired-test-key"),
        role="user",
        rate_limit_tier="standard",
        is_active=True,
        description="Expired test key",
        created_at=datetime.utcnow() - timedelta(days=60),
        expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
        last_used_at=None,
    )


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ============================================================================
# Test: hash_api_key()
# ============================================================================

def test_hash_api_key_consistency():
    """Test that hash_api_key produces consistent SHA-256 hashes."""
    key = "test-key-12345"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)

    # Same key should produce same hash
    assert hash1 == hash2

    # Hash should be 64 characters (SHA-256 hex)
    assert len(hash1) == 64

    # Should match manual SHA-256 hash
    expected_hash = hashlib.sha256(key.encode()).hexdigest()
    assert hash1 == expected_hash


def test_hash_api_key_different_keys():
    """Test that different keys produce different hashes."""
    key1 = "test-key-1"
    key2 = "test-key-2"

    hash1 = hash_api_key(key1)
    hash2 = hash_api_key(key2)

    assert hash1 != hash2


def test_hash_api_key_empty_string():
    """Test hashing empty string."""
    hash_empty = hash_api_key("")
    expected = hashlib.sha256(b"").hexdigest()
    assert hash_empty == expected


# ============================================================================
# Test: verify_api_key() - Success Cases
# ============================================================================

@pytest.mark.asyncio
async def test_verify_api_key_valid(mock_request, valid_api_key, mock_db_session):
    """Test successful authentication with valid API key."""
    # Mock database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = valid_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Call verify_api_key
    result = await verify_api_key(
        request=mock_request,
        x_api_key="valid-test-key",
        session=mock_db_session
    )

    # Assertions
    assert result == valid_api_key
    assert result.role == "user"
    assert result.is_active is True

    # Verify last_used_at was updated
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_api_key_admin(mock_request, admin_api_key, mock_db_session):
    """Test successful authentication with admin API key."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = admin_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await verify_api_key(
        request=mock_request,
        x_api_key="admin-test-key",
        session=mock_db_session
    )

    assert result == admin_api_key
    assert result.role == "admin"
    assert result.rate_limit_tier == "unlimited"


@pytest.mark.asyncio
async def test_verify_api_key_no_expiration(mock_request, admin_api_key, mock_db_session):
    """Test API key with no expiration date (expires_at=None)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = admin_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await verify_api_key(
        request=mock_request,
        x_api_key="admin-test-key",
        session=mock_db_session
    )

    # Should not raise exception - no expiration is valid
    assert result.expires_at is None
    assert not result.is_expired()


# ============================================================================
# Test: verify_api_key() - Error Cases
# ============================================================================

@pytest.mark.asyncio
async def test_verify_api_key_missing(mock_request, mock_db_session):
    """Test missing API key raises 401 Unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key=None,  # Missing
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Missing API key" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_api_key_invalid(mock_request, mock_db_session):
    """Test invalid API key (not in database) raises 401."""
    # Mock database returning None (key not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key="invalid-key-12345",
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid API key" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_api_key_inactive(mock_request, inactive_api_key, mock_db_session):
    """Test inactive API key raises 401."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = inactive_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key="inactive-test-key",
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "inactive" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_api_key_expired(mock_request, expired_api_key, mock_db_session):
    """Test expired API key raises 401."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expired_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key="expired-test-key",
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_api_key_database_error(mock_request, mock_db_session):
    """Test database error raises 500 Internal Server Error."""
    # Mock database raising exception
    mock_db_session.execute = AsyncMock(side_effect=Exception("Database connection error"))

    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key="test-key",
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "unavailable" in exc_info.value.detail.lower()


# ============================================================================
# Test: get_current_api_key()
# ============================================================================

@pytest.mark.asyncio
async def test_get_current_api_key(valid_api_key):
    """Test get_current_api_key returns the API key."""
    result = await get_current_api_key(api_key=valid_api_key)
    assert result == valid_api_key


# ============================================================================
# Test: require_role() - Authorization
# ============================================================================

@pytest.mark.asyncio
async def test_require_role_admin_success(mock_request, admin_api_key, mock_db_session):
    """Test admin-only endpoint allows admin."""
    # Create require_role dependency
    check_admin = require_role("admin")

    # Mock verify_api_key to return admin key
    with patch("backend.orchestration.api.middleware.auth.verify_api_key") as mock_verify:
        mock_verify.return_value = admin_api_key

        result = await check_admin(api_key=admin_api_key)

        assert result == admin_api_key
        assert result.role == "admin"


@pytest.mark.asyncio
async def test_require_role_admin_deny_user(mock_request, valid_api_key, mock_db_session):
    """Test admin-only endpoint denies regular user."""
    check_admin = require_role("admin")

    with patch("backend.orchestration.api.middleware.auth.verify_api_key") as mock_verify:
        mock_verify.return_value = valid_api_key

        with pytest.raises(HTTPException) as exc_info:
            await check_admin(api_key=valid_api_key)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_role_multiple_roles(admin_api_key, valid_api_key):
    """Test multiple roles allowed (admin OR user)."""
    check_auth = require_role(["admin", "user"])

    # Admin should pass
    result_admin = await check_auth(api_key=admin_api_key)
    assert result_admin == admin_api_key

    # User should pass
    result_user = await check_auth(api_key=valid_api_key)
    assert result_user == valid_api_key


@pytest.mark.asyncio
async def test_require_role_guest_denied(admin_api_key):
    """Test guest role denied for admin-only endpoint."""
    check_admin = require_role("admin")

    # Create guest API key
    guest_key = ApiKey(
        key_id="guest-key-001",
        api_key_hash=hash_api_key("guest-test-key"),
        role="guest",
        rate_limit_tier="limited",
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await check_admin(api_key=guest_key)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test: optional_api_key()
# ============================================================================

@pytest.mark.asyncio
async def test_optional_api_key_no_key(mock_db_session):
    """Test optional_api_key allows anonymous access (no key)."""
    result = await optional_api_key(
        x_api_key=None,  # No key provided
        session=mock_db_session
    )

    assert result is None  # Anonymous access


@pytest.mark.asyncio
async def test_optional_api_key_valid(valid_api_key, mock_db_session):
    """Test optional_api_key authenticates valid key."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = valid_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await optional_api_key(
        x_api_key="valid-test-key",
        session=mock_db_session
    )

    assert result == valid_api_key


@pytest.mark.asyncio
async def test_optional_api_key_invalid(mock_db_session):
    """Test optional_api_key raises 401 if key provided but invalid."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Key not found
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await optional_api_key(
            x_api_key="invalid-key",
            session=mock_db_session
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_optional_api_key_database_error_allows_anonymous(mock_db_session):
    """Test optional_api_key allows anonymous if database error."""
    # Mock database error
    mock_db_session.execute = AsyncMock(side_effect=Exception("DB error"))

    # Should return None (anonymous) instead of raising exception
    result = await optional_api_key(
        x_api_key="any-key",
        session=mock_db_session
    )

    assert result is None


# ============================================================================
# Test: Edge Cases and Security
# ============================================================================

def test_hash_api_key_case_sensitive():
    """Test that API key hashing is case-sensitive."""
    key_lower = "testkey123"
    key_upper = "TESTKEY123"

    hash_lower = hash_api_key(key_lower)
    hash_upper = hash_api_key(key_upper)

    assert hash_lower != hash_upper


def test_hash_api_key_special_characters():
    """Test hashing keys with special characters."""
    key_special = "test-key_123!@#$%^&*()"
    hash_special = hash_api_key(key_special)

    assert len(hash_special) == 64  # Valid SHA-256


@pytest.mark.asyncio
async def test_verify_api_key_sql_injection_attempt(mock_request, mock_db_session):
    """Test that SQL injection attempts are safely handled."""
    # Attempt SQL injection in API key
    malicious_key = "test'; DROP TABLE api_keys; --"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(
            request=mock_request,
            x_api_key=malicious_key,
            session=mock_db_session
        )

    # Should get invalid key error (hash won't match)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_verify_api_key_updates_last_used_commit_failure(
    mock_request, valid_api_key, mock_db_session
):
    """Test that authentication succeeds even if last_used_at update fails."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = valid_api_key
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Mock commit to fail
    mock_db_session.commit = AsyncMock(side_effect=Exception("Commit failed"))

    # Should still return the API key (authentication successful)
    result = await verify_api_key(
        request=mock_request,
        x_api_key="valid-test-key",
        session=mock_db_session
    )

    assert result == valid_api_key
    mock_db_session.rollback.assert_called_once()


# ============================================================================
# Test Summary
# ============================================================================

"""
Authentication Middleware Test Summary
======================================

Test Coverage:
- hash_api_key(): 5 tests
- verify_api_key(): 10 tests
  - Success cases: 3 tests
  - Error cases: 5 tests
  - Edge cases: 2 tests
- get_current_api_key(): 1 test
- require_role(): 4 tests
- optional_api_key(): 4 tests
- Security tests: 3 tests

Total: 27 test cases

Run with:
    pytest tests/orchestration/test_auth_middleware.py -v

Coverage target: 95%+
"""
