"""
Intent Classification API Endpoints
===================================

FastAPI router for intent classification with RLCF feedback integration.

Endpoints:
- POST /intent/classify - Classify intent from query + NER context
- GET /intent/classifications - List classifications with filters
- POST /intent/validate - Submit RLCF feedback/validation
- GET /intent/review-queue - Get pending review tasks
- GET /intent/stats - Classification statistics
- GET /intent/training-data - Export ground truth dataset

Integration:
- backend/orchestration/intent_classifier.py (classifier logic)
- backend/rlcf_framework/models_intent.py (database models)

Reference: docs/02-methodology/query-understanding.md Stage 4
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.orchestration.intent_classifier import (
    get_intent_classifier,
    IntentType,
    IntentResult,
    reload_intent_classifier
)
from backend.rlcf_framework.models_intent import (
    IntentClassification,
    IntentValidationFeedback,
    IntentClassificationStats,
    IntentTypeEnum,
    ValidationStatusEnum
)
from backend.rlcf_framework.database import SessionLocal

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/intent", tags=["intent_classification"])


# ===================================
# Request/Response Models
# ===================================

class NormReference(BaseModel):
    """Norm reference from NER pipeline"""
    text: str
    act_type: Optional[str] = None
    article: Optional[str] = None
    act_number: Optional[str] = None
    date: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class IntentClassifyRequest(BaseModel):
    """Request for intent classification"""
    query: str = Field(..., min_length=10, max_length=2000, description="Legal query text")
    norm_references: Optional[List[NormReference]] = Field(
        None,
        description="References extracted by NER pipeline"
    )
    context: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional context"
    )


class IntentClassifyResponse(BaseModel):
    """Response from intent classification"""
    classification_id: str
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    needs_review: bool
    timestamp: datetime
    model_version: str
    classification_source: str


class IntentValidateRequest(BaseModel):
    """RLCF feedback on intent classification"""
    classification_id: str
    user_id: str = Field(..., description="ID of validating expert")
    validated_intent: str = Field(..., description="Expert's correction/validation")
    is_correct: Optional[bool] = Field(None, description="Whether original classification was correct")
    correction_reasoning: Optional[str] = Field(
        None,
        max_length=1000,
        description="Why expert provided this feedback"
    )
    confidence_in_validation: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Expert's confidence in their feedback"
    )
    user_authority_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="RLCF authority score (A_u(t))"
    )


class IntentValidateResponse(BaseModel):
    """Response to validation feedback"""
    feedback_id: str
    classification_id: str
    status: str = "accepted"
    authority_weighted_contribution: float
    message: str


class IntentClassificationListItem(BaseModel):
    """Item in classifications list"""
    id: str
    query_text: str
    predicted_intent: str
    confidence: float
    community_validated: bool
    validation_status: str
    created_at: datetime


class IntentReviewTask(BaseModel):
    """Task for community review"""
    classification_id: str
    query_text: str
    predicted_intent: str
    confidence: float
    reasoning: str
    uncertainty_score: float
    priority: str  # 'low', 'normal', 'high'


class IntentStatsResponse(BaseModel):
    """Statistics on intent classifications"""
    total_classifications: int
    by_intent: Dict[str, int]
    community_validated_count: int
    validation_rate: float  # 0.0 to 1.0
    avg_confidence: float
    pending_reviews: int
    ground_truth_samples: int


# ===================================
# Endpoint Implementations
# ===================================

@router.post(
    "/classify",
    response_model=IntentClassifyResponse,
    summary="Classify intent of legal query"
)
async def classify_intent(
    request: IntentClassifyRequest
) -> IntentClassifyResponse:
    """
    Classify the intent of a legal query using OpenRouter LLM (Phase 1) or
    fine-tuned model (Phase 2+).

    The response includes:
    - Intent classification (one of 4 types)
    - Confidence score
    - Reasoning from classifier
    - Flag for community review if confidence < threshold

    RLCF feedback is automatically collected for ground truth building.

    Example:
    ```bash
    curl -X POST http://localhost:8000/intent/classify \
      -H "Content-Type: application/json" \
      -d '{
        "query": "Cosa significa questa clausola di non concorrenza?",
        "norm_references": [
          {
            "text": "art. 2043 c.c.",
            "act_type": "codice_civile",
            "article": "2043"
          }
        ]
      }'
    ```
    """
    try:
        classifier = await get_intent_classifier()

        # Convert request to function call
        norm_refs = [ref.dict() for ref in request.norm_references] if request.norm_references else None

        # Classify intent
        result: IntentResult = await classifier.classify_intent(
            query_text=request.query,
            norm_references=norm_refs,
            context=request.context
        )

        # Generate classification ID (for linking to feedback)
        classification_id = classifier.feedback_collector._generate_classification_id()

        # Return response
        return IntentClassifyResponse(
            classification_id=classification_id,
            intent=result.intent.value,
            confidence=result.confidence,
            reasoning=result.reasoning,
            needs_review=result.needs_review,
            timestamp=result.timestamp,
            model_version=result.model_version,
            classification_source=result.classification_source
        )

    except Exception as e:
        logger.error(f"Error classifying intent: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Intent classification failed: {str(e)}"
        )


@router.get(
    "/classifications",
    response_model=List[IntentClassificationListItem],
    summary="List intent classifications"
)
async def list_classifications(
    intent: Optional[str] = Query(None, description="Filter by intent type"),
    validated_only: bool = Query(False, description="Only validated classifications"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(SessionLocal)
) -> List[IntentClassificationListItem]:
    """
    List intent classifications with optional filtering.

    Useful for:
    - Reviewing recent classifications
    - Finding patterns
    - Quality assurance

    Query parameters:
    - intent: Filter by specific intent type
    - validated_only: Show only community-validated classifications
    - limit: Number of results (default 20, max 100)
    - offset: Pagination offset
    """
    try:
        query = db.query(IntentClassification)

        if intent:
            query = query.filter(IntentClassification.predicted_intent == intent)

        if validated_only:
            query = query.filter(IntentClassification.community_validated == True)

        classifications = query.order_by(
            IntentClassification.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            IntentClassificationListItem(
                id=c.id,
                query_text=c.query_text,
                predicted_intent=c.predicted_intent.value,
                confidence=c.confidence,
                community_validated=c.community_validated,
                validation_status=c.validation_status.value if c.validation_status else "pending_review",
                created_at=c.created_at
            )
            for c in classifications
        ]

    except Exception as e:
        logger.error(f"Error listing classifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/validate",
    response_model=IntentValidateResponse,
    summary="Submit RLCF feedback"
)
async def submit_validation(
    request: IntentValidateRequest,
    db: Session = Depends(SessionLocal)
) -> IntentValidateResponse:
    """
    Submit community feedback/validation on an intent classification.

    This is the core RLCF feedback loop:
    1. Expert reviews classification
    2. Provides validation (correct/incorrect)
    3. Optionally provides correction
    4. Feedback is authority-weighted
    5. Aggregated into ground truth dataset

    Authority weighting:
    - Higher authority experts have more influence (A_u(t))
    - Feedback weight = (authority_score ^ 1.5) / sum(all_weights)
    - Used for training Phase 2 fine-tuned model

    Example:
    ```bash
    curl -X POST http://localhost:8000/intent/validate \
      -H "Content-Type: application/json" \
      -d '{
        "classification_id": "uuid-here",
        "user_id": "expert_001",
        "validated_intent": "contract_interpretation",
        "is_correct": true,
        "user_authority_score": 0.85
      }'
    ```
    """
    try:
        # Verify classification exists
        classification = db.query(IntentClassification).filter(
            IntentClassification.id == request.classification_id
        ).first()

        if not classification:
            raise HTTPException(status_code=404, detail="Classification not found")

        # Create feedback record
        feedback = IntentValidationFeedback(
            classification_id=request.classification_id,
            user_id=request.user_id,
            user_authority_score=request.user_authority_score,
            validated_intent=IntentTypeEnum(request.validated_intent),
            is_correct=request.is_correct,
            correction_reasoning=request.correction_reasoning,
            confidence_in_validation=request.confidence_in_validation,
            feedback_weight=request.user_authority_score ** 1.5  # Simple weighting for now
        )

        db.add(feedback)

        # Update classification tracking
        classification.num_community_validations += 1
        if request.is_correct:
            classification.validation_status = ValidationStatusEnum.VALIDATED
        else:
            classification.validation_status = ValidationStatusEnum.DISPUTED

        db.commit()

        return IntentValidateResponse(
            feedback_id=feedback.id,
            classification_id=request.classification_id,
            status="accepted",
            authority_weighted_contribution=feedback.feedback_weight,
            message=f"Feedback accepted. Authority weight: {feedback.feedback_weight:.3f}"
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid intent type: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting validation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/review-queue",
    response_model=List[IntentReviewTask],
    summary="Get pending review tasks"
)
async def get_review_queue(
    limit: int = Query(10, ge=1, le=50),
    min_priority: str = Query("normal", description="Minimum priority: low, normal, high"),
    db: Session = Depends(SessionLocal)
) -> List[IntentReviewTask]:
    """
    Get intent classifications pending community review.

    Sorted by uncertainty/priority for active learning.

    Use this endpoint to:
    1. Get uncertain classifications that need human review
    2. Build the RLCF community review interface
    3. Identify hard cases for model improvement
    """
    try:
        tasks = IntentClassificationStats.get_pending_reviews(db, limit=limit)

        priority_map = {
            "high": 0,      # Reviewed first
            "normal": 1,
            "low": 2
        }
        min_priority_val = priority_map.get(min_priority, 1)

        return [
            IntentReviewTask(
                classification_id=task.id,
                query_text=task.query_text,
                predicted_intent=task.predicted_intent.value,
                confidence=task.confidence,
                reasoning=task.reasoning or "",
                uncertainty_score=task.uncertainty_score or (1.0 - task.confidence),
                priority="high" if task.confidence < 0.7 else "normal"
            )
            for task in tasks
        ]

    except Exception as e:
        logger.error(f"Error fetching review queue: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stats",
    response_model=IntentStatsResponse,
    summary="Get classification statistics"
)
async def get_stats(
    db: Session = Depends(SessionLocal)
) -> IntentStatsResponse:
    """
    Get statistics on intent classifications.

    Useful for monitoring:
    - Classification distribution
    - Community validation rate
    - Model quality metrics
    - Ground truth dataset size
    """
    try:
        total = db.query(IntentClassification).count()
        validated = db.query(IntentClassification).filter(
            IntentClassification.community_validated == True
        ).count()

        # Distribution by intent
        by_intent_raw = db.query(
            IntentClassification.predicted_intent,
            IntentClassification.predicted_intent
        ).group_by(IntentClassification.predicted_intent).count()

        by_intent = {
            IntentType.CONTRACT_INTERPRETATION.value: 0,
            IntentType.COMPLIANCE_QUESTION.value: 0,
            IntentType.NORM_EXPLANATION.value: 0,
            IntentType.PRECEDENT_SEARCH.value: 0,
            IntentType.UNKNOWN.value: 0
        }

        # Calculate averages
        avg_conf = db.query(IntentClassification.confidence).all()
        avg_confidence = sum(c[0] for c in avg_conf) / len(avg_conf) if avg_conf else 0.0

        pending_reviews = db.query(IntentClassification).filter(
            IntentClassification.needs_community_review == True
        ).count()

        ground_truth = db.query(IntentClassification).filter(
            IntentClassification.validation_status == ValidationStatusEnum.GROUND_TRUTH
        ).count()

        return IntentStatsResponse(
            total_classifications=total,
            by_intent=by_intent,
            community_validated_count=validated,
            validation_rate=validated / total if total > 0 else 0.0,
            avg_confidence=avg_confidence,
            pending_reviews=pending_reviews,
            ground_truth_samples=ground_truth
        )

    except Exception as e:
        logger.error(f"Error calculating stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/training-data",
    response_model=Dict[str, Any],
    summary="Export ground truth dataset"
)
async def export_training_data(
    format: str = Query("json", description="Format: json, csv"),
    min_authority: float = Query(0.6, ge=0.0, le=1.0),
    db: Session = Depends(SessionLocal)
) -> Dict[str, Any]:
    """
    Export validated classifications for Phase 2 model fine-tuning.

    Returns only high-authority validated classifications suitable for
    training. Used to transition from Phase 1 (OpenRouter) to Phase 2
    (fine-tuned model).

    Filtering:
    - Only validated classifications (community consensus)
    - Only high authority aggregated scores (min_authority)
    - Minimum 3 validations per classification

    This dataset powers Phase 2 fine-tuning of Italian-Legal-BERT.
    """
    try:
        ground_truth = IntentClassificationStats.get_ground_truth_dataset(
            db,
            min_authority=min_authority
        )

        if format == "json":
            return {
                "format": "json",
                "count": len(ground_truth),
                "min_authority": min_authority,
                "samples": [
                    {
                        "id": c.id,
                        "query_text": c.query_text,
                        "intent": c.validated_intent.value if c.validated_intent else c.predicted_intent.value,
                        "confidence": c.authority_scores_aggregated or c.confidence,
                        "norm_references": c.norm_references,
                        "num_validations": c.num_community_validations
                    }
                    for c in ground_truth
                ]
            }
        else:
            # CSV format - prepare as list of dicts for conversion
            return {
                "format": "csv",
                "count": len(ground_truth),
                "message": "CSV export not yet implemented - use json format"
            }

    except Exception as e:
        logger.error(f"Error exporting training data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reload",
    summary="Reload intent classifier configuration"
)
async def reload_classifier():
    """
    Hot-reload intent classifier configuration without server restart.

    Useful for:
    - Updating intent types
    - Changing LLM model parameters
    - Deploying Phase 2 fine-tuned model
    """
    try:
        await reload_intent_classifier()
        return {
            "status": "success",
            "message": "Intent classifier configuration reloaded"
        }
    except Exception as e:
        logger.error(f"Error reloading classifier: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
