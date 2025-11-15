"""
KG Ingestion API - FastAPI Application
========================================

REST API for controlling LLM-driven knowledge graph ingestion.

Endpoints:
- POST /api/kg-ingestion/start - Start ingestion batch
- GET /api/kg-ingestion/status/{batch_id} - Get batch status
- POST /api/kg-ingestion/stop/{batch_id} - Stop running batch
- GET /api/kg-ingestion/batches - List all batches
- GET /api/kg-ingestion/models - List available LLM models
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

from ..graph_construction_pipeline import (
    GraphConstructionPipeline,
    GraphConstructionConfig,
    GraphConstructionStats
)

log = structlog.get_logger(__name__)

# =============================================================================
# Global State (in-memory for now, can move to Redis later)
# =============================================================================

# Active batches: {batch_id: {"task": asyncio.Task, "status": {...}}}
active_batches: Dict[str, Dict[str, Any]] = {}

# Batch history: {batch_id: {"config": {...}, "stats": {...}}}
batch_history: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Pydantic Models
# =============================================================================

class IngestionBatchConfig(BaseModel):
    """Configuration for ingestion batch."""

    # Batch identification
    batch_name: Optional[str] = Field(None, description="Optional batch name")

    # Article range
    tipo_atto: str = Field("codice civile", description="Type of legal act")
    start_article: int = Field(..., ge=1, le=2969, description="Starting article number")
    end_article: int = Field(..., ge=1, le=2969, description="Ending article number")

    # LLM configuration
    llm_model: str = Field(
        "anthropic/claude-3.5-sonnet",
        description="LLM model to use (e.g., anthropic/claude-3.5-sonnet, google/gemini-pro)"
    )
    llm_temperature: float = Field(0.1, ge=0.0, le=2.0, description="LLM temperature")

    # BrocardiInfo enrichment
    include_brocardi: bool = Field(True, description="Include BrocardiInfo enrichment")

    # Auto-approval thresholds
    entity_auto_approve_threshold: float = Field(
        0.85, ge=0.0, le=1.0,
        description="Auto-approve entities above this confidence"
    )
    relationship_auto_approve_threshold: float = Field(
        0.80, ge=0.0, le=1.0,
        description="Auto-approve relationships above this confidence"
    )

    # Processing options
    dry_run: bool = Field(False, description="Dry run mode (no DB writes)")
    max_concurrent_llm: int = Field(3, ge=1, le=10, description="Max concurrent LLM calls")


class IngestionBatchStatus(BaseModel):
    """Current status of ingestion batch."""

    batch_id: str
    batch_name: Optional[str]
    status: str  # "running", "completed", "failed", "stopped"

    # Progress
    articles_requested: int
    articles_fetched: int
    articles_processed: int
    current_article: Optional[str] = None

    # Entities
    total_entities_extracted: int
    entities_auto_approved: int
    entities_manual_review: int
    avg_entity_confidence: float

    # Relationships
    total_relationships_extracted: int
    relationships_auto_approved: int
    relationships_manual_review: int
    avg_relationship_confidence: float

    # Cost & timing
    total_llm_cost_usd: float
    elapsed_seconds: Optional[float]
    estimated_completion_seconds: Optional[float]

    # Errors
    errors_count: int
    last_error: Optional[str] = None

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None


class BatchHistoryItem(BaseModel):
    """Historical batch record."""

    batch_id: str
    batch_name: Optional[str]
    config: IngestionBatchConfig
    stats: Dict[str, Any]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]


class AvailableModel(BaseModel):
    """Available LLM model."""

    model_id: str
    provider: str
    name: str
    description: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    recommended: bool = False


# =============================================================================
# Lifespan Context (startup/shutdown)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    log.info("KG Ingestion API starting...")

    yield

    # Cleanup on shutdown
    log.info("KG Ingestion API shutting down...")
    for batch_id, batch_data in active_batches.items():
        task = batch_data.get("task")
        if task and not task.done():
            log.warning(f"Cancelling active batch {batch_id}")
            task.cancel()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="MERL-T KG Ingestion API",
    description="Control LLM-driven knowledge graph ingestion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Background Task Functions
# =============================================================================

async def run_ingestion_batch(
    batch_id: str,
    config: IngestionBatchConfig
):
    """
    Run ingestion batch in background.

    Args:
        batch_id: Unique batch identifier
        config: Batch configuration
    """
    try:
        log.info("Starting ingestion batch", batch_id=batch_id, config=config.dict())

        # Create pipeline config
        pipeline_config = GraphConstructionConfig(
            openrouter_api_key=config.llm_model.split("/")[0],  # TODO: Get from env
            visualex_url="http://localhost:5000",
            llm_model=config.llm_model,
            llm_temperature=config.llm_temperature,
            include_brocardi=config.include_brocardi,
            entity_auto_approve_threshold=config.entity_auto_approve_threshold,
            relationship_auto_approve_threshold=config.relationship_auto_approve_threshold,
            dry_run=config.dry_run,
            max_concurrent_llm=config.max_concurrent_llm
        )

        # Create pipeline
        pipeline = GraphConstructionPipeline(pipeline_config)

        # Progress callback to update status
        def progress_callback(current: int, total: int):
            if batch_id in active_batches:
                batch_data = active_batches[batch_id]
                batch_data["status"]["articles_processed"] = current
                batch_data["status"]["current_article"] = str(config.start_article + current - 1)

                # Estimate completion time
                elapsed = (datetime.utcnow() - batch_data["status"]["started_at"]).total_seconds()
                if current > 0:
                    rate = elapsed / current
                    remaining = total - current
                    batch_data["status"]["estimated_completion_seconds"] = remaining * rate

        # Run batch
        stats = await pipeline.construct_codice_civile_batch(
            start_article=config.start_article,
            end_article=config.end_article,
            progress_callback=lambda c, t: progress_callback(c, t)
        )

        # Update status with final stats
        if batch_id in active_batches:
            batch_data = active_batches[batch_id]
            batch_data["status"].update({
                "status": "completed",
                "articles_requested": stats.articles_requested,
                "articles_fetched": stats.articles_fetched,
                "articles_processed": stats.articles_processed,
                "total_entities_extracted": stats.total_entities_extracted,
                "entities_auto_approved": stats.entities_auto_approved,
                "entities_manual_review": stats.entities_manual_review,
                "avg_entity_confidence": stats.avg_entity_confidence,
                "total_relationships_extracted": stats.total_relationships_extracted,
                "relationships_auto_approved": stats.relationships_auto_approved,
                "relationships_manual_review": stats.relationships_manual_review,
                "avg_relationship_confidence": stats.avg_relationship_confidence,
                "total_llm_cost_usd": stats.total_llm_cost_usd,
                "elapsed_seconds": stats.duration_seconds,
                "errors_count": len(stats.errors),
                "completed_at": datetime.utcnow()
            })

            # Move to history
            batch_history[batch_id] = {
                "config": config.dict(),
                "stats": stats.to_dict(),
                "status": batch_data["status"],
                "started_at": batch_data["status"]["started_at"],
                "completed_at": datetime.utcnow()
            }

        await pipeline.close()

        log.info("Ingestion batch completed", batch_id=batch_id, stats=stats.to_dict())

    except asyncio.CancelledError:
        log.warning("Ingestion batch cancelled", batch_id=batch_id)
        if batch_id in active_batches:
            active_batches[batch_id]["status"]["status"] = "stopped"
            active_batches[batch_id]["status"]["completed_at"] = datetime.utcnow()
        raise

    except Exception as e:
        log.error("Ingestion batch failed", batch_id=batch_id, error=str(e), exc_info=True)
        if batch_id in active_batches:
            active_batches[batch_id]["status"]["status"] = "failed"
            active_batches[batch_id]["status"]["last_error"] = str(e)
            active_batches[batch_id]["status"]["errors_count"] += 1
            active_batches[batch_id]["status"]["completed_at"] = datetime.utcnow()


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/api/kg-ingestion/start", response_model=Dict[str, str])
async def start_ingestion_batch(
    config: IngestionBatchConfig,
    background_tasks: BackgroundTasks
):
    """
    Start a new ingestion batch.

    Args:
        config: Batch configuration

    Returns:
        {"batch_id": "...", "message": "..."}
    """
    # Validate article range
    if config.start_article > config.end_article:
        raise HTTPException(
            status_code=400,
            detail="start_article must be <= end_article"
        )

    # Generate batch ID
    batch_id = str(uuid.uuid4())

    # Initialize status
    status = {
        "batch_id": batch_id,
        "batch_name": config.batch_name,
        "status": "running",
        "articles_requested": config.end_article - config.start_article + 1,
        "articles_fetched": 0,
        "articles_processed": 0,
        "current_article": None,
        "total_entities_extracted": 0,
        "entities_auto_approved": 0,
        "entities_manual_review": 0,
        "avg_entity_confidence": 0.0,
        "total_relationships_extracted": 0,
        "relationships_auto_approved": 0,
        "relationships_manual_review": 0,
        "avg_relationship_confidence": 0.0,
        "total_llm_cost_usd": 0.0,
        "elapsed_seconds": None,
        "estimated_completion_seconds": None,
        "errors_count": 0,
        "last_error": None,
        "started_at": datetime.utcnow(),
        "completed_at": None
    }

    # Create background task
    task = asyncio.create_task(run_ingestion_batch(batch_id, config))

    # Store in active batches
    active_batches[batch_id] = {
        "task": task,
        "status": status,
        "config": config.dict()
    }

    log.info(
        "Ingestion batch started",
        batch_id=batch_id,
        start_article=config.start_article,
        end_article=config.end_article,
        llm_model=config.llm_model
    )

    return {
        "batch_id": batch_id,
        "message": f"Ingestion batch started (articles {config.start_article}-{config.end_article})"
    }


@app.get("/api/kg-ingestion/status/{batch_id}", response_model=IngestionBatchStatus)
async def get_batch_status(batch_id: str):
    """
    Get status of ingestion batch.

    Args:
        batch_id: Batch identifier

    Returns:
        Current batch status
    """
    # Check active batches first
    if batch_id in active_batches:
        status = active_batches[batch_id]["status"]
        return IngestionBatchStatus(**status)

    # Check history
    if batch_id in batch_history:
        hist = batch_history[batch_id]
        return IngestionBatchStatus(**hist["status"])

    raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")


@app.post("/api/kg-ingestion/stop/{batch_id}")
async def stop_batch(batch_id: str):
    """
    Stop a running ingestion batch.

    Args:
        batch_id: Batch identifier

    Returns:
        {"message": "..."}
    """
    if batch_id not in active_batches:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found or not running")

    batch_data = active_batches[batch_id]
    task = batch_data.get("task")

    if task and not task.done():
        task.cancel()
        log.info("Ingestion batch stopped", batch_id=batch_id)
        return {"message": f"Batch {batch_id} stopped"}
    else:
        return {"message": f"Batch {batch_id} already completed"}


@app.get("/api/kg-ingestion/batches", response_model=List[BatchHistoryItem])
async def list_batches(
    limit: int = 50,
    status: Optional[str] = None
):
    """
    List ingestion batches (history + active).

    Args:
        limit: Max number of batches to return
        status: Filter by status (running, completed, failed, stopped)

    Returns:
        List of batch history items
    """
    all_batches = []

    # Add active batches
    for batch_id, batch_data in active_batches.items():
        if status is None or batch_data["status"]["status"] == status:
            all_batches.append(BatchHistoryItem(
                batch_id=batch_id,
                batch_name=batch_data["status"].get("batch_name"),
                config=IngestionBatchConfig(**batch_data["config"]),
                stats=batch_data["status"],
                status=batch_data["status"]["status"],
                started_at=batch_data["status"]["started_at"],
                completed_at=batch_data["status"].get("completed_at")
            ))

    # Add historical batches
    for batch_id, hist in batch_history.items():
        if status is None or hist["status"]["status"] == status:
            all_batches.append(BatchHistoryItem(
                batch_id=batch_id,
                batch_name=hist["status"].get("batch_name"),
                config=IngestionBatchConfig(**hist["config"]),
                stats=hist["stats"],
                status=hist["status"]["status"],
                started_at=hist["started_at"],
                completed_at=hist.get("completed_at")
            ))

    # Sort by started_at descending
    all_batches.sort(key=lambda x: x.started_at, reverse=True)

    return all_batches[:limit]


@app.get("/api/kg-ingestion/models", response_model=List[AvailableModel])
async def list_available_models():
    """
    List available LLM models for ingestion.

    Returns:
        List of available models with pricing
    """
    return [
        AvailableModel(
            model_id="anthropic/claude-3.5-sonnet",
            provider="Anthropic",
            name="Claude 3.5 Sonnet",
            description="Best for complex legal reasoning and extraction",
            cost_per_1m_input=3.0,
            cost_per_1m_output=15.0,
            recommended=True
        ),
        AvailableModel(
            model_id="anthropic/claude-3-opus",
            provider="Anthropic",
            name="Claude 3 Opus",
            description="Highest quality, slower and more expensive",
            cost_per_1m_input=15.0,
            cost_per_1m_output=75.0,
            recommended=False
        ),
        AvailableModel(
            model_id="anthropic/claude-3-haiku",
            provider="Anthropic",
            name="Claude 3 Haiku",
            description="Faster and cheaper, good for simple extractions",
            cost_per_1m_input=0.25,
            cost_per_1m_output=1.25,
            recommended=False
        ),
        AvailableModel(
            model_id="google/gemini-pro-1.5",
            provider="Google",
            name="Gemini Pro 1.5",
            description="Google's advanced model with long context",
            cost_per_1m_input=1.25,
            cost_per_1m_output=5.0,
            recommended=False
        ),
        AvailableModel(
            model_id="openai/gpt-4-turbo",
            provider="OpenAI",
            name="GPT-4 Turbo",
            description="OpenAI's latest GPT-4 variant",
            cost_per_1m_input=10.0,
            cost_per_1m_output=30.0,
            recommended=False
        ),
    ]


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_batches": len(active_batches),
        "historical_batches": len(batch_history)
    }


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from orchestration API
        log_level="info"
    )
