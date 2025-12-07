"""
Middleware package for MERL-T Orchestration API.

Contains:
- auth.py: API key authentication and authorization
- rate_limit.py: Rate limiting with Redis
"""

from .auth import verify_api_key, get_current_api_key, require_role
from .rate_limit import check_rate_limit

__all__ = [
    "verify_api_key",
    "get_current_api_key",
    "require_role",
    "check_rate_limit",
]
