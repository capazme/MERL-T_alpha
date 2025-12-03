"""
Query Understanding Router & API Endpoints
===========================================

FastAPI router for Query Understanding service.

Provides REST endpoints for:
- Query analysis
- Batch analysis
- Monitoring/metrics
- Integration with pipeline

Routes:
- POST /preprocessing/analyze - Analyze single query
- POST /preprocessing/analyze-batch - Batch analysis
- GET /preprocessing/analyze/{query_id} - Retrieve cached analysis
- GET /preprocessing/metrics - Service metrics
- GET /preprocessing/health - Health check

Integration point between:
- Input: Raw query from user/pipeline
- Processing: Query Understanding
- Output: Enriched query context for KG enrichment
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Body, Query as QueryParam
from pydantic import BaseModel, Field

from backend.preprocessing.query_understanding import (
    QueryUnderstandingService,
    QueryUnderstandingResult,
    get_query_understanding_service,
    prepare_query_for_enrichment,
    QueryIntentType
)

logger = logging.getLogger(__name__)


# ==========================================
# Request/Response Models
# ==========================================

class AnalyzeQueryRequest(BaseModel):
    """Request to analyze a legal query"""
    query: str = Field(..., min_length=1, max_length=5000, description="Legal query text")
    query_id: Optional[str] = Field(None, description="Optional unique identifier")
    use_llm: bool = Field(default=True, description="Use LLM for intent classification")
    trace_id: Optional[str] = Field(None, description="Request trace ID for logging")

    class Config:
        schema_extra = {
            "example": {
                "query": "Art. 1321 c.c. definisce il contratto. Quali sono i requisiti?",
                "trace_id": "req_abc123"
            }
        }


class AnalyzeQueryResponse(BaseModel):
    """Response from query analysis"""
    query_id: str
    original_query: str
    intent: str
    intent_confidence: float
    entities_count: int
    norm_references: List[str]
    legal_concepts: List[str]
    dates: List[str]
    overall_confidence: float
    needs_review: bool
    processing_time_ms: float
    timestamp: str

    class Config:
        schema_extra = {
            "example": {
                "query_id": "qry_123456",
                "original_query": "Art. 1321 c.c.",
                "intent": "norm_search",
                "intent_confidence": 0.88,
                "entities_count": 1,
                "norm_references": ["cc_art_1321"],
                "legal_concepts": ["contratto"],
                "dates": [],
                "overall_confidence": 0.88,
                "needs_review": False,
                "processing_time_ms": 12.5
            }
        }


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze multiple queries"""
    queries: List[str] = Field(..., min_items=1, max_items=100)
    use_llm: bool = Field(default=True)
    trace_id: Optional[str] = Field(None)


class BatchAnalyzeResponse(BaseModel):
    """Response from batch analysis"""
    total_queries: int
    successful: int
    failed: int
    results: List[AnalyzeQueryResponse]
    total_processing_time_ms: float


class QueryUnderstandingMetrics(BaseModel):
    """Service metrics"""
    total_queries_processed: int
    avg_processing_time_ms: float
    avg_confidence: float
    queries_flagged_for_review: int
    intent_distribution: Dict[str, int]
    error_count: int
    uptime_seconds: float


# ==========================================
# Service State & Cache
# ==========================================

_service: Optional[QueryUnderstandingService] = None
_service_start_time: datetime = datetime.utcnow()
_metrics = {
    "total_queries": 0,
    "successful_queries": 0,
    "failed_queries": 0,
    "total_processing_time": 0.0,
    "total_confidence": 0.0,
    "review_flagged": 0,
    "intent_counts": {},
    "errors": 0
}
_analysis_cache: Dict[str, QueryUnderstandingResult] = {}  # Simple in-memory cache


# ==========================================
# Router Setup
# ==========================================

def create_query_understanding_router() -> APIRouter:
    """Create FastAPI router for Query Understanding endpoints"""
    router = APIRouter(
        prefix="/preprocessing",
        tags=["query_understanding"],
        responses={500: {"description": "Internal server error"}}
    )

    # Initialize service on first use
    def get_service() -> QueryUnderstandingService:
        global _service
        if _service is None:
            _service = get_query_understanding_service()
        return _service

    # ==========================================
    # Endpoints
    # ==========================================

    @router.post("/analyze", response_model=AnalyzeQueryResponse)
    async def analyze_query_endpoint(
        request: AnalyzeQueryRequest
    ) -> AnalyzeQueryResponse:
        """
        Analyze a single legal query.

        Extracts:
        - Intent classification
        - Named entities (norms, dates, amounts)
        - Legal concepts
        - Norm references

        Returns full analysis with confidence scores.
        """
        try:
            service = get_service()
            start = time.time()

            # Analyze query
            result = await service.analyze_query(
                query=request.query,
                query_id=request.query_id,
                use_llm=request.use_llm
            )

            processing_time = (time.time() - start) * 1000

            # Update cache
            _analysis_cache[result.query_id] = result

            # Update metrics
            _metrics["total_queries"] += 1
            _metrics["successful_queries"] += 1
            _metrics["total_processing_time"] += processing_time
            _metrics["total_confidence"] += result.overall_confidence
            if result.needs_review:
                _metrics["review_flagged"] += 1
            _metrics["intent_counts"][result.intent.value] = \
                _metrics["intent_counts"].get(result.intent.value, 0) + 1

            logger.info(
                f"Query analyzed: {result.query_id} | "
                f"Intent: {result.intent.value} | "
                f"Confidence: {result.overall_confidence:.2f}"
            )

            # Format response
            return AnalyzeQueryResponse(
                query_id=result.query_id,
                original_query=result.original_query,
                intent=result.intent.value,
                intent_confidence=result.intent_confidence,
                entities_count=len(result.entities),
                norm_references=result.norm_references,
                legal_concepts=result.legal_concepts,
                dates=result.dates,
                overall_confidence=result.overall_confidence,
                needs_review=result.needs_review,
                processing_time_ms=result.processing_time_ms,
                timestamp=result.timestamp.isoformat()
            )

        except Exception as e:
            _metrics["errors"] += 1
            _metrics["failed_queries"] += 1
            logger.error(f"Query analysis failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Query analysis failed: {str(e)}"
            )

    @router.post("/analyze-batch", response_model=BatchAnalyzeResponse)
    async def analyze_batch_endpoint(
        request: BatchAnalyzeRequest
    ) -> BatchAnalyzeResponse:
        """
        Analyze multiple queries in batch.

        Useful for:
        - Processing multiple user queries
        - Building training datasets
        - Batch testing

        Returns array of analysis results.
        """
        try:
            service = get_service()
            start = time.time()
            successful = 0
            failed = 0
            results = []

            import asyncio

            # Process queries in parallel
            analysis_tasks = [
                service.analyze_query(
                    query=q,
                    use_llm=request.use_llm
                )
                for q in request.queries
            ]

            batch_results = await asyncio.gather(
                *analysis_tasks,
                return_exceptions=True
            )

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    failed += 1
                    _metrics["failed_queries"] += 1
                    logger.error(f"Batch query failed: {str(result)}")
                else:
                    successful += 1
                    _metrics["successful_queries"] += 1
                    _metrics["total_confidence"] += result.overall_confidence
                    _metrics["total_processing_time"] += result.processing_time_ms
                    if result.needs_review:
                        _metrics["review_flagged"] += 1
                    _metrics["intent_counts"][result.intent.value] = \
                        _metrics["intent_counts"].get(result.intent.value, 0) + 1

                    # Convert to response format
                    response_item = AnalyzeQueryResponse(
                        query_id=result.query_id,
                        original_query=result.original_query,
                        intent=result.intent.value,
                        intent_confidence=result.intent_confidence,
                        entities_count=len(result.entities),
                        norm_references=result.norm_references,
                        legal_concepts=result.legal_concepts,
                        dates=result.dates,
                        overall_confidence=result.overall_confidence,
                        needs_review=result.needs_review,
                        processing_time_ms=result.processing_time_ms,
                        timestamp=result.timestamp.isoformat()
                    )
                    results.append(response_item)

            _metrics["total_queries"] += len(request.queries)
            processing_time = (time.time() - start) * 1000

            logger.info(
                f"Batch analysis complete: {successful}/{len(request.queries)} successful"
            )

            return BatchAnalyzeResponse(
                total_queries=len(request.queries),
                successful=successful,
                failed=failed,
                results=results,
                total_processing_time_ms=processing_time
            )

        except Exception as e:
            _metrics["errors"] += 1
            logger.error(f"Batch analysis failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Batch analysis failed: {str(e)}"
            )

    @router.get("/analyze/{query_id}")
    async def retrieve_analysis(query_id: str) -> Dict[str, Any]:
        """
        Retrieve cached analysis results for a query.

        Useful for:
        - Retrieving previous analysis results
        - Debugging specific queries
        - Auditing
        """
        if query_id not in _analysis_cache:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for query_id: {query_id}"
            )

        result = _analysis_cache[query_id]
        return result.to_dict()

    @router.get("/metrics", response_model=QueryUnderstandingMetrics)
    async def get_metrics() -> QueryUnderstandingMetrics:
        """
        Get service metrics and statistics.

        Returns:
        - Total queries processed
        - Average processing time
        - Average confidence
        - Queries flagged for review
        - Intent distribution
        - Error count
        - Uptime
        """
        uptime = (datetime.utcnow() - _service_start_time).total_seconds()

        avg_processing_time = (
            _metrics["total_processing_time"] / max(_metrics["total_queries"], 1)
        )
        avg_confidence = (
            _metrics["total_confidence"] / max(_metrics["successful_queries"], 1)
        )

        return QueryUnderstandingMetrics(
            total_queries_processed=_metrics["total_queries"],
            avg_processing_time_ms=avg_processing_time,
            avg_confidence=avg_confidence,
            queries_flagged_for_review=_metrics["review_flagged"],
            intent_distribution=_metrics["intent_counts"],
            error_count=_metrics["errors"],
            uptime_seconds=uptime
        )

    @router.get("/health")
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint.

        Returns service status and basic info.
        """
        try:
            service = get_service()
            return {
                "status": "healthy",
                "service": "query_understanding",
                "version": "phase1_openrouter",
                "uptime_seconds": (
                    datetime.utcnow() - _service_start_time
                ).total_seconds(),
                "total_queries_processed": _metrics["total_queries"],
                "cache_size": len(_analysis_cache),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    return router


# ==========================================
# Convenience Functions
# ==========================================

async def integrate_query_understanding_with_kg(
    query: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Complete pipeline: Query Understanding → KG Enrichment.

    This function bridges the two systems for the full integration.

    Args:
        query: Raw user query
        use_llm: Use LLM for intent classification

    Returns:
        Dictionary ready for KG enrichment stage with:
        - Query analysis
        - Extracted entities
        - Intent classification
        - Confidence scores
        - Metadata for next stage
    """
    # Stage 1: Query Understanding
    prepared = await prepare_query_for_enrichment(query, use_llm=use_llm)

    # Stage 2 preparation: Format for KG enrichment
    enrichment_input = {
        "query_id": prepared["query_id"],
        "original_query": prepared["original_query"],
        "intent": prepared["intent"],
        "intent_confidence": prepared["intent_confidence"],
        "norm_references": prepared["norm_references"],
        "legal_concepts": prepared["legal_concepts"],
        "entities": prepared["extracted_entities"],
        "overall_confidence": prepared["overall_confidence"],
        "needs_review": prepared["needs_review"],
        "stage": "query_understanding_complete",
        "next_stage": "kg_enrichment"
    }

    logger.info(
        f"Query Understanding→KG Bridge: Query {prepared['query_id']} "
        f"ready for KG enrichment (intent: {prepared['intent']})"
    )

    return enrichment_input
