"""
Knowledge Graph FastAPI Router
===============================

Endpoints for KG enrichment, review workflows, community contributions.

Endpoints:
- POST /kg/enrich - Main enrichment endpoint
- GET /kg/review-queue - Review queue viewer
- POST /kg/review/{id} - Expert approval
- GET /kg/contributions/pending - Contributions awaiting votes
- POST /kg/contributions/vote - Community voting
- POST /kg/contributions/upload - Submit contribution
- GET /kg/stats - Quality metrics
- GET /kg/cache-stats - Cache statistics
- POST /kg/invalidate-cache - Clear cache
- GET /kg/health - Service health
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
import logging

from backend.orchestration.intent_classifier import IntentResult, IntentType
from backend.preprocessing.kg_enrichment_service import (
    KGEnrichmentService, EnrichedContext, NormaContext, SentenzaContext,
    DoctrineContext, ContributionContext, ControversyFlag
)
from backend.preprocessing.models_kg import (
    StagingEntity, ReviewStatusEnum, Contribution, ControversyRecord
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/kg", tags=["knowledge_graph"])


# ==========================================
# Dependency Injection
# ==========================================

async def get_kg_service() -> KGEnrichmentService:
    """Get KG enrichment service instance."""
    # In production, this would be a singleton from app state
    from backend.rlcf_framework.main import kg_service
    return kg_service


# ==========================================
# Request/Response Models
# ==========================================

class EnrichmentRequest(BaseModel):
    """Request for KG enrichment."""
    intent_result: IntentResult = Field(..., description="Intent classification result")

    class Config:
        schema_extra = {
            "example": {
                "intent_result": {
                    "classification_id": "cls_123",
                    "intent": "contract_interpretation",
                    "confidence": 0.92,
                    "query": "Cosa significa questa clausola?"
                }
            }
        }


class EnrichmentResponse(BaseModel):
    """Response with enriched context."""
    enriched_context: EnrichedContext = Field(..., description="Full enriched context")
    processing_time_ms: int = Field(..., description="Time to enrich in milliseconds")
    cache_hit: bool = Field(..., description="Whether result came from cache")

    class Config:
        schema_extra = {
            "example": {
                "enriched_context": {},
                "processing_time_ms": 245,
                "cache_hit": False
            }
        }


class ReviewRequest(BaseModel):
    """Request to review staged entity."""
    status: ReviewStatusEnum = Field(..., description="Approval status")
    comments: Optional[str] = Field(None, description="Review comments")
    confidence: Optional[float] = Field(None, description="Reviewer confidence score")
    suggestions: Optional[Dict[str, Any]] = Field(None, description="Suggestions for improvement")

    class Config:
        schema_extra = {
            "example": {
                "status": "approved",
                "comments": "Nodo verificato e corretto",
                "confidence": 0.95
            }
        }


class ReviewResponse(BaseModel):
    """Response to review submission."""
    success: bool
    staging_id: str
    status: ReviewStatusEnum
    neo4j_node_id: Optional[str] = None
    message: str

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "staging_id": "stage_123",
                "status": "approved",
                "neo4j_node_id": "node_456",
                "message": "Entity approved and added to graph"
            }
        }


class ContributionVoteRequest(BaseModel):
    """Request to vote on contribution."""
    contribution_id: str = Field(..., description="Contribution ID")
    vote: int = Field(..., ge=-1, le=1, description="Vote: -1 (down), 0 (skip), 1 (up)")
    comment: Optional[str] = Field(None, description="Optional comment")

    class Config:
        schema_extra = {
            "example": {
                "contribution_id": "contrib_123",
                "vote": 1,
                "comment": "Great analysis!"
            }
        }


class ContributionVoteResponse(BaseModel):
    """Response to vote submission."""
    success: bool
    contribution_id: str
    new_upvotes: int
    new_downvotes: int
    net_votes: int
    auto_approved: bool = Field(default=False, description="Whether contribution auto-approved")
    message: str


class ContributionUploadRequest(BaseModel):
    """Request to upload contribution."""
    author_id: str = Field(..., description="Author user ID")
    author_name: Optional[str] = Field(None, description="Author name")
    author_email: Optional[str] = Field(None, description="Author email")
    tipo: str = Field(..., description="Type: academic_paper, commentary, case_analysis, practice_guide")
    titolo: str = Field(..., description="Contribution title")
    descrizione: Optional[str] = Field(None, description="Description")

    class Config:
        schema_extra = {
            "example": {
                "author_id": "user_123",
                "author_name": "Prof. Mario Rossi",
                "tipo": "case_analysis",
                "titolo": "Analisi della sentenza 1234/2023"
            }
        }


class ContributionUploadResponse(BaseModel):
    """Response to contribution upload."""
    success: bool
    contribution_id: str
    status: str = Field(default="pending", description="pending, voting, approved, rejected")
    voting_end_date: Optional[str] = Field(None, description="When voting ends (ISO format)")
    message: str


class QualityMetricsResponse(BaseModel):
    """Quality metrics summary."""
    total_nodes: int
    total_edges: int
    avg_confidence: float
    nodes_with_controversy: int
    controversy_ratio: float
    staging_queue_pending: int
    community_contributions_total: int
    cache_hit_ratio: float
    last_normattiva_sync: Optional[str]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CacheStatsResponse(BaseModel):
    """Redis cache statistics."""
    used_memory: str
    connected_clients: int
    total_commands_processed: int
    instantaneous_ops_per_sec: int
    cache_entries: int
    cache_hit_ratio: float


class HealthResponse(BaseModel):
    """Service health status."""
    healthy: bool
    neo4j: bool = Field(..., description="Neo4j connection status")
    redis: bool = Field(..., description="Redis connection status")
    postgresql: bool = Field(..., description="PostgreSQL connection status")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReviewQueueItem(BaseModel):
    """Item in review queue."""
    id: str
    entity_type: str
    source_type: str
    label: str
    confidence_initial: float
    status: str
    created_at: str
    reviewer_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "id": "stage_123",
                "entity_type": "norma",
                "label": "Art. 2043 c.c.",
                "confidence_initial": 0.92,
                "status": "pending",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class PendingContribution(BaseModel):
    """Contribution awaiting community voting."""
    id: str
    author_id: str
    titolo: str
    tipo: str
    upvote_count: int
    downvote_count: int
    net_votes: int
    voting_end_date: str
    submission_date: str
    days_remaining: int

    class Config:
        schema_extra = {
            "example": {
                "id": "contrib_123",
                "author_id": "user_456",
                "titolo": "Analisi della sentenza X",
                "upvote_count": 7,
                "downvote_count": 0,
                "net_votes": 7,
                "days_remaining": 3
            }
        }


# ==========================================
# Endpoints
# ==========================================

@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich_context(
    request: EnrichmentRequest,
    service: KGEnrichmentService = Depends(get_kg_service)
) -> EnrichmentResponse:
    """
    Enrich intent classification with KG context.

    Main endpoint: integrates all multi-source context (norms, sentenze, dottrina, contributions).

    Returns:
    - Related norms from Normattiva
    - Case law from official registries
    - Academic doctrine commentary
    - Community contributions
    - Controversy flags (if any)
    """
    try:
        start_time = datetime.utcnow()
        enriched = await service.enrich_context(request.intent_result)
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return EnrichmentResponse(
            enriched_context=enriched,
            processing_time_ms=processing_time,
            cache_hit=enriched.enrichment_metadata.get("cache_hit", False)
        )

    except Exception as e:
        logger.error(f"Error enriching context: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.get("/review-queue", response_model=List[ReviewQueueItem])
async def get_review_queue(
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
) -> List[ReviewQueueItem]:
    """
    Get items in review queue (staging_entities).

    Filters:
    - entity_type: norma, sentenza, dottrina, contribution
    - status: pending, approved, rejected, needs_revision

    Returns:
    - Staged entities awaiting expert review
    """
    # In production: query PostgreSQL staging_entities table
    # Mock response for now
    return [
        ReviewQueueItem(
            id="stage_001",
            entity_type="norma",
            source_type="normattiva",
            label="Art. 2043 c.c.",
            confidence_initial=0.92,
            status="pending",
            created_at="2025-01-15T10:30:00Z"
        )
    ]


@router.post("/review/{staging_id}", response_model=ReviewResponse)
async def review_entity(
    staging_id: str,
    request: ReviewRequest
) -> ReviewResponse:
    """
    Expert review and approval of staged entity.

    Workflow:
    1. Expert reviews staged entity
    2. Approves (adds to Neo4j) or rejects (deletes)
    3. System creates audit record
    4. If approved, triggers Neo4j ingestion

    Returns:
    - Success status
    - New Neo4j node ID (if approved)
    """
    # In production: update PostgreSQL, trigger Neo4j ingestion
    return ReviewResponse(
        success=True,
        staging_id=staging_id,
        status=request.status,
        neo4j_node_id="node_" + staging_id if request.status == ReviewStatusEnum.APPROVED else None,
        message=f"Entity {request.status.value} successfully"
    )


@router.get("/contributions/pending", response_model=List[PendingContribution])
async def get_pending_contributions(
    limit: int = 10,
    min_days_remaining: int = 0,
    sort_by: str = "net_votes"  # net_votes, submission_date, view_count
) -> List[PendingContribution]:
    """
    Get contributions awaiting community voting.

    Returns:
    - Contributions in 7-day voting window
    - Sorted by relevance (net_votes, submission_date, etc)
    - Shows voting progress
    """
    # In production: query PostgreSQL contributions where status='voting'
    return [
        PendingContribution(
            id="contrib_001",
            author_id="user_123",
            titolo="Analisi della sentenza Cassazione 1234/2023",
            tipo="case_analysis",
            upvote_count=8,
            downvote_count=0,
            net_votes=8,
            voting_end_date="2025-01-22T10:30:00Z",
            submission_date="2025-01-15T10:30:00Z",
            days_remaining=7
        )
    ]


@router.post("/contributions/vote", response_model=ContributionVoteResponse)
async def vote_contribution(
    request: ContributionVoteRequest
) -> ContributionVoteResponse:
    """
    Vote on community contribution.

    Voting:
    - User can vote: up (+1), down (-1), or skip (0)
    - Vote counted toward community consensus
    - >= 10 net upvotes after 7 days = auto-approve
    - < 0 net votes = auto-reject

    Returns:
    - Vote counted
    - Updated vote totals
    - Auto-approval status (if threshold reached)
    """
    # In production: update PostgreSQL contributions table, check thresholds
    return ContributionVoteResponse(
        success=True,
        contribution_id=request.contribution_id,
        new_upvotes=9,
        new_downvotes=0,
        net_votes=9,
        message="Vote registered"
    )


@router.post("/contributions/upload", response_model=ContributionUploadResponse)
async def upload_contribution(
    request: ContributionUploadRequest,
    file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None
) -> ContributionUploadResponse:
    """
    Submit community contribution to enrichment queue.

    Workflow:
    1. User uploads document (PDF, DOCX, TXT, MD)
    2. System stores in S3/local, extracts text
    3. Contribution goes to voting window (7 days)
    4. Community votes
    5. Auto-approve if >= 10 net upvotes (or expert review if controversial)

    Returns:
    - Contribution ID
    - Voting window end date
    - Current status
    """
    contribution_id = f"contrib_{request.author_id}_{datetime.utcnow().timestamp():.0f}"

    # In production:
    # - Store file
    # - Extract text
    # - Create PostgreSQL record
    # - Schedule voting window

    if background_tasks:
        background_tasks.add_task(lambda: logger.info(f"Processing contribution {contribution_id}"))

    return ContributionUploadResponse(
        success=True,
        contribution_id=contribution_id,
        status="voting",
        voting_end_date="2025-01-22T10:30:00Z",
        message="Contribution submitted for community voting"
    )


@router.get("/stats", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    service: KGEnrichmentService = Depends(get_kg_service)
) -> QualityMetricsResponse:
    """
    Get KG quality metrics.

    Returns:
    - Node/edge counts by type
    - Confidence distribution
    - Controversy ratio
    - Staging queue status
    - Community contribution status
    - Cache performance
    """
    # In production: query PostgreSQL kg_quality_metrics table (computed nightly)
    cache_stats = await service.get_cache_stats()

    return QualityMetricsResponse(
        total_nodes=15234,
        total_edges=45892,
        avg_confidence=0.87,
        nodes_with_controversy=23,
        controversy_ratio=0.0015,
        staging_queue_pending=12,
        community_contributions_total=156,
        cache_hit_ratio=0.72,
        last_normattiva_sync="2025-01-15T02:00:00Z"
    )


@router.get("/cache-stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    service: KGEnrichmentService = Depends(get_kg_service)
) -> CacheStatsResponse:
    """
    Get Redis cache statistics.

    Returns:
    - Memory usage
    - Connected clients
    - Commands processed
    - Hit ratio
    """
    stats = await service.get_cache_stats()

    return CacheStatsResponse(
        used_memory=stats.get("used_memory", "unknown"),
        connected_clients=stats.get("connected_clients", 0),
        total_commands_processed=stats.get("total_commands_processed", 0),
        instantaneous_ops_per_sec=stats.get("instantaneous_ops_per_sec", 0),
        cache_entries=0,  # Would compute from cache keys
        cache_hit_ratio=0.72
    )


@router.post("/invalidate-cache")
async def invalidate_cache(
    pattern: str = "kg_enrich:*",
    service: KGEnrichmentService = Depends(get_kg_service)
) -> Dict[str, Any]:
    """
    Manually invalidate cache entries.

    Triggers:
    - After Normattiva sync
    - After RLCF feedback
    - On user request

    Args:
        pattern: Cache key pattern (e.g., "kg_enrich:*" or "kg_enrich:contract_*")

    Returns:
    - Count of invalidated entries
    """
    try:
        count = await service.invalidate_cache(pattern)
        return {"success": True, "invalidated_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalidation failed: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check(
    service: KGEnrichmentService = Depends(get_kg_service)
) -> HealthResponse:
    """
    Service health check.

    Returns status of:
    - Neo4j connection
    - Redis connection
    - PostgreSQL connection (inferred)
    """
    health = await service.health_check()

    return HealthResponse(
        healthy=health.get("healthy", False),
        neo4j=health.get("neo4j", False),
        redis=health.get("redis", False),
        postgresql=True  # Would check actual connection
    )


# ==========================================
# Error Handlers
# ==========================================

@router.get("/test")
async def test_endpoint() -> Dict[str, str]:
    """Simple test endpoint."""
    return {"status": "kg_router_active"}
