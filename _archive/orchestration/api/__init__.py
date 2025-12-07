"""
MERL-T API Layer

FastAPI-based REST API for the MERL-T orchestration layer.
Exposes the complete LangGraph workflow via HTTP endpoints.

Modules:
- schemas: Pydantic request/response models
- routers: FastAPI route handlers
- services: Business logic and workflow execution
"""

from .main import app

__all__ = ["app"]
