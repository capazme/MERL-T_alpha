"""
Service Layer (v2)
==================

Service implementations and dependency injection.

This module provides:
1. ServiceRegistry: Central registry for all services
2. Direct implementations (monolith mode)
3. HTTP clients (microservices mode - future)

Usage:
    from backend.services import get_services

    # Get configured services (reads from env/config)
    services = get_services()

    # Use services
    results = await services.storage.hybrid_search(...)
    opinion = await services.experts["literal"].analyze(...)

Configuration:
    Set MERL_T_MODE environment variable:
    - "monolith" (default): Direct implementations
    - "distributed": HTTP clients to microservices
"""

from .registry import ServiceRegistry, get_services

__all__ = [
    "ServiceRegistry",
    "get_services",
]
