"""
Feedback Router

FastAPI router for feedback submission endpoints.

Implements 3 feedback mechanisms:
1. User Feedback - General ratings from end users
2. RLCF Expert Feedback - Detailed corrections from legal experts
3. NER Corrections - Entity extraction corrections for model training
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from ..schemas.feedback import (
    UserFeedbackRequest,
    RLCFFeedbackRequest,
    NERCorrectionRequest,
    FeedbackResponse,
)
from ..services.feedback_processor import FeedbackProcessor

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)

# Global FeedbackProcessor instance (singleton pattern)
feedback_processor = FeedbackProcessor()


@router.post(
    "/user",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit User Feedback",
    description="""
Submit general user feedback for a query answer.

End users can rate answers with:
- **Overall rating** (1-5 stars)
- **Detailed categories**: accuracy, completeness, clarity, legal_soundness
- **Free-text feedback**

This feedback is used to:
- Track user satisfaction metrics
- Identify low-quality answers for review
- Inform future model improvements
    """,
    responses={
        201: {
            "description": "User feedback accepted",
            "content": {
                "application/json": {
                    "example": {
                        "feedback_id": "FB-USER-20250105-abc123",
                        "status": "accepted",
                        "trace_id": "QRY-20250105-abc123",
                        "message": "User feedback accepted. Rating: 4/5"
                    }
                }
            }
        },
        400: {"description": "Invalid feedback request"},
        500: {"description": "Internal server error"}
    }
)
async def submit_user_feedback(
    feedback: UserFeedbackRequest
) -> FeedbackResponse:
    """
    Submit user feedback for a query answer.

    Args:
        feedback: UserFeedbackRequest with rating and comments

    Returns:
        FeedbackResponse with acceptance status

    Raises:
        HTTPException: 400 for invalid request, 500 for errors
    """
    try:
        logger.info(
            f"Received user feedback for trace_id={feedback.trace_id}, "
            f"rating={feedback.rating}"
        )

        # Process feedback via FeedbackProcessor
        response = await feedback_processor.process_user_feedback(feedback)

        logger.info(
            f"[{response.feedback_id}] User feedback processed successfully"
        )

        return response

    except ValueError as e:
        logger.error(f"Invalid user feedback request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user feedback request: {str(e)}"
        )

    except Exception as e:
        logger.error(f"User feedback processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during feedback processing: {str(e)}"
        )


@router.post(
    "/rlcf",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit RLCF Expert Feedback",
    description="""
Submit detailed corrections from legal experts (RLCF feedback).

Legal experts can provide corrections for:
- **Concept mapping errors** (missing/incorrect legal concepts)
- **Routing decision errors** (wrong expert selection)
- **Answer quality issues** (incorrect/incomplete legal reasoning)

This feedback is used to:
- Generate training examples for model fine-tuning
- Improve routing decisions
- Enhance legal reasoning quality

Expert corrections are **authority-weighted** based on demonstrated competence.
    """,
    responses={
        201: {
            "description": "RLCF feedback accepted",
            "content": {
                "application/json": {
                    "example": {
                        "feedback_id": "FB-RLCF-20250105-abc123",
                        "status": "accepted",
                        "trace_id": "QRY-20250105-abc123",
                        "authority_weight": 0.85,
                        "training_examples_generated": 3,
                        "scheduled_for_retraining": True,
                        "next_retrain_date": "2025-01-12"
                    }
                }
            }
        },
        400: {"description": "Invalid RLCF feedback request"},
        500: {"description": "Internal server error"}
    }
)
async def submit_rlcf_feedback(
    feedback: RLCFFeedbackRequest
) -> FeedbackResponse:
    """
    Submit RLCF expert feedback with detailed corrections.

    Args:
        feedback: RLCFFeedbackRequest with corrections and authority score

    Returns:
        FeedbackResponse with retraining schedule

    Raises:
        HTTPException: 400 for invalid request, 500 for errors
    """
    try:
        logger.info(
            f"Received RLCF feedback from expert_id={feedback.expert_id} "
            f"(authority={feedback.authority_score:.2f}) for trace_id={feedback.trace_id}"
        )

        # Process feedback via FeedbackProcessor
        response = await feedback_processor.process_rlcf_feedback(feedback)

        logger.info(
            f"[{response.feedback_id}] RLCF feedback processed successfully. "
            f"Training examples: {response.training_examples_generated}, "
            f"Retraining scheduled: {response.scheduled_for_retraining}"
        )

        return response

    except ValueError as e:
        logger.error(f"Invalid RLCF feedback request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid RLCF feedback request: {str(e)}"
        )

    except Exception as e:
        logger.error(f"RLCF feedback processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during RLCF feedback processing: {str(e)}"
        )


@router.post(
    "/ner",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit NER Correction",
    description="""
Submit entity extraction correction for model training.

Experts can correct 4 types of NER errors:
- **MISSING_ENTITY**: Entity was not detected
- **SPURIOUS_ENTITY**: False positive entity detection
- **WRONG_BOUNDARY**: Entity boundaries incorrect
- **WRONG_TYPE**: Entity type misclassified

This feedback is used to:
- Generate training examples for NER model fine-tuning
- Improve entity extraction accuracy
- Fix systematic extraction errors

NER corrections are accumulated and trigger batch retraining when threshold is reached.
    """,
    responses={
        201: {
            "description": "NER correction accepted",
            "content": {
                "application/json": {
                    "example": {
                        "feedback_id": "FB-NER-20250105-abc123",
                        "status": "accepted",
                        "trace_id": "QRY-20250105-abc123",
                        "training_examples_generated": 1,
                        "scheduled_for_retraining": False,
                        "next_retrain_date": "2025-01-12"
                    }
                }
            }
        },
        400: {"description": "Invalid NER correction request"},
        500: {"description": "Internal server error"}
    }
)
async def submit_ner_correction(
    correction: NERCorrectionRequest
) -> FeedbackResponse:
    """
    Submit NER correction for entity extraction errors.

    Args:
        correction: NERCorrectionRequest with correction type and data

    Returns:
        FeedbackResponse with retraining schedule

    Raises:
        HTTPException: 400 for invalid request, 500 for errors
    """
    try:
        logger.info(
            f"Received NER correction from expert_id={correction.expert_id} "
            f"for trace_id={correction.trace_id}, type={correction.correction_type}"
        )

        # Process correction via FeedbackProcessor
        response = await feedback_processor.process_ner_correction(correction)

        logger.info(
            f"[{response.feedback_id}] NER correction processed successfully. "
            f"Retraining scheduled: {response.scheduled_for_retraining}"
        )

        return response

    except ValueError as e:
        logger.error(f"Invalid NER correction request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid NER correction request: {str(e)}"
        )

    except Exception as e:
        logger.error(f"NER correction processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during NER correction processing: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get Feedback Statistics",
    description="""
Retrieve feedback statistics and retraining status.

Returns:
- Counts of user feedback, RLCF feedback, NER corrections
- Retraining thresholds
- Retraining readiness status
    """
)
async def get_feedback_stats() -> Dict[str, Any]:
    """
    Get feedback statistics.

    Returns:
        Dictionary with feedback counts and retraining status
    """
    try:
        logger.info("Feedback stats requested")

        stats = feedback_processor.get_feedback_stats()

        logger.info(
            f"Feedback stats: user={stats['user_feedback_count']}, "
            f"rlcf={stats['rlcf_feedback_count']}, "
            f"ner={stats['ner_corrections_count']}"
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to retrieve feedback stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error retrieving feedback stats: {str(e)}"
        )
