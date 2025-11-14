"""
Stats Router

FastAPI router for analytics and statistics endpoints.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from ..schemas.stats import (
    PipelineStatsResponse,
    FeedbackStatsResponse,
    StagePerformance,
    ExpertUsageStats,
    ModelImprovementMetric,
    RetrainingEvent,
)
from ..schemas.examples import ERROR_RESPONSE_EXAMPLES
from ..services.feedback_processor import FeedbackProcessor
from ..services.persistence_service import persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["Statistics & Analytics"]
)

# Reference to global feedback processor for stats
from ..routers.feedback import feedback_processor


@router.get(
    "/pipeline",
    response_model=PipelineStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pipeline Statistics",
    description="""
Retrieve comprehensive pipeline performance metrics.

Returns:
- **Total queries** executed in period
- **Average/P95/P99 response times**
- **Success rate**
- **Per-stage performance** (query_understanding, kg_enrichment, router, retrieval, experts, synthesis)
- **Average iterations** (refinement cycles)
- **Expert usage rates** (activation frequency per expert type)
- **Agent usage rates** (kg_agent, api_agent, vectordb_agent)

Useful for:
- Monitoring system performance
- Identifying bottlenecks
- Capacity planning
- SLA compliance
    """,
    responses={
        200: {
            "description": "Pipeline statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "period": "last_7_days",
                        "queries_total": 1543,
                        "avg_response_time_ms": 2456.7,
                        "p95_response_time_ms": 4200.0,
                        "success_rate": 0.987,
                        "avg_iterations": 1.2,
                        "expert_usage": {
                            "literal_interpreter": 0.92,
                            "systemic_teleological": 0.68
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "internal_error": ERROR_RESPONSE_EXAMPLES["internal_error"]
                    }
                }
            }
        }
    }
)
async def get_pipeline_stats(period: str = "last_7_days") -> PipelineStatsResponse:
    """
    Get pipeline performance statistics.

    Args:
        period: Time period for stats (default: "last_7_days")

    Returns:
        PipelineStatsResponse with comprehensive metrics

    Raises:
        HTTPException: 500 for errors
    """
    try:
        logger.info(f"Pipeline stats requested for period={period}")

        # Parse period to days
        days_mapping = {
            "last_7_days": 7,
            "last_30_days": 30,
            "last_90_days": 90,
        }
        days = days_mapping.get(period, 7)

        # Get real pipeline stats from database
        db_stats = await persistence_service.get_pipeline_stats(days=days)

        # TODO: Extract per-stage performance from execution_trace JSONB
        # For now, use mock stage performance data
        stages_performance = {
            "query_understanding": StagePerformance(
                avg_ms=245.3,
                p95_ms=320.0,
                count=db_stats["total_queries"]
            ),
            "kg_enrichment": StagePerformance(
                avg_ms=50.2,
                p95_ms=80.0,
                count=db_stats["total_queries"]
            ),
            "router": StagePerformance(
                avg_ms=1800.5,
                p95_ms=2500.0,
                count=db_stats["total_queries"]
            ),
            "retrieval": StagePerformance(
                avg_ms=280.4,
                p95_ms=450.0,
                count=db_stats["total_queries"]
            ),
            "experts": StagePerformance(
                avg_ms=2100.6,
                p95_ms=3500.0,
                count=db_stats["total_queries"]
            ),
            "synthesis": StagePerformance(
                avg_ms=800.2,
                p95_ms=1200.0,
                count=db_stats["total_queries"]
            ),
        }

        # TODO: Extract expert usage from execution_trace JSONB
        # For now, use mock expert usage data
        expert_usage = ExpertUsageStats(
            literal_interpreter=0.92,
            systemic_teleological=0.68,
            principles_balancer=0.15,
            precedent_analyst=0.45,
        )

        # TODO: Extract agent usage from execution_trace JSONB
        # For now, use mock agent usage data
        agent_usage = {
            "kg_agent": 0.85,
            "api_agent": 0.72,
            "vectordb_agent": 0.68,
        }

        # Build response with real data
        response = PipelineStatsResponse(
            period=period,
            queries_total=db_stats["total_queries"],
            avg_response_time_ms=2456.7,  # TODO: Calculate from timestamps
            p95_response_time_ms=4200.0,  # TODO: Calculate from timestamps
            p99_response_time_ms=5800.0,  # TODO: Calculate from timestamps
            success_rate=db_stats["success_rate"],
            stages_performance=stages_performance,
            avg_iterations=1.2,  # TODO: Extract from execution_trace
            expert_usage=expert_usage,
            agent_usage=agent_usage,
        )

        logger.info(
            f"Pipeline stats: {response.queries_total} queries, "
            f"avg={response.avg_response_time_ms:.0f}ms, "
            f"p95={response.p95_response_time_ms:.0f}ms"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to retrieve pipeline stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error retrieving pipeline stats: {str(e)}"
        )


@router.get(
    "/feedback",
    response_model=FeedbackStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Feedback Statistics",
    description="""
Retrieve RLCF feedback metrics and model improvement tracking.

Returns:
- **User feedback count** and average rating
- **RLCF expert feedback count**
- **NER corrections count**
- **Model improvements** (before/after metrics for each model)
- **Retraining events** (recent model updates with performance gains)
- **Feedback distribution** (histogram of ratings 1-5 stars)

Useful for:
- Tracking user satisfaction
- Monitoring model improvement over time
- Evaluating RLCF effectiveness
- Planning retraining schedules
    """,
    responses={
        200: {
            "description": "Feedback statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "period": "last_30_days",
                        "user_feedback_count": 456,
                        "avg_user_rating": 4.2,
                        "rlcf_expert_feedback_count": 89,
                        "ner_corrections_count": 34,
                        "retraining_events": [
                            {
                                "model": "ner_model",
                                "version": "v2.3 → v2.4",
                                "date": "2025-01-02"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "internal_error": ERROR_RESPONSE_EXAMPLES["internal_error"]
                    }
                }
            }
        }
    }
)
async def get_feedback_stats(period: str = "last_30_days") -> FeedbackStatsResponse:
    """
    Get feedback statistics and model improvement metrics.

    Args:
        period: Time period for stats (default: "last_30_days")

    Returns:
        FeedbackStatsResponse with RLCF metrics

    Raises:
        HTTPException: 500 for errors
    """
    try:
        logger.info(f"Feedback stats requested for period={period}")

        # Parse period to days
        days_mapping = {
            "last_7_days": 7,
            "last_30_days": 30,
            "last_90_days": 90,
        }
        days = days_mapping.get(period, 30)

        # Get real feedback stats from database
        db_feedback_stats = await persistence_service.get_feedback_stats(days=days)

        # Get real-time counts from FeedbackProcessor (for thresholds)
        realtime_stats = await feedback_processor.get_feedback_stats()

        # TODO: Query model improvement metrics from ML pipeline
        # For now, use mock model improvements
        model_improvements = {
            "concept_mapping_accuracy": ModelImprovementMetric(
                before=0.78,
                after=0.85,
                improvement=0.07
            ),
            "routing_accuracy": ModelImprovementMetric(
                before=0.82,
                after=0.88,
                improvement=0.06
            ),
        }

        # TODO: Query retraining events from ML pipeline logs
        # For now, use mock retraining events
        retraining_events = [
            RetrainingEvent(
                model="ner_model",
                version="v2.3 → v2.4",
                date="2025-01-02",
                improvements={
                    "f1_score": ModelImprovementMetric(
                        before=0.87,
                        after=0.91,
                        improvement=0.04
                    ),
                    "precision": ModelImprovementMetric(
                        before=0.89,
                        after=0.93,
                        improvement=0.04
                    ),
                    "recall": ModelImprovementMetric(
                        before=0.85,
                        after=0.90,
                        improvement=0.05
                    ),
                }
            ),
        ]

        # TODO: Calculate feedback distribution from user_feedback table
        # For now, use mock feedback distribution
        feedback_distribution = {
            "1": 12,
            "2": 23,
            "3": 67,
            "4": 189,
            "5": 165,
        }

        # Use average rating from database
        avg_user_rating = db_feedback_stats["avg_user_rating"]

        # Build response
        response = FeedbackStatsResponse(
            period=period,
            user_feedback_count=db_feedback_stats["user_feedback_count"],
            avg_user_rating=avg_user_rating,
            rlcf_expert_feedback_count=db_feedback_stats["rlcf_feedback_count"],
            ner_corrections_count=db_feedback_stats["ner_corrections_count"],
            model_improvements=model_improvements,
            retraining_events=retraining_events,
            feedback_distribution=feedback_distribution,
        )

        logger.info(
            f"Feedback stats: user={response.user_feedback_count}, "
            f"rlcf={response.rlcf_expert_feedback_count}, "
            f"ner={response.ner_corrections_count}, "
            f"avg_rating={response.avg_user_rating:.2f}"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to retrieve feedback stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error retrieving feedback stats: {str(e)}"
        )
