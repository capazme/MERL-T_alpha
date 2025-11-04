"""
Authentication and authorization for RLCF Framework API

This module provides API key-based authentication for admin endpoints.
In production, consider using OAuth2 or a more robust authentication system.
"""

import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# API Key configuration
API_KEY = os.getenv("ADMIN_API_KEY", "supersecretkey")
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header_value: str = Security(api_key_header)):
    """
    Validate API key for admin endpoints.

    Args:
        api_key_header_value: The API key from the request header

    Returns:
        The validated API key

    Raises:
        HTTPException: If the API key is invalid
    """
    if api_key_header_value == API_KEY:
        return api_key_header_value
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
