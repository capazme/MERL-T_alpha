"""
Pydantic schemas for analytics/statistics endpoints.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# PIPELINE STATISTICS SCHEMAS
# ============================================================================

class StagePerformance(BaseModel):
    """Performance metrics for a single pipeline stage."""

    avg_ms: float = Field(..., ge=0.0, description="Average execution time (ms)")
    p95_ms: float = Field(..., ge=0.0, description="95th percentile execution time (ms)")
    p99_ms: Optional[float] = Field(None, ge=0.0, description="99th percentile execution time (ms)")
    count: int = Field(..., ge=0, description="Number of executions")


class ExpertUsageStats(BaseModel):
    """Usage statistics for reasoning experts."""

    literal_interpreter: float = Field(..., ge=0.0, le=1.0, description="Usage rate (0-1)")
    systemic_teleological: float = Field(..., ge=0.0, le=1.0, description="Usage rate (0-1)")
    principles_balancer: float = Field(..., ge=0.0, le=1.0, description="Usage rate (0-1)")
    precedent_analyst: float = Field(..., ge=0.0, le=1.0, description="Usage rate (0-1)")


class PipelineStatsResponse(BaseModel):
    """
    Response schema for GET /stats/pipeline.

    Returns comprehensive pipeline performance metrics.
    """

    period: str = Field(..., description="Time period for stats (e.g., 'last_7_days')")
    queries_total: int = Field(..., ge=0, description="Total queries executed")
    avg_response_time_ms: float = Field(..., ge=0.0, description="Average response time (ms)")
    p95_response_time_ms: float = Field(..., ge=0.0, description="95th percentile response time (ms)")
    p99_response_time_ms: Optional[float] = Field(
        None,
        ge=0.0,
        description="99th percentile response time (ms)"
    )
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Success rate (0-1)"
    )
    stages_performance: Dict[str, StagePerformance] = Field(
        ...,
        description="Per-stage performance metrics"
    )
    avg_iterations: float = Field(..., ge=1.0, description="Average refinement iterations")
    expert_usage: ExpertUsageStats = Field(..., description="Expert activation rates")
    agent_usage: Optional[Dict[str, float]] = Field(
        None,
        description="Agent activation rates (kg_agent, api_agent, vectordb_agent)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "period": "last_7_days",
                "queries_total": 1543,
                "avg_response_time_ms": 2456.7,
                "p95_response_time_ms": 4200.0,
                "success_rate": 0.987,
                "stages_performance": {
                    "query_understanding": {"avg_ms": 245.3, "p95_ms": 320.0, "count": 1543},
                    "kg_enrichment": {"avg_ms": 50.2, "p95_ms": 80.0, "count": 1543},
                    "router": {"avg_ms": 1800.5, "p95_ms": 2500.0, "count": 1543},
                    "retrieval": {"avg_ms": 280.4, "p95_ms": 450.0, "count": 1543},
                    "experts": {"avg_ms": 2100.6, "p95_ms": 3500.0, "count": 1543},
                    "synthesis": {"avg_ms": 800.2, "p95_ms": 1200.0, "count": 1543}
                },
                "avg_iterations": 1.2,
                "expert_usage": {
                    "literal_interpreter": 0.92,
                    "systemic_teleological": 0.68,
                    "principles_balancer": 0.15,
                    "precedent_analyst": 0.45
                }
            }
        }


# ============================================================================
# FEEDBACK STATISTICS SCHEMAS
# ============================================================================

class ModelImprovementMetric(BaseModel):
    """Before/after metrics for model improvements."""

    before: float = Field(..., ge=0.0, le=1.0, description="Metric before retraining")
    after: float = Field(..., ge=0.0, le=1.0, description="Metric after retraining")
    improvement: float = Field(..., description="Absolute improvement (after - before)")


class RetrainingEvent(BaseModel):
    """Model retraining event details."""

    model: str = Field(..., description="Model name (ner_model, router_model, etc.)")
    version: str = Field(..., description="Version transition (e.g., 'v2.3 → v2.4')")
    date: str = Field(..., description="Retraining date (ISO 8601)")
    improvements: Dict[str, ModelImprovementMetric] = Field(
        ...,
        description="Performance improvements by metric"
    )


class FeedbackStatsResponse(BaseModel):
    """
    Response schema for GET /stats/feedback.

    Returns RLCF feedback metrics and model improvement tracking.
    """

    period: str = Field(..., description="Time period for stats (e.g., 'last_30_days')")
    user_feedback_count: int = Field(..., ge=0, description="Total user feedback submissions")
    avg_user_rating: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Average user rating (1-5 stars)"
    )
    rlcf_expert_feedback_count: int = Field(
        ...,
        ge=0,
        description="Total RLCF expert feedback submissions"
    )
    ner_corrections_count: int = Field(..., ge=0, description="Total NER corrections")
    model_improvements: Optional[Dict[str, ModelImprovementMetric]] = Field(
        None,
        description="Model performance improvements"
    )
    retraining_events: List[RetrainingEvent] = Field(
        default_factory=list,
        description="Recent retraining events"
    )
    feedback_distribution: Optional[Dict[str, int]] = Field(
        None,
        description="Feedback count by rating (1-5 stars)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "period": "last_30_days",
                "user_feedback_count": 456,
                "avg_user_rating": 4.2,
                "rlcf_expert_feedback_count": 89,
                "ner_corrections_count": 34,
                "model_improvements": {
                    "concept_mapping_accuracy": {
                        "before": 0.78,
                        "after": 0.85,
                        "improvement": 0.07
                    },
                    "routing_accuracy": {
                        "before": 0.82,
                        "after": 0.88,
                        "improvement": 0.06
                    }
                },
                "retraining_events": [
                    {
                        "model": "ner_model",
                        "version": "v2.3 → v2.4",
                        "date": "2025-01-02",
                        "improvements": {
                            "f1_score": {
                                "before": 0.87,
                                "after": 0.91,
                                "improvement": 0.04
                            }
                        }
                    }
                ],
                "feedback_distribution": {
                    "1": 12,
                    "2": 23,
                    "3": 67,
                    "4": 189,
                    "5": 165
                }
            }
        }
