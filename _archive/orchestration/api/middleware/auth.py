"""
API Key Authentication Middleware
==================================

Provides API key authentication and authorization for MERL-T Orchestration API.

Features:
- SHA-256 hashed API keys (never stores plaintext)
- Role-based access control (admin, user, guest)
- API key expiration checks
- Usage tracking for analytics
- FastAPI dependency injection pattern

Usage:
    from backend.orchestration.api.middleware import verify_api_key, require_role

    @app.get("/protected")
    async def protected_endpoint(api_key: ApiKey = Depends(verify_api_key)):
        return {"message": "Authenticated!"}

    @app.post("/admin-only")
    async def admin_endpoint(api_key: ApiKey = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}

Author: Claude Code
Date: Week 8 Day 4
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import Header, HTTPException, status, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ApiKey, ApiUsage
from ..database import get_session

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def hash_api_key(plaintext_key: str) -> str:
    """
    Hash API key using SHA-256.

    Args:
        plaintext_key: The plaintext API key

    Returns:
        SHA-256 hash of the key (64 character hex string)
    """
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


async def log_api_usage(
    session: AsyncSession,
    key_id: str,
    request: Request,
    response_status: int,
    response_time_ms: float
) -> None:
    """
    Log API usage for analytics and rate limiting.

    Args:
        session: Database session
        key_id: API key ID
        request: FastAPI request object
        response_status: HTTP response status code
        response_time_ms: Response time in milliseconds
    """
    try:
        usage = ApiUsage(
            key_id=key_id,
            endpoint=str(request.url.path),
            method=request.method,
            response_status=response_status,
            response_time_ms=response_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            timestamp=datetime.utcnow(),
        )
        session.add(usage)
        await session.commit()
        logger.debug(f"Logged API usage: key={key_id}, endpoint={request.url.path}, status={response_status}")
    except Exception as e:
        logger.warning(f"Failed to log API usage: {e}")
        await session.rollback()


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, description="API key for authentication")
) -> Optional[str]:
    """
    Extract API key from X-API-Key header.

    Args:
        x_api_key: API key from request header

    Returns:
        API key if present, None otherwise
    """
    return x_api_key


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Depends(get_api_key_from_header),
    session: AsyncSession = Depends(get_session)
) -> ApiKey:
    """
    Verify API key and return ApiKey model if valid.

    Checks:
    1. API key is provided
    2. API key exists in database
    3. API key is active
    4. API key has not expired

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header
        session: Database session

    Returns:
        ApiKey model if authentication successful

    Raises:
        HTTPException 401: If API key is missing, invalid, inactive, or expired
    """
    # Check if API key is provided
    if not x_api_key:
        logger.warning(f"Missing API key for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Hash the provided key
    key_hash = hash_api_key(x_api_key)

    # Query database for API key
    try:
        result = await session.execute(
            select(ApiKey).where(ApiKey.api_key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error during API key verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )

    # Check if API key exists
    if not api_key:
        logger.warning(f"Invalid API key attempt for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if API key is active
    if not api_key.is_active:
        logger.warning(f"Inactive API key attempt: {api_key.key_id} for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive. Contact administrator.",
        )

    # Check if API key has expired
    if api_key.is_expired():
        logger.warning(f"Expired API key attempt: {api_key.key_id} (expired: {api_key.expires_at})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API key expired on {api_key.expires_at.isoformat()}. Request new key.",
        )

    # Update last_used_at timestamp
    try:
        api_key.last_used_at = datetime.utcnow()
        await session.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for key {api_key.key_id}: {e}")
        await session.rollback()

    logger.info(f"API key authenticated: {api_key.key_id} (role={api_key.role}, tier={api_key.rate_limit_tier})")
    return api_key


async def get_current_api_key(
    api_key: ApiKey = Depends(verify_api_key)
) -> ApiKey:
    """
    Convenience dependency for getting current authenticated API key.

    Alias for verify_api_key with clearer name.

    Args:
        api_key: Authenticated API key from verify_api_key

    Returns:
        ApiKey model
    """
    return api_key


# ============================================================================
# Role-Based Authorization
# ============================================================================

def require_role(allowed_roles: List[str] | str):
    """
    Dependency factory for role-based authorization.

    Creates a dependency that checks if the authenticated API key
    has one of the allowed roles.

    Args:
        allowed_roles: Single role or list of allowed roles (e.g., "admin" or ["admin", "user"])

    Returns:
        FastAPI dependency function

    Usage:
        @app.post("/admin-only")
        async def admin_endpoint(api_key: ApiKey = Depends(require_role("admin"))):
            return {"message": "Admin access"}

        @app.get("/user-or-admin")
        async def user_endpoint(api_key: ApiKey = Depends(require_role(["admin", "user"]))):
            return {"data": "..."}
    """
    # Normalize to list
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    async def check_role(api_key: ApiKey = Depends(verify_api_key)) -> ApiKey:
        """Check if API key has required role."""
        if api_key.role not in allowed_roles:
            logger.warning(
                f"Unauthorized role attempt: key={api_key.key_id}, role={api_key.role}, "
                f"required={allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {' or '.join(allowed_roles)}",
            )
        return api_key

    return check_role


# ============================================================================
# Optional Authentication (Public + Private Endpoints)
# ============================================================================

async def optional_api_key(
    x_api_key: Optional[str] = Depends(get_api_key_from_header),
    session: AsyncSession = Depends(get_session)
) -> Optional[ApiKey]:
    """
    Optional API key authentication.

    Returns ApiKey if valid key provided, None if no key provided.
    Raises HTTPException only if key is provided but invalid/expired.

    Useful for endpoints that have both public and authenticated access
    with different rate limits or features.

    Args:
        x_api_key: Optional API key from header
        session: Database session

    Returns:
        ApiKey if authenticated, None if no key provided

    Raises:
        HTTPException 401: If key provided but invalid/expired

    Usage:
        @app.get("/public-with-benefits")
        async def endpoint(api_key: Optional[ApiKey] = Depends(optional_api_key)):
            if api_key:
                # Authenticated user - higher rate limit, more features
                return {"data": "full", "tier": api_key.rate_limit_tier}
            else:
                # Public user - basic features
                return {"data": "limited", "tier": "public"}
    """
    if not x_api_key:
        # No key provided - allow anonymous access
        return None

    # Key provided - validate it
    key_hash = hash_api_key(x_api_key)

    try:
        result = await session.execute(
            select(ApiKey).where(ApiKey.api_key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Database error during optional API key verification: {e}")
        # Don't block request if database error - fallback to anonymous
        return None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key (if provided, must be valid)",
        )

    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive",
        )

    if api_key.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Update last_used_at
    try:
        api_key.last_used_at = datetime.utcnow()
        await session.commit()
    except Exception:
        await session.rollback()

    return api_key
