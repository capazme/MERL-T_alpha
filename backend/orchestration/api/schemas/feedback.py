"""
Pydantic schemas for feedback submission endpoints.

Implements 3 feedback mechanisms as per MERL-T methodology:
1. User Feedback - General rating from end users
2. RLCF Expert Feedback - Detailed corrections from legal experts
3. NER Corrections - Entity extraction corrections for model training
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# USER FEEDBACK SCHEMAS
# ============================================================================

class FeedbackCategories(BaseModel):
    """Detailed feedback categories for user rating."""

    accuracy: int = Field(
        ...,
        ge=1,
        le=5,
        description="Legal accuracy (1-5 stars)"
    )
    completeness: int = Field(
        ...,
        ge=1,
        le=5,
        description="Completeness of answer (1-5 stars)"
    )
    clarity: int = Field(
        ...,
        ge=1,
        le=5,
        description="Clarity and understandability (1-5 stars)"
    )
    legal_soundness: int = Field(
        ...,
        ge=1,
        le=5,
        description="Legal soundness and reasoning (1-5 stars)"
    )


class UserFeedbackRequest(BaseModel):
    """
    User feedback submission schema for POST /feedback/user.

    End users can rate answers with overall rating and detailed categories.
    """

    trace_id: str = Field(
        ...,
        description="Trace ID of the query being rated"
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID (optional, for tracking)"
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall rating (1-5 stars)"
    )
    feedback_text: Optional[str] = Field(
        None,
        max_length=2000,
        description="Free-text feedback from user"
    )
    categories: Optional[FeedbackCategories] = Field(
        None,
        description="Detailed category ratings"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "user_id": "user_789",
                "rating": 4,
                "feedback_text": "Risposta utile ma mancava riferimento a giurisprudenza",
                "categories": {
                    "accuracy": 4,
                    "completeness": 3,
                    "clarity": 5,
                    "legal_soundness": 4
                }
            }
        }


# ============================================================================
# RLCF EXPERT FEEDBACK SCHEMAS
# ============================================================================

class ConceptMappingCorrection(BaseModel):
    """Correction for concept mapping errors."""

    issue: str = Field(
        ...,
        description="Description of the concept mapping issue"
    )
    correction: Dict[str, Any] = Field(
        ...,
        description="Corrected concept mapping"
    )


class RoutingDecisionCorrection(BaseModel):
    """Correction for routing decision errors."""

    issue: str = Field(
        ...,
        description="Description of the routing issue"
    )
    improved_plan: Dict[str, Any] = Field(
        ...,
        description="Improved ExecutionPlan"
    )


class AnswerQualityCorrection(BaseModel):
    """Correction for answer quality issues."""

    validated_answer: str = Field(
        ...,
        description="Corrected legal answer"
    )
    position: Literal["correct", "partially_correct", "incorrect"] = Field(
        ...,
        description="Expert assessment of original answer"
    )
    reasoning: str = Field(
        ...,
        description="Expert reasoning for correction"
    )
    missing_norms: Optional[List[str]] = Field(
        None,
        description="Norm IDs that should have been included"
    )
    missing_jurisprudence: Optional[List[str]] = Field(
        None,
        description="Case law that should have been included"
    )


class RLCFCorrections(BaseModel):
    """Complete set of RLCF expert corrections."""

    concept_mapping: Optional[ConceptMappingCorrection] = Field(
        None,
        description="Corrections to concept mapping"
    )
    routing_decision: Optional[RoutingDecisionCorrection] = Field(
        None,
        description="Corrections to routing decision"
    )
    answer_quality: Optional[AnswerQualityCorrection] = Field(
        None,
        description="Corrections to answer quality"
    )


class RLCFFeedbackRequest(BaseModel):
    """
    RLCF expert feedback submission schema for POST /feedback/rlcf.

    Legal experts provide detailed corrections with authority weighting.
    """

    trace_id: str = Field(
        ...,
        description="Trace ID of the query being corrected"
    )
    expert_id: str = Field(
        ...,
        description="Expert identifier"
    )
    authority_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expert authority score (0-1), calculated from credentials"
    )
    corrections: RLCFCorrections = Field(
        ...,
        description="Detailed corrections to pipeline components"
    )
    overall_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Overall expert rating of the answer (1-5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "expert_id": "expert_456",
                "authority_score": 0.85,
                "corrections": {
                    "concept_mapping": {
                        "issue": "Missing concept: 'emancipazione'",
                        "correction": {
                            "action": "add_concept",
                            "concept_id": "emancipazione",
                            "confidence": 0.85
                        }
                    },
                    "routing_decision": {
                        "issue": "Should have activated Precedent_Analyst",
                        "improved_plan": {
                            "experts": ["literal_interpreter", "precedent_analyst"]
                        }
                    },
                    "answer_quality": {
                        "validated_answer": "Corrected legal answer...",
                        "position": "partially_correct",
                        "reasoning": "La risposta era corretta ma incompleta...",
                        "missing_norms": ["cc-art-390"],
                        "missing_jurisprudence": ["Cass-12450-2018"]
                    }
                },
                "overall_rating": 3
            }
        }


# ============================================================================
# NER CORRECTION SCHEMAS
# ============================================================================

class NERCorrectionData(BaseModel):
    """Detailed NER correction data."""

    text_span: str = Field(
        ...,
        description="Text span being corrected"
    )
    start_char: int = Field(
        ...,
        ge=0,
        description="Start character position in original query"
    )
    end_char: int = Field(
        ...,
        ge=0,
        description="End character position in original query"
    )
    correct_label: Optional[str] = Field(
        None,
        description="Correct entity label (None if SPURIOUS_ENTITY)"
    )
    incorrect_label: Optional[str] = Field(
        None,
        description="Incorrect label that was assigned (None if MISSING_ENTITY)"
    )
    attributes: Optional[Dict[str, Any]] = Field(
        None,
        description="Entity attributes (age, date, etc.)"
    )


class NERCorrectionRequest(BaseModel):
    """
    NER correction submission schema for POST /feedback/ner.

    Experts correct entity extraction errors for model training.
    """

    trace_id: str = Field(
        ...,
        description="Trace ID of the query with NER error"
    )
    expert_id: str = Field(
        ...,
        description="Expert identifier"
    )
    correction_type: Literal[
        "MISSING_ENTITY",
        "SPURIOUS_ENTITY",
        "WRONG_BOUNDARY",
        "WRONG_TYPE"
    ] = Field(
        ...,
        description="Type of NER correction"
    )
    correction: NERCorrectionData = Field(
        ...,
        description="Detailed correction data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "expert_id": "expert_456",
                "correction_type": "MISSING_ENTITY",
                "correction": {
                    "text_span": "sedicenne",
                    "start_char": 37,
                    "end_char": 46,
                    "correct_label": "PERSON",
                    "incorrect_label": None,
                    "attributes": {
                        "age": 16
                    }
                }
            }
        }


# ============================================================================
# FEEDBACK RESPONSE SCHEMAS
# ============================================================================

class FeedbackResponse(BaseModel):
    """
    Common response schema for all feedback submission endpoints.
    """

    feedback_id: str = Field(
        ...,
        description="Unique feedback identifier"
    )
    status: Literal["accepted", "rejected", "pending"] = Field(
        ...,
        description="Feedback processing status"
    )
    trace_id: str = Field(
        ...,
        description="Original query trace ID"
    )
    authority_weight: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Authority weight applied (for RLCF feedback)"
    )
    training_examples_generated: Optional[int] = Field(
        None,
        ge=0,
        description="Number of training examples generated (for RLCF/NER)"
    )
    scheduled_for_retraining: Optional[bool] = Field(
        None,
        description="Whether correction is scheduled for model retraining"
    )
    next_retrain_date: Optional[str] = Field(
        None,
        description="Next scheduled retraining date (ISO 8601)"
    )
    message: Optional[str] = Field(
        None,
        description="Additional message about feedback processing"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Feedback submission timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_id": "FB-RLCF-456",
                "status": "accepted",
                "trace_id": "QRY-20250105-abc123",
                "authority_weight": 0.85,
                "training_examples_generated": 3,
                "scheduled_for_retraining": True,
                "next_retrain_date": "2025-01-12",
                "timestamp": "2025-01-05T14:35:00Z"
            }
        }
