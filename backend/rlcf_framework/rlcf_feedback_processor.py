"""
RLCF Feedback Processor
======================

Processes RLCF (Reinforcement Learning from Community Feedback) results
and coordinates feedback distribution to learning systems.

Responsibilities:
1. Aggregate expert feedback on pipeline results
2. Calculate authority-weighted consensus
3. Detect controversies and conflicts
4. Distribute feedback to KG and NER systems
5. Update quality metrics based on feedback

The RLCF feedback loop enables:
- Continuous improvement of entity extraction (NER)
- Entity interpretation refinement
- Authority score updates
- Knowledge graph accuracy tracking
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from backend.rlcf_framework.models import (
    User,
    Task,
    TaskStatus,
    TaskType,
    ExpertFeedback,
    AggregationResult
)
from backend.rlcf_framework.authority_module import (
    calculate_authority_score,
    AuthorityScoreInput
)
from backend.rlcf_framework.aggregation_engine import (
    aggregate_feedback,
    AggregationStrategy
)
from backend.preprocessing.models_kg import (
    StagingEntity,
    KGEdgeAudit,
    ControversyRecord,
    ReviewStatusEnum,
    EntityTypeEnum,
    SourceTypeEnum
)


logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Type of expert feedback."""
    ENTITY_VALIDATION = "entity_validation"  # Entity is correct
    ENTITY_CORRECTION = "entity_correction"  # Entity is wrong, propose fix
    INTERPRETATION_VOTE = "interpretation_vote"  # Vote on entity interpretation
    CONTROVERSY_REPORT = "controversy_report"  # Flag controversial interpretation
    CONFIDENCE_ASSESSMENT = "confidence_assessment"  # Assess confidence score


class FeedbackSource(str, Enum):
    """Source of feedback."""
    EXPERT_PANEL = "expert_panel"
    COMMUNITY = "community"
    AUTOMATED_VALIDATION = "automated_validation"


class FeedbackDecision(str, Enum):
    """Decision based on aggregated feedback."""
    APPROVE = "approve"  # Entity accepted
    REJECT = "reject"  # Entity rejected
    REQUEST_REVISION = "request_revision"  # Entity needs revision
    FLAG_CONTROVERSY = "flag_controversy"  # Controversy exists
    ESCALATE_REVIEW = "escalate_review"  # Needs further review


class ExpertVote:
    """Single expert's vote on an entity."""

    def __init__(
        self,
        expert_id: str,
        entity_id: str,
        feedback_type: FeedbackType,
        vote_value: float,  # Usually -1, 0, 1 or 0-1 range
        confidence: float,  # Expert's confidence in vote
        explanation: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.vote_id = str(uuid.uuid4())
        self.expert_id = expert_id
        self.entity_id = entity_id
        self.feedback_type = feedback_type
        self.vote_value = vote_value
        self.confidence = confidence
        self.explanation = explanation
        self.timestamp = timestamp or datetime.utcnow()


class RLCFFeedbackProcessor:
    """
    Process and aggregate RLCF feedback on pipeline results.

    Workflow:
    1. Collect expert votes on entities
    2. Weight votes by expert authority
    3. Aggregate into consensus
    4. Detect controversies
    5. Distribute feedback to systems
    """

    def __init__(
        self,
        db_session: AsyncSession,
        authority_module=None,
        aggregation_engine=None
    ):
        """
        Initialize feedback processor.

        Args:
            db_session: Database session
            authority_module: Authority scoring module
            aggregation_engine: Feedback aggregation engine
        """
        self.db_session = db_session
        self.authority_module = authority_module
        self.aggregation_engine = aggregation_engine
        self.logger = logger

    async def process_expert_votes(
        self,
        entity_id: str,
        entity_type: EntityTypeEnum,
        votes: List[ExpertVote]
    ) -> Tuple[FeedbackDecision, Dict[str, Any]]:
        """
        Process expert votes on an entity.

        Flow:
        1. Validate votes
        2. Weight by authority
        3. Aggregate
        4. Make decision
        5. Detect controversies

        Args:
            entity_id: Entity being voted on
            entity_type: Type of entity (norm, sentenza, etc)
            votes: List of expert votes

        Returns:
            (decision, details) tuple
        """
        try:
            if not votes:
                return FeedbackDecision.REQUEST_REVISION, {"reason": "No votes received"}

            # Step 1: Collect expert authority scores
            weighted_votes = await self._weight_votes_by_authority(votes)

            # Step 2: Aggregate votes
            aggregation_result = await self._aggregate_votes(weighted_votes, entity_type)

            # Step 3: Make decision
            decision = self._make_decision(aggregation_result, entity_type)

            # Step 4: Detect controversies
            controversy_info = await self._detect_controversies(
                entity_id,
                weighted_votes,
                aggregation_result
            )

            # Step 5: Log result
            await self._log_feedback_result(
                entity_id,
                entity_type,
                votes,
                aggregation_result,
                decision,
                controversy_info
            )

            details = {
                "entity_id": entity_id,
                "votes_count": len(votes),
                "aggregation_result": aggregation_result,
                "controversy_detected": controversy_info["is_controversy"],
                "agreement_score": aggregation_result.get("agreement_score", 0.0),
                "decision_rationale": self._explain_decision(decision, aggregation_result)
            }

            return decision, details

        except Exception as e:
            self.logger.error(f"Error processing expert votes: {str(e)}", exc_info=True)
            return FeedbackDecision.ESCALATE_REVIEW, {"error": str(e)}

    async def _weight_votes_by_authority(
        self,
        votes: List[ExpertVote]
    ) -> List[Tuple[ExpertVote, float]]:
        """
        Weight each vote by expert authority score.

        Authority scores based on:
        - Track record of previous correct votes
        - Credentials (expert type)
        - Temporal performance
        """
        weighted_votes = []

        for vote in votes:
            try:
                # Get expert authority score
                result = await self.db_session.execute(
                    select(User).where(User.id == vote.expert_id)
                )
                expert = result.scalar()

                if expert:
                    authority = expert.authority_score if hasattr(expert, 'authority_score') else 0.5
                else:
                    authority = 0.5  # Default for unknown experts

                weighted_votes.append((vote, authority))

            except Exception as e:
                self.logger.warning(f"Error getting authority for expert {vote.expert_id}: {str(e)}")
                weighted_votes.append((vote, 0.5))  # Default weight

        return weighted_votes

    async def _aggregate_votes(
        self,
        weighted_votes: List[Tuple[ExpertVote, float]],
        entity_type: EntityTypeEnum
    ) -> Dict[str, Any]:
        """
        Aggregate weighted votes into consensus.

        Uses uncertainty-preserving aggregation:
        - Calculates mean and variance
        - Detects disagreement via entropy
        - Returns confidence bounds
        """
        if not weighted_votes:
            return {"consensus": 0.0, "confidence": 0.0, "agreement_score": 0.0}

        # Extract values and weights
        values = [vote.vote_value for vote, _ in weighted_votes]
        weights = [authority for _, authority in weighted_votes]

        # Calculate weighted mean
        weighted_mean = sum(v * w for v, w in zip(values, weights)) / sum(weights)

        # Calculate variance (disagreement)
        variance = sum(
            w * (v - weighted_mean) ** 2
            for v, w in zip(values, weights)
        ) / sum(weights)

        # Agreement score (1 - normalized_variance)
        max_variance = 1.0  # Max possible variance for -1 to 1 range
        agreement_score = max(0.0, 1.0 - (variance / max_variance))

        # Entropy-based disagreement
        vote_counts = Counter(values)
        total_votes = len(values)
        disagreement_entropy = -sum(
            (count / total_votes) * (count / total_votes) ** 2
            for count in vote_counts.values()
        )

        return {
            "consensus": float(weighted_mean),
            "confidence": float(agreement_score),
            "agreement_score": float(agreement_score),
            "variance": float(variance),
            "disagreement_entropy": float(disagreement_entropy),
            "vote_count": len(weighted_votes),
            "expert_count": len(set(vote.expert_id for vote, _ in weighted_votes))
        }

    def _make_decision(
        self,
        aggregation_result: Dict[str, Any],
        entity_type: EntityTypeEnum
    ) -> FeedbackDecision:
        """
        Make decision based on aggregation result.

        Decision rules by entity type (with dynamic quorum):
        - High consensus (>0.8 agreement) → APPROVE
        - Low consensus (<0.3 agreement) → FLAG_CONTROVERSY
        - Moderate consensus → REQUEST_REVISION
        """
        agreement = aggregation_result.get("agreement_score", 0.0)
        consensus = aggregation_result.get("consensus", 0.0)

        # Dynamic thresholds by entity type
        if entity_type == EntityTypeEnum.NORMA:
            approve_threshold = 0.80
            controversy_threshold = 0.30
        elif entity_type == EntityTypeEnum.SENTENZA:
            approve_threshold = 0.85
            controversy_threshold = 0.25
        else:  # DOTTRINA, CONTRIBUTION
            approve_threshold = 0.75
            controversy_threshold = 0.35

        if agreement >= approve_threshold:
            return FeedbackDecision.APPROVE
        elif agreement < controversy_threshold:
            return FeedbackDecision.FLAG_CONTROVERSY
        else:
            return FeedbackDecision.REQUEST_REVISION

    async def _detect_controversies(
        self,
        entity_id: str,
        weighted_votes: List[Tuple[ExpertVote, float]],
        aggregation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect if there's controversy around entity.

        Controversy detected when:
        - Agreement score < 0.4
        - High disagreement entropy (>0.5)
        - Polarized votes (some +1, some -1)
        """
        agreement = aggregation_result.get("agreement_score", 0.0)
        entropy = aggregation_result.get("disagreement_entropy", 0.0)

        # Check for polarization
        vote_values = [vote.vote_value for vote, _ in weighted_votes]
        has_positive = any(v > 0 for v in vote_values)
        has_negative = any(v < 0 for v in vote_values)
        is_polarized = has_positive and has_negative

        is_controversy = (
            agreement < 0.4 or
            entropy > 0.5 or
            is_polarized
        )

        return {
            "is_controversy": is_controversy,
            "agreement_score": agreement,
            "disagreement_entropy": entropy,
            "is_polarized": is_polarized,
            "conflicting_opinions": [
                vote.explanation for vote, _ in weighted_votes
                if vote.explanation
            ] if is_controversy else []
        }

    def _explain_decision(
        self,
        decision: FeedbackDecision,
        aggregation_result: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of decision."""
        agreement = aggregation_result.get("agreement_score", 0.0)

        explanations = {
            FeedbackDecision.APPROVE: (
                f"Experts agree (agreement: {agreement:.1%}). "
                f"Entity approved with high confidence."
            ),
            FeedbackDecision.REJECT: (
                f"Experts disagree (agreement: {agreement:.1%}). "
                f"Entity rejected."
            ),
            FeedbackDecision.REQUEST_REVISION: (
                f"Mixed feedback (agreement: {agreement:.1%}). "
                f"Entity needs revision based on expert suggestions."
            ),
            FeedbackDecision.FLAG_CONTROVERSY: (
                f"Significant disagreement (agreement: {agreement:.1%}). "
                f"Controversy flagged for further review."
            ),
            FeedbackDecision.ESCALATE_REVIEW: (
                "Insufficient data or processing error. "
                "Escalating to expert review queue."
            )
        }

        return explanations.get(decision, "Decision made based on aggregated feedback")

    async def _log_feedback_result(
        self,
        entity_id: str,
        entity_type: EntityTypeEnum,
        votes: List[ExpertVote],
        aggregation_result: Dict[str, Any],
        decision: FeedbackDecision,
        controversy_info: Dict[str, Any]
    ) -> None:
        """Log feedback processing result to database."""
        try:
            feedback_log = {
                "entity_id": entity_id,
                "entity_type": entity_type.value,
                "votes_count": len(votes),
                "aggregation_result": aggregation_result,
                "decision": decision.value,
                "controversy_detected": controversy_info["is_controversy"],
                "timestamp": datetime.utcnow().isoformat()
            }

            self.logger.info(f"Feedback processed: {feedback_log}")

            # In production: save to feedback_log table

        except Exception as e:
            self.logger.error(f"Error logging feedback: {str(e)}")

    async def distribute_feedback(
        self,
        feedback_targets: List[str],
        entity_id: str,
        feedback_result: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Distribute feedback to target systems.

        Targets:
        - ner_pipeline: Feedback on entity extraction
        - intent_classifier: Feedback on intent classification
        - kg_system: Update KG with correction
        - expert_review_queue: Escalate for expert review

        Args:
            feedback_targets: Systems to send feedback to
            entity_id: Entity being corrected
            feedback_result: Feedback data

        Returns:
            Status of feedback distribution
        """
        results = {}

        for target in feedback_targets:
            try:
                if target == "ner_pipeline":
                    await self._send_ner_feedback(entity_id, feedback_result)
                    results["ner_pipeline"] = True

                elif target == "intent_classifier":
                    await self._send_intent_feedback(entity_id, feedback_result)
                    results["intent_classifier"] = True

                elif target == "kg_system":
                    await self._send_kg_feedback(entity_id, feedback_result)
                    results["kg_system"] = True

                elif target == "expert_review_queue":
                    await self._escalate_to_expert_review(entity_id, feedback_result)
                    results["expert_review_queue"] = True

            except Exception as e:
                self.logger.error(f"Error distributing feedback to {target}: {str(e)}")
                results[target] = False

        return results

    async def _send_ner_feedback(
        self,
        entity_id: str,
        feedback_result: Dict[str, Any]
    ) -> None:
        """Send feedback to NER pipeline for model improvement."""
        self.logger.info(f"Sending NER feedback for entity {entity_id}")
        # In production: queue to NER feedback system

    async def _send_intent_feedback(
        self,
        entity_id: str,
        feedback_result: Dict[str, Any]
    ) -> None:
        """Send feedback to intent classifier."""
        self.logger.info(f"Sending intent feedback for entity {entity_id}")
        # In production: queue to intent classifier feedback

    async def _send_kg_feedback(
        self,
        entity_id: str,
        feedback_result: Dict[str, Any]
    ) -> None:
        """Send feedback to KG system for updates."""
        self.logger.info(f"Sending KG feedback for entity {entity_id}")
        # In production: update entity in Neo4j

    async def _escalate_to_expert_review(
        self,
        entity_id: str,
        feedback_result: Dict[str, Any]
    ) -> None:
        """Escalate to expert review queue."""
        self.logger.info(f"Escalating entity {entity_id} to expert review")
        # In production: create task in expert_review_queue

    # ==========================================
    # Batch Processing
    # ==========================================

    async def process_batch_feedback(
        self,
        feedback_batch: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process batch of feedback entries.

        Efficient processing of multiple votes/corrections.

        Args:
            feedback_batch: List of feedback entries

        Returns:
            Batch processing statistics
        """
        stats = {
            "total_processed": 0,
            "approved": 0,
            "rejected": 0,
            "controversies_detected": 0,
            "escalated_to_expert": 0,
            "errors": 0
        }

        tasks = []
        for feedback_item in feedback_batch:
            try:
                # Parse feedback item
                entity_id = feedback_item.get("entity_id")
                entity_type = EntityTypeEnum(feedback_item.get("entity_type"))
                votes = [
                    ExpertVote(
                        expert_id=v["expert_id"],
                        entity_id=entity_id,
                        feedback_type=FeedbackType(v["feedback_type"]),
                        vote_value=v["vote_value"],
                        confidence=v.get("confidence", 0.8)
                    )
                    for v in feedback_item.get("votes", [])
                ]

                # Process asynchronously
                task = self.process_expert_votes(entity_id, entity_type, votes)
                tasks.append((feedback_item, task))

            except Exception as e:
                self.logger.error(f"Error parsing feedback: {str(e)}")
                stats["errors"] += 1

        # Await all tasks
        if tasks:
            results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )

            for (feedback_item, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    stats["errors"] += 1
                else:
                    decision, details = result
                    stats["total_processed"] += 1

                    if decision == FeedbackDecision.APPROVE:
                        stats["approved"] += 1
                    elif decision == FeedbackDecision.REJECT:
                        stats["rejected"] += 1
                    elif decision == FeedbackDecision.FLAG_CONTROVERSY:
                        stats["controversies_detected"] += 1
                    elif decision == FeedbackDecision.ESCALATE_REVIEW:
                        stats["escalated_to_expert"] += 1

        return stats


# ==========================================
# Factory Functions
# ==========================================

async def create_feedback_processor(
    db_session: AsyncSession
) -> RLCFFeedbackProcessor:
    """
    Factory function to create feedback processor.

    Args:
        db_session: Database session

    Returns:
        Initialized RLCFFeedbackProcessor instance
    """
    return RLCFFeedbackProcessor(db_session=db_session)
