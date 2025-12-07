"""
Service Interfaces (v2)
=======================

Abstract interfaces for all MERL-T services.

These interfaces allow:
1. Modular code with clear contracts
2. Easy testing with mocks
3. Future migration to microservices

Current: Direct implementation (monolith)
Future: HTTP/gRPC clients (microservices)

Usage:
    # The consuming code uses the interface
    from backend.interfaces import IStorageService

    class MyComponent:
        def __init__(self, storage: IStorageService):
            self.storage = storage

    # Injection can be direct or via HTTP client
    component = MyComponent(storage=DirectStorageService())  # Now
    component = MyComponent(storage=HTTPStorageClient())     # Future
"""

from .storage import IStorageService, IGraphDB, IVectorDB, IBridgeTable
from .experts import IExpert, IExpertGating
from .rlcf import IRLCFService, IAuthorityCalculator

__all__ = [
    # Storage
    "IStorageService",
    "IGraphDB",
    "IVectorDB",
    "IBridgeTable",
    # Experts
    "IExpert",
    "IExpertGating",
    # RLCF
    "IRLCFService",
    "IAuthorityCalculator",
]
