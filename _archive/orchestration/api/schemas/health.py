"""
Pydantic schemas for health check endpoint.
"""

from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Status of a single system component."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Component health status"
    )
    latency_ms: Optional[float] = Field(
        None,
        ge=0.0,
        description="Average response latency (ms)"
    )
    connection: Optional[bool] = Field(
        None,
        description="Connection status for external services"
    )
    issue: Optional[str] = Field(
        None,
        description="Description of issue (if degraded/unhealthy)"
    )
    metadata: Optional[Dict[str, str]] = Field(
        None,
        description="Additional component-specific metadata"
    )


class HealthResponse(BaseModel):
    """
    System health check response for GET /health endpoint.

    Reports status of all MERL-T components and overall system health.
    """

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall system health status"
    )
    components: Dict[str, ComponentStatus] = Field(
        ...,
        description="Status of individual components"
    )
    version: str = Field(
        ...,
        description="MERL-T API version"
    )
    uptime_seconds: int = Field(
        ...,
        ge=0,
        description="Server uptime in seconds"
    )
    timestamp: str = Field(
        ...,
        description="Health check timestamp (ISO 8601)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "components": {
                    "query_understanding": {
                        "status": "healthy",
                        "latency_ms": 45.0
                    },
                    "kg_enrichment": {
                        "status": "healthy",
                        "connection": True,
                        "metadata": {"neo4j_version": "5.x"}
                    },
                    "router": {
                        "status": "healthy",
                        "connection": True,
                        "metadata": {"openrouter_api": "connected"}
                    },
                    "kg_agent": {
                        "status": "healthy"
                    },
                    "api_agent": {
                        "status": "degraded",
                        "issue": "visualex slow response (>2s)"
                    },
                    "vectordb_agent": {
                        "status": "healthy",
                        "connection": True,
                        "metadata": {"qdrant_collections": "1"}
                    },
                    "experts": {
                        "status": "healthy"
                    },
                    "synthesizer": {
                        "status": "healthy"
                    }
                },
                "version": "v0.2.0",
                "uptime_seconds": 345678,
                "timestamp": "2025-01-05T14:30:22Z"
            }
        }
