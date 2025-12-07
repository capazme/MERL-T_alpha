"""
Service Registry
================

Central registry for all MERL-T services.
Supports both monolith and distributed deployment modes.
"""

import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

from backend.interfaces import (
    IStorageService,
    IExpert,
    IExpertGating,
    IRLCFService,
)

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for service deployment."""
    mode: str = "monolith"  # "monolith" or "distributed"

    # Service URLs (only used in distributed mode)
    storage_url: str = "http://localhost:8001"
    orchestration_url: str = "http://localhost:8000"
    rlcf_url: str = "http://localhost:8002"

    # Expert service URLs
    expert_urls: Dict[str, str] = None

    def __post_init__(self):
        if self.expert_urls is None:
            self.expert_urls = {
                "literal": "http://localhost:8010",
                "systemic": "http://localhost:8011",
                "principles": "http://localhost:8012",
                "precedent": "http://localhost:8013",
            }


class ServiceRegistry:
    """
    Central registry for all services.

    In monolith mode: Creates direct implementations
    In distributed mode: Creates HTTP clients

    Example:
        registry = ServiceRegistry()
        await registry.initialize()

        storage = registry.storage
        literal_expert = registry.experts["literal"]
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or self._load_config_from_env()
        self._storage: Optional[IStorageService] = None
        self._experts: Dict[str, IExpert] = {}
        self._gating: Optional[IExpertGating] = None
        self._rlcf: Optional[IRLCFService] = None
        self._initialized = False

        logger.info(f"ServiceRegistry created - mode={self.config.mode}")

    def _load_config_from_env(self) -> ServiceConfig:
        """Load configuration from environment variables."""
        return ServiceConfig(
            mode=os.getenv("MERL_T_MODE", "monolith"),
            storage_url=os.getenv("STORAGE_SERVICE_URL", "http://localhost:8001"),
            orchestration_url=os.getenv("ORCHESTRATION_URL", "http://localhost:8000"),
            rlcf_url=os.getenv("RLCF_SERVICE_URL", "http://localhost:8002"),
        )

    async def initialize(self) -> None:
        """Initialize all services based on mode."""
        if self._initialized:
            return

        if self.config.mode == "monolith":
            await self._init_monolith()
        else:
            await self._init_distributed()

        self._initialized = True
        logger.info(f"ServiceRegistry initialized - mode={self.config.mode}")

    async def _init_monolith(self) -> None:
        """Initialize services in monolith mode (direct implementations)."""
        # Storage Service
        from backend.services.storage_service import StorageServiceImpl
        self._storage = StorageServiceImpl()
        await self._storage.initialize()

        # Expert Gating
        from backend.orchestration.gating import ExpertGatingNetwork
        self._gating = ExpertGatingNetwork()

        # Experts
        from backend.orchestration.experts import (
            LiteralInterpreterV2,
            SystemicTeleologicalV2,
            PrinciplesBalancerV2,
            PrecedentAnalystV2,
        )
        self._experts = {
            "literal": LiteralInterpreterV2(),
            "systemic": SystemicTeleologicalV2(),
            "principles": PrinciplesBalancerV2(),
            "precedent": PrecedentAnalystV2(),
        }

        # RLCF Service
        from backend.services.rlcf_service import RLCFServiceImpl
        self._rlcf = RLCFServiceImpl()

        logger.info("Monolith services initialized")

    async def _init_distributed(self) -> None:
        """Initialize services in distributed mode (HTTP clients)."""
        # v2 PLACEHOLDER: Implement HTTP clients
        logger.warning(
            "Distributed mode not yet implemented. "
            "Falling back to monolith mode."
        )
        await self._init_monolith()

    @property
    def storage(self) -> IStorageService:
        """Get storage service."""
        if not self._initialized:
            raise RuntimeError("ServiceRegistry not initialized. Call initialize() first.")
        return self._storage

    @property
    def experts(self) -> Dict[str, IExpert]:
        """Get expert services."""
        if not self._initialized:
            raise RuntimeError("ServiceRegistry not initialized. Call initialize() first.")
        return self._experts

    @property
    def gating(self) -> IExpertGating:
        """Get gating network."""
        if not self._initialized:
            raise RuntimeError("ServiceRegistry not initialized. Call initialize() first.")
        return self._gating

    @property
    def rlcf(self) -> IRLCFService:
        """Get RLCF service."""
        if not self._initialized:
            raise RuntimeError("ServiceRegistry not initialized. Call initialize() first.")
        return self._rlcf

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        results = {}

        if self._storage:
            try:
                storage_health = await self._storage.health_check()
                results["storage"] = all(storage_health.values())
            except Exception as e:
                logger.error(f"Storage health check failed: {e}")
                results["storage"] = False

        for name, expert in self._experts.items():
            try:
                results[f"expert_{name}"] = await expert.health_check()
            except Exception as e:
                logger.error(f"Expert {name} health check failed: {e}")
                results[f"expert_{name}"] = False

        if self._rlcf:
            try:
                results["rlcf"] = await self._rlcf.health_check()
            except Exception as e:
                logger.error(f"RLCF health check failed: {e}")
                results["rlcf"] = False

        return results

    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down services...")
        # Add cleanup logic here
        self._initialized = False


# Singleton instance
_registry: Optional[ServiceRegistry] = None


def get_services(config: Optional[ServiceConfig] = None) -> ServiceRegistry:
    """
    Get the global service registry.

    Creates a new registry if one doesn't exist.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        ServiceRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ServiceRegistry(config)
    return _registry


async def initialize_services(config: Optional[ServiceConfig] = None) -> ServiceRegistry:
    """
    Initialize and return the global service registry.

    Convenience function that creates and initializes in one call.
    """
    registry = get_services(config)
    await registry.initialize()
    return registry
