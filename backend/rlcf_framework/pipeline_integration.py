"""
Pipeline Integration Module
===========================

Integrates all components (Intent Classifier, KG Service, RLCF, NER Feedback)
into the main FastAPI application.

This module:
1. Initializes all services
2. Adds pipeline endpoints
3. Sets up feedback loops
4. Configures middleware
5. Manages lifecycle events
"""

import logging
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestration.intent_classifier import get_intent_classifier
from backend.preprocessing.kg_enrichment_service import KGEnrichmentService
from backend.orchestration.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineContext,
    PipelineExecutionStatus,
    create_pipeline_orchestrator
)
from backend.rlcf_framework.rlcf_feedback_processor import (
    RLCFFeedbackProcessor,
    ExpertVote,
    FeedbackType,
    create_feedback_processor
)
from backend.preprocessing.ner_feedback_loop import (
    NERFeedbackLoopManager,
    CorrectionType,
    create_ner_feedback_manager
)
from backend.rlcf_framework.database import SessionLocal
# v2: Neo4j archived - will be replaced by FalkorDB
# from backend.preprocessing.neo4j_connection import Neo4jConnectionManager
from backend.preprocessing.redis_connection import RedisConnectionManager
from backend.preprocessing.config.kg_config import load_kg_config


logger = logging.getLogger(__name__)


# ==========================================
# Request/Response Models
# ==========================================

class PipelineQueryRequest(BaseModel):
    """Request for full pipeline execution."""
    query: str = Field(..., min_length=10, max_length=2000, description="Legal query")
    user_id: Optional[str] = Field(None, description="User ID")
    context: Optional[str] = Field(None, description="Additional context")
    trace_id: Optional[str] = Field(None, description="Request trace ID")


class PipelineQueryResponse(BaseModel):
    """Response from pipeline execution."""
    context_id: str
    status: str
    intent: Optional[str]
    intent_confidence: float
    kg_entities_found: int
    total_latency_ms: float
    feedback_targets: List[str]
    errors: List[str]
    warnings: List[str]


class ExpertFeedbackRequest(BaseModel):
    """Request to submit expert feedback."""
    context_id: str
    feedback_type: str  # "validation", "correction", "clarification"
    entity_id: str
    feedback_text: str
    user_authority: float = Field(ge=0.0, le=1.0)


class NERCorrectionRequest(BaseModel):
    """Request to submit NER correction."""
    query: str
    original_extraction: List[Dict[str, Any]]
    corrected_extraction: List[Dict[str, Any]]
    correction_type: str
    expert_id: str


class PipelineStatsResponse(BaseModel):
    """Pipeline performance statistics."""
    total_executions: int
    success_rate: float
    avg_latency_ms: Dict[str, float]
    error_rate: float
    cache_hit_ratio: float
    feedback_loops_triggered: int


# ==========================================
# Singleton Services
# ==========================================

# Global service instances
_pipeline_orchestrator: Optional[PipelineOrchestrator] = None
_rlcf_feedback_processor: Optional[RLCFFeedbackProcessor] = None
_ner_feedback_manager: Optional[NERFeedbackLoopManager] = None


async def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator instance (dependency injection)."""
    global _pipeline_orchestrator
    if _pipeline_orchestrator is None:
        raise RuntimeError("Pipeline orchestrator not initialized")
    return _pipeline_orchestrator


async def get_rlcf_feedback_processor() -> RLCFFeedbackProcessor:
    """Get RLCF feedback processor instance."""
    global _rlcf_feedback_processor
    if _rlcf_feedback_processor is None:
        raise RuntimeError("RLCF feedback processor not initialized")
    return _rlcf_feedback_processor


async def get_ner_feedback_manager() -> NERFeedbackLoopManager:
    """Get NER feedback loop manager instance."""
    global _ner_feedback_manager
    if _ner_feedback_manager is None:
        raise RuntimeError("NER feedback manager not initialized")
    return _ner_feedback_manager


# ==========================================
# Pipeline Router
# ==========================================

def create_pipeline_router() -> APIRouter:
    """
    Create FastAPI router for pipeline endpoints.

    Returns:
        APIRouter with all pipeline endpoints
    """
    router = APIRouter(prefix="/pipeline", tags=["full_pipeline"])

    @router.post("/query", response_model=PipelineQueryResponse)
    async def execute_pipeline(
        request: PipelineQueryRequest,
        orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator)
    ) -> PipelineQueryResponse:
        """
        Execute full legal query pipeline.

        Executes:
        1. Intent Classification
        2. KG Enrichment
        3. RLCF Processing
        4. Feedback Loop Preparation

        Args:
            request: Pipeline query request

        Returns:
            Pipeline execution response
        """
        try:
            # Execute pipeline
            context, status = await orchestrator.execute_pipeline(
                query=request.query,
                user_id=request.user_id,
                trace_id=request.trace_id
            )

            # Format response
            return PipelineQueryResponse(
                context_id=context.context_id,
                status=status.value,
                intent=context.intent_result.intent.value if context.intent_result else None,
                intent_confidence=context.intent_result.confidence if context.intent_result else 0.0,
                kg_entities_found=(
                    len(context.enriched_context.norms or []) +
                    len(context.enriched_context.sentenze or []) +
                    len(context.enriched_context.dottrina or [])
                ) if context.enriched_context else 0,
                total_latency_ms=context.total_duration_ms(),
                feedback_targets=context.feedback_targets,
                errors=context.errors,
                warnings=context.warnings
            )

        except Exception as e:
            logger.error(f"Pipeline execution error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

    @router.post("/feedback/submit")
    async def submit_pipeline_feedback(
        request: ExpertFeedbackRequest,
        orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator)
    ) -> Dict[str, Any]:
        """
        Submit expert feedback on pipeline results.

        Args:
            request: Expert feedback request

        Returns:
            Feedback processing status
        """
        try:
            result = await orchestrator.submit_feedback(
                context_id=request.context_id,
                feedback_type=request.feedback_type,
                entity_id=request.entity_id,
                feedback_text=request.feedback_text,
                user_authority=request.user_authority
            )

            return result

        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

    @router.post("/ner/correct")
    async def submit_ner_correction(
        request: NERCorrectionRequest,
        manager: NERFeedbackLoopManager = Depends(get_ner_feedback_manager)
    ) -> Dict[str, Any]:
        """
        Submit NER correction for model improvement.

        Args:
            request: NER correction request

        Returns:
            Training example creation status
        """
        try:
            result = await manager.process_ner_correction(
                query=request.query,
                original_extraction=request.original_extraction,
                corrected_extraction=request.corrected_extraction,
                expert_id=request.expert_id,
                correction_type=CorrectionType(request.correction_type)
            )

            return result

        except Exception as e:
            logger.error(f"Error processing NER correction: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Correction processing failed: {str(e)}")

    @router.get("/stats", response_model=PipelineStatsResponse)
    async def get_pipeline_stats(
        orchestrator: PipelineOrchestrator = Depends(get_pipeline_orchestrator)
    ) -> PipelineStatsResponse:
        """Get pipeline performance statistics."""
        try:
            metrics = await orchestrator.get_pipeline_metrics()

            return PipelineStatsResponse(
                total_executions=metrics.get("total_executions", 0),
                success_rate=metrics.get("success_rate", 0.0),
                avg_latency_ms=metrics.get("avg_latency_ms", {}),
                error_rate=metrics.get("error_rate", 0.0),
                cache_hit_ratio=metrics.get("cache_hit_ratio", 0.0),
                feedback_loops_triggered=metrics.get("feedback_loops_triggered", 0)
            )

        except Exception as e:
            logger.error(f"Error getting pipeline stats: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

    @router.get("/health")
    async def pipeline_health_check() -> Dict[str, Any]:
        """Check pipeline component health."""
        try:
            # Check Neo4j health
            neo4j_health = await Neo4jConnectionManager.health_check()

            # Check Redis health
            redis_health = await RedisConnectionManager.health_check()

            # Overall status: healthy if all critical components are healthy
            all_healthy = (
                bool(_pipeline_orchestrator) and
                neo4j_health["status"] == "healthy" and
                redis_health["status"] == "healthy"
            )

            health = {
                "status": "healthy" if all_healthy else "degraded",
                "components": {
                    "orchestrator": "ok" if _pipeline_orchestrator else "not_initialized",
                    "rlcf_processor": "ok" if _rlcf_feedback_processor else "not_initialized",
                    "ner_manager": "ok" if _ner_feedback_manager else "not_initialized",
                    "neo4j": neo4j_health,
                    "redis": redis_health
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            return health

        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    return router


# ==========================================
# Initialization Functions
# ==========================================

async def initialize_pipeline_components(app: FastAPI) -> None:
    """
    Initialize all pipeline components on startup.

    Args:
        app: FastAPI application instance
    """
    global _pipeline_orchestrator, _rlcf_feedback_processor, _ner_feedback_manager

    try:
        logger.info("Initializing pipeline components...")

        # Load KG configuration
        logger.info("Loading KG configuration...")
        try:
            kg_config = load_kg_config()
            logger.info("✓ KG configuration loaded")
        except FileNotFoundError:
            logger.warning("⚠️ kg_config.yaml not found, using defaults")
            kg_config = None
        except Exception as e:
            logger.warning(f"⚠️ Error loading KG config: {str(e)}, using defaults")
            kg_config = None

        # Initialize Neo4j connection
        logger.info("Initializing Neo4j connection...")
        try:
            if kg_config:
                neo4j_driver = await Neo4jConnectionManager.initialize(
                    uri=kg_config.neo4j.uri,
                    username=kg_config.neo4j.user,
                    password=kg_config.neo4j.password,
                    database=kg_config.neo4j.database,
                    max_connection_pool_size=kg_config.neo4j.max_connection_pool_size
                )
            else:
                neo4j_driver = await Neo4jConnectionManager.initialize()

            logger.info("✓ Neo4j connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j initialization failed: {str(e)}")
            logger.warning("   Pipeline will continue without Neo4j (some features may be unavailable)")
            neo4j_driver = None

        # Initialize Redis connection
        logger.info("Initializing Redis connection...")
        try:
            if kg_config:
                redis_client = await RedisConnectionManager.initialize(
                    host=kg_config.redis.host,
                    port=kg_config.redis.port,
                    db=kg_config.redis.db,
                    password=kg_config.redis.password,
                    max_connections=kg_config.redis.max_connections
                )
            else:
                redis_client = await RedisConnectionManager.initialize()

            logger.info("✓ Redis connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Redis initialization failed: {str(e)}")
            logger.warning("   Pipeline will continue without caching (performance may be reduced)")
            redis_client = None

        # Get database session
        async with SessionLocal() as db_session:
            # Initialize Intent Classifier
            intent_classifier = get_intent_classifier()
            logger.info("✓ Intent classifier initialized")

            # Initialize KG Service with real connections
            kg_service = KGEnrichmentService(
                neo4j_driver=neo4j_driver,
                redis_client=redis_client,
                config=kg_config
            )
            logger.info("✓ KG enrichment service initialized")

            # Initialize Pipeline Orchestrator
            _pipeline_orchestrator = await create_pipeline_orchestrator(
                intent_classifier=intent_classifier,
                kg_service=kg_service,
                db_session=db_session
            )
            logger.info("✓ Pipeline orchestrator initialized")

            # Initialize RLCF Feedback Processor
            _rlcf_feedback_processor = await create_feedback_processor(db_session)
            logger.info("✓ RLCF feedback processor initialized")

            # Initialize NER Feedback Manager
            _ner_feedback_manager = await create_ner_feedback_manager(db_session)
            logger.info("✓ NER feedback manager initialized")

        logger.info("✅ All pipeline components initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing pipeline components: {str(e)}", exc_info=True)
        raise


async def shutdown_pipeline_components(app: FastAPI) -> None:
    """
    Cleanup pipeline components on shutdown.

    Args:
        app: FastAPI application instance
    """
    global _pipeline_orchestrator, _rlcf_feedback_processor, _ner_feedback_manager

    try:
        logger.info("Shutting down pipeline components...")

        # Close Redis connection
        logger.info("Closing Redis connection...")
        await RedisConnectionManager.close()
        logger.info("✓ Redis connection closed")

        # Close Neo4j connection
        logger.info("Closing Neo4j connection...")
        await Neo4jConnectionManager.close()
        logger.info("✓ Neo4j connection closed")

        # Clear service references
        _pipeline_orchestrator = None
        _rlcf_feedback_processor = None
        _ner_feedback_manager = None

        logger.info("✅ Pipeline components shutdown complete")

    except Exception as e:
        logger.error(f"Error shutting down pipeline components: {str(e)}", exc_info=True)


# ==========================================
# App Integration
# ==========================================

def integrate_pipeline_into_app(app: FastAPI) -> FastAPI:
    """
    Integrate all pipeline components into FastAPI app.

    Adds:
    - Pipeline endpoints (/pipeline/*)
    - Startup initialization
    - Shutdown cleanup

    Args:
        app: FastAPI application

    Returns:
        Modified FastAPI application
    """
    # Add pipeline router
    pipeline_router = create_pipeline_router()
    app.include_router(pipeline_router)

    # Add lifecycle events
    @app.on_event("startup")
    async def startup():
        await initialize_pipeline_components(app)

    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_pipeline_components(app)

    logger.info("Pipeline integrated into FastAPI application")

    return app
