"""
FastAPI routers for different endpoint groups.
"""

from .query import router as query_router
from .feedback import router as feedback_router
from .stats import router as stats_router

__all__ = ["query_router", "feedback_router", "stats_router"]
