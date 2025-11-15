"""
NER API Router
==============

FastAPI routes for Legal Entity Recognition (NER) preprocessing.
Provides endpoints for text extraction, model management, and active learning.

Integrated with MERL-T orchestration layer.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# MERL-T imports
from ..database import SessionLocal, get_db
from ..models_extension import TrainedModel, EvaluationRun, AnnotationTask, ModelStatus
from backend.orchestration.model_manager import get_model_manager, ModelMetrics
from backend.preprocessing.ner_module import LegalSourceExtractionPipeline
from backend.preprocessing.label_mapping import get_label_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ner", tags=["NER Pipeline"])


# ===================================
# Pydantic Schemas
# ===================================

class ExtractedEntity(BaseModel):
    """Extracted legal entity from text."""
    text: str
    start_char: int
    end_char: int
    label: str
    confidence: float
    act_type: Optional[str] = None
    article: Optional[str] = None
    act_number: Optional[str] = None
    date: Optional[str] = None


class NERRequest(BaseModel):
    """Request for NER extraction."""
    text: str = Field(..., min_length=10, max_length=10000, description="Text to extract entities from")
    return_metadata: bool = Field(False, description="Include pipeline metadata in response")


class NERResponse(BaseModel):
    """Response with extracted entities."""
    request_id: str
    entities: List[ExtractedEntity]
    text_length: int
    entity_count: int
    requires_review: bool
    metadata: Optional[Dict[str, Any]] = None


class ModelInfo(BaseModel):
    """Information about a trained model."""
    version: str
    status: str
    model_path: str
    is_active: bool
    f1_score: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    accuracy: Optional[float] = None
    created_at: str


class ModelListResponse(BaseModel):
    """Response listing all models."""
    total_models: int
    models: List[ModelInfo]


class ActivateModelRequest(BaseModel):
    """Request to activate a model."""
    version: str = Field(..., description="Model version to activate")


class ActivateModelResponse(BaseModel):
    """Response to model activation."""
    success: bool
    message: str
    version: Optional[str] = None
    error: Optional[str] = None


class CompareModelsRequest(BaseModel):
    """Request to compare two models."""
    version_1: str
    version_2: str


class CompareModelsResponse(BaseModel):
    """Response with model comparison results."""
    model_1: Dict[str, Any]
    model_2: Dict[str, Any]
    delta: Dict[str, float]
    winner: str


# ===================================
# Extraction Endpoints
# ===================================

@router.post("/extract", response_model=NERResponse, summary="Extract legal entities from text")
async def extract_entities(
    request: NERRequest,
    db=Depends(get_db),
    background_tasks: BackgroundTasks = None
) -> NERResponse:
    """
    Extract legal entities (norms, acts, references) from Italian legal text.

    Uses 5-stage NER pipeline with optional fine-tuned model support.

    **Response includes**:
    - Extracted entities with confidence scores
    - Character positions for highlighting
    - Flags for entries requiring human review

    **Entity types** (act_type):
    - decreto_legislativo, legge, codice_civile, costituzione
    - direttiva_ue, regolamento_ue, delibera_regionale, etc.
    """
    try:
        # Get configuration
        ner_config = {}  # TODO: Load from ner_config.yaml

        # Initialize pipeline
        model_manager = get_model_manager()
        pipeline = model_manager.get_active_pipeline()

        if not pipeline:
            # Initialize default rule-based pipeline if no model active
            pipeline = LegalSourceExtractionPipeline(config=ner_config)

        # Extract entities
        results = await pipeline.extract_legal_sources(request.text)

        # Convert to response format
        entities = []
        requires_review = False

        for result in results:
            entity = ExtractedEntity(
                text=result.get("text", ""),
                start_char=result.get("start_char", 0),
                end_char=result.get("end_char", 0),
                label=result.get("source_type", "unknown"),
                confidence=result.get("confidence", 0.0),
                act_type=result.get("act_type"),
                article=result.get("article"),
                act_number=result.get("act_number"),
                date=result.get("date")
            )
            entities.append(entity)

            # Flag for review if low confidence
            if entity.confidence < 0.7:
                requires_review = True

        # Generate request ID
        request_id = f"ner_{datetime.now().isoformat()}_{len(entities)}"

        response = NERResponse(
            request_id=request_id,
            entities=entities,
            text_length=len(request.text),
            entity_count=len(entities),
            requires_review=requires_review,
            metadata={"model_version": model_manager._active_model_version} if request.return_metadata else None
        )

        log.info(f"Extracted {len(entities)} entities from text (request_id={request_id})")

        return response

    except Exception as e:
        log.error(f"Error in entity extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# ===================================
# Model Management Endpoints
# ===================================

@router.get("/models", response_model=ModelListResponse, summary="List all trained NER models")
async def list_models(db=Depends(get_db)) -> ModelListResponse:
    """
    List all trained NER models with their status and metrics.

    Returns models sorted by creation date (newest first).
    """
    try:
        model_manager = get_model_manager()
        models_list = model_manager.list_models()

        model_infos = [
            ModelInfo(
                version=m["version"],
                status=m["status"],
                model_path=m["model_path"],
                is_active=m["is_active"],
                f1_score=m.get("metrics", {}).get("f1_score"),
                precision=m.get("metrics", {}).get("precision"),
                recall=m.get("metrics", {}).get("recall"),
                accuracy=m.get("metrics", {}).get("accuracy"),
                created_at=m["created_at"]
            )
            for m in models_list
        ]

        return ModelListResponse(
            total_models=len(model_infos),
            models=model_infos
        )

    except Exception as e:
        log.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.post("/models/activate", response_model=ActivateModelResponse, summary="Activate a model version")
async def activate_model(
    request: ActivateModelRequest,
    db=Depends(get_db)
) -> ActivateModelResponse:
    """
    Activate a specific trained model version.

    Hot-reloads the NER pipeline to use this model without server restart.
    """
    try:
        model_manager = get_model_manager()
        result = model_manager.activate_model(request.version)

        if result["success"]:
            log.info(f"Activated model {request.version}")
            return ActivateModelResponse(
                success=True,
                message=f"Model {request.version} activated successfully",
                version=request.version
            )
        else:
            log.warning(f"Failed to activate model {request.version}: {result.get('error')}")
            return ActivateModelResponse(
                success=False,
                message="Model activation failed",
                error=result.get("error")
            )

    except Exception as e:
        log.error(f"Error activating model: {e}")
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")


@router.post("/models/auto-select", response_model=ActivateModelResponse, summary="Auto-select best model")
async def auto_select_best_model(
    metric: str = Query("f1_score", description="Metric to optimize for (f1_score, precision, recall, accuracy)"),
    db=Depends(get_db)
) -> ActivateModelResponse:
    """
    Automatically select and activate the best performing model.

    Evaluates all models by the specified metric and activates the best one.
    """
    try:
        model_manager = get_model_manager()
        result = model_manager.auto_select_best_model(metric=metric)

        if result["success"]:
            log.info(f"Auto-selected best model for metric {metric}")
            return ActivateModelResponse(
                success=True,
                message=f"Auto-selected model {result.get('version')} (best {metric})",
                version=result.get("version")
            )
        else:
            log.warning(f"Auto-selection failed: {result.get('error')}")
            return ActivateModelResponse(
                success=False,
                message="Auto-selection failed",
                error=result.get("error")
            )

    except Exception as e:
        log.error(f"Error in auto-selection: {e}")
        raise HTTPException(status_code=500, detail=f"Auto-selection failed: {str(e)}")


@router.post("/models/compare", response_model=CompareModelsResponse, summary="Compare two models")
async def compare_models(
    request: CompareModelsRequest,
    db=Depends(get_db)
) -> CompareModelsResponse:
    """
    Compare two model versions by their evaluation metrics.

    Shows performance deltas and identifies the better model.
    """
    try:
        model_manager = get_model_manager()
        result = model_manager.compare_models(request.version_1, request.version_2)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return CompareModelsResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


# ===================================
# Configuration Management Endpoints
# ===================================

@router.post("/reload", summary="Reload NER pipeline configuration")
async def reload_pipeline(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Reload the NER pipeline with current configuration.

    Useful after updating ner_config.yaml or label mappings.
    """
    try:
        model_manager = get_model_manager()
        result = model_manager.reload_pipeline()

        if result["success"]:
            log.info("NER pipeline reloaded successfully")
            return result
        else:
            raise HTTPException(status_code=500, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error reloading pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


@router.get("/labels", summary="Get label mapping system")
async def get_labels() -> Dict[str, Any]:
    """
    Get current label mappings.

    Shows both traditional act types and semantic ontology labels.
    """
    try:
        label_manager = get_label_manager()

        return {
            "act_types": label_manager.get_all_act_types(),
            "display_labels": label_manager.get_all_labels(),
            "semantic_ontology": label_manager.get_semantic_ontology()
        }

    except Exception as e:
        log.error(f"Error getting labels: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve labels")


# ===================================
# Health & Statistics Endpoints
# ===================================

@router.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """
    Check NER pipeline health status.

    Returns status of models, pipeline, and configuration.
    """
    try:
        model_manager = get_model_manager()
        active_model = model_manager.get_active_model()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_model": {
                "version": active_model.version if active_model else None,
                "status": active_model.status if active_model else None
            } if active_model else None,
            "statistics": model_manager.get_model_stats()
        }

    except Exception as e:
        log.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/stats", summary="Get NER pipeline statistics")
async def get_stats(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Get statistics about NER models and predictions.

    Includes model count, status distribution, and active model info.
    """
    try:
        model_manager = get_model_manager()

        return {
            "models": model_manager.get_model_stats(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        log.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
