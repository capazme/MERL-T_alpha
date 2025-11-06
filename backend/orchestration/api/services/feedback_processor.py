"""
Feedback Processor Service

Processes 3 types of feedback submissions:
1. User Feedback - General ratings
2. RLCF Expert Feedback - Detailed corrections with authority weighting
3. NER Corrections - Entity extraction corrections for model training
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..schemas.feedback import (
    UserFeedbackRequest,
    RLCFFeedbackRequest,
    NERCorrectionRequest,
    FeedbackResponse,
)

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """
    Service for processing feedback submissions and scheduling retraining.

    Handles storage, validation, and orchestration of feedback loops.
    """

    def __init__(self):
        """Initialize Feedback Processor."""
        # In-memory storage (TODO: Replace with PostgreSQL persistence)
        self._user_feedback_store: Dict[str, Dict[str, Any]] = {}
        self._rlcf_feedback_store: Dict[str, Dict[str, Any]] = {}
        self._ner_corrections_store: Dict[str, Dict[str, Any]] = {}

        # Retraining thresholds
        self.rlcf_retrain_threshold = 10  # Retrain after 10 RLCF corrections
        self.ner_retrain_threshold = 20   # Retrain after 20 NER corrections

        logger.info("FeedbackProcessor initialized")

    def _generate_feedback_id(self, feedback_type: str) -> str:
        """Generate unique feedback ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"FB-{feedback_type.upper()}-{timestamp}-{unique_id}"

    def _calculate_next_retrain_date(self, current_count: int, threshold: int) -> Optional[str]:
        """
        Calculate next retraining date based on feedback accumulation.

        Args:
            current_count: Current number of feedback items
            threshold: Threshold for triggering retraining

        Returns:
            ISO date string for next retraining, or None if not scheduled
        """
        if current_count >= threshold:
            # Immediate retraining (within 24 hours)
            next_retrain = datetime.utcnow() + timedelta(hours=24)
            return next_retrain.date().isoformat()
        else:
            # Weekly batch retraining
            days_until_sunday = (6 - datetime.utcnow().weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            next_retrain = datetime.utcnow() + timedelta(days=days_until_sunday)
            return next_retrain.date().isoformat()

    async def process_user_feedback(
        self,
        feedback: UserFeedbackRequest
    ) -> FeedbackResponse:
        """
        Process user feedback submission.

        Args:
            feedback: UserFeedbackRequest with rating and comments

        Returns:
            FeedbackResponse with acceptance status
        """
        feedback_id = self._generate_feedback_id("user")

        logger.info(
            f"[{feedback_id}] Processing user feedback for trace_id={feedback.trace_id}, "
            f"rating={feedback.rating}"
        )

        # Store feedback (TODO: Replace with database)
        feedback_data = {
            "feedback_id": feedback_id,
            "trace_id": feedback.trace_id,
            "user_id": feedback.user_id,
            "rating": feedback.rating,
            "feedback_text": feedback.feedback_text,
            "categories": feedback.categories.model_dump() if feedback.categories else None,
            "timestamp": datetime.utcnow(),
        }
        self._user_feedback_store[feedback_id] = feedback_data

        logger.info(
            f"[{feedback_id}] User feedback stored successfully. "
            f"Total user feedback: {len(self._user_feedback_store)}"
        )

        # Build response
        response = FeedbackResponse(
            feedback_id=feedback_id,
            status="accepted",
            trace_id=feedback.trace_id,
            message=f"User feedback accepted. Rating: {feedback.rating}/5",
            timestamp=datetime.utcnow(),
        )

        return response

    async def process_rlcf_feedback(
        self,
        feedback: RLCFFeedbackRequest
    ) -> FeedbackResponse:
        """
        Process RLCF expert feedback submission.

        Args:
            feedback: RLCFFeedbackRequest with detailed corrections

        Returns:
            FeedbackResponse with retraining schedule
        """
        feedback_id = self._generate_feedback_id("rlcf")

        logger.info(
            f"[{feedback_id}] Processing RLCF feedback from expert_id={feedback.expert_id} "
            f"(authority={feedback.authority_score:.2f}) for trace_id={feedback.trace_id}"
        )

        # Generate training examples from corrections
        training_examples_count = 0

        # Concept mapping correction → training example
        if feedback.corrections.concept_mapping:
            training_examples_count += 1
            logger.info(
                f"[{feedback_id}] Concept mapping correction: "
                f"{feedback.corrections.concept_mapping.issue}"
            )

        # Routing decision correction → training example
        if feedback.corrections.routing_decision:
            training_examples_count += 1
            logger.info(
                f"[{feedback_id}] Routing decision correction: "
                f"{feedback.corrections.routing_decision.issue}"
            )

        # Answer quality correction → training example
        if feedback.corrections.answer_quality:
            training_examples_count += 1
            logger.info(
                f"[{feedback_id}] Answer quality correction: "
                f"{feedback.corrections.answer_quality.position}"
            )

        # Store feedback (TODO: Replace with database)
        feedback_data = {
            "feedback_id": feedback_id,
            "trace_id": feedback.trace_id,
            "expert_id": feedback.expert_id,
            "authority_score": feedback.authority_score,
            "corrections": feedback.corrections.model_dump(),
            "overall_rating": feedback.overall_rating,
            "training_examples_generated": training_examples_count,
            "timestamp": datetime.utcnow(),
        }
        self._rlcf_feedback_store[feedback_id] = feedback_data

        # Check if retraining threshold reached
        current_count = len(self._rlcf_feedback_store)
        scheduled_for_retraining = current_count >= self.rlcf_retrain_threshold
        next_retrain_date = self._calculate_next_retrain_date(
            current_count,
            self.rlcf_retrain_threshold
        )

        logger.info(
            f"[{feedback_id}] RLCF feedback stored successfully. "
            f"Total RLCF feedback: {current_count}, "
            f"Training examples: {training_examples_count}, "
            f"Scheduled for retraining: {scheduled_for_retraining}"
        )

        # Build response
        response = FeedbackResponse(
            feedback_id=feedback_id,
            status="accepted",
            trace_id=feedback.trace_id,
            authority_weight=feedback.authority_score,
            training_examples_generated=training_examples_count,
            scheduled_for_retraining=scheduled_for_retraining,
            next_retrain_date=next_retrain_date,
            message=f"RLCF feedback accepted from expert with authority {feedback.authority_score:.2f}",
            timestamp=datetime.utcnow(),
        )

        return response

    async def process_ner_correction(
        self,
        correction: NERCorrectionRequest
    ) -> FeedbackResponse:
        """
        Process NER correction submission.

        Args:
            correction: NERCorrectionRequest with entity correction

        Returns:
            FeedbackResponse with retraining schedule
        """
        feedback_id = self._generate_feedback_id("ner")

        logger.info(
            f"[{feedback_id}] Processing NER correction from expert_id={correction.expert_id} "
            f"for trace_id={correction.trace_id}, type={correction.correction_type}"
        )

        # Store correction (TODO: Replace with database)
        correction_data = {
            "feedback_id": feedback_id,
            "trace_id": correction.trace_id,
            "expert_id": correction.expert_id,
            "correction_type": correction.correction_type,
            "correction": correction.correction.model_dump(),
            "timestamp": datetime.utcnow(),
        }
        self._ner_corrections_store[feedback_id] = correction_data

        # Check if retraining threshold reached
        current_count = len(self._ner_corrections_store)
        scheduled_for_retraining = current_count >= self.ner_retrain_threshold
        next_retrain_date = self._calculate_next_retrain_date(
            current_count,
            self.ner_retrain_threshold
        )

        logger.info(
            f"[{feedback_id}] NER correction stored successfully. "
            f"Total NER corrections: {current_count}, "
            f"Scheduled for retraining: {scheduled_for_retraining}"
        )

        # Build response
        response = FeedbackResponse(
            feedback_id=feedback_id,
            status="accepted",
            trace_id=correction.trace_id,
            training_examples_generated=1,  # Each correction = 1 training example
            scheduled_for_retraining=scheduled_for_retraining,
            next_retrain_date=next_retrain_date,
            message=f"NER correction accepted: {correction.correction_type}",
            timestamp=datetime.utcnow(),
        )

        return response

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics for analytics.

        Returns:
            Dictionary with feedback counts and retraining status
        """
        return {
            "user_feedback_count": len(self._user_feedback_store),
            "rlcf_feedback_count": len(self._rlcf_feedback_store),
            "ner_corrections_count": len(self._ner_corrections_store),
            "rlcf_retrain_threshold": self.rlcf_retrain_threshold,
            "ner_retrain_threshold": self.ner_retrain_threshold,
            "rlcf_retraining_ready": len(self._rlcf_feedback_store) >= self.rlcf_retrain_threshold,
            "ner_retraining_ready": len(self._ner_corrections_store) >= self.ner_retrain_threshold,
        }

    async def trigger_retraining(self, model_type: str) -> Dict[str, Any]:
        """
        Trigger retraining for a specific model type.

        Args:
            model_type: "rlcf" or "ner"

        Returns:
            Retraining job information
        """
        logger.info(f"Triggering {model_type} model retraining...")

        # TODO: Implement actual retraining pipeline
        # This would:
        # 1. Collect training examples from feedback stores
        # 2. Prepare training dataset
        # 3. Submit retraining job to ML pipeline
        # 4. Clear processed feedback from stores

        if model_type == "rlcf":
            training_examples = len(self._rlcf_feedback_store)
        elif model_type == "ner":
            training_examples = len(self._ner_corrections_store)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        logger.info(
            f"{model_type.upper()} retraining triggered with {training_examples} examples"
        )

        return {
            "model_type": model_type,
            "training_examples": training_examples,
            "status": "submitted",
            "job_id": f"RETRAIN-{model_type.upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "estimated_completion": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        }
