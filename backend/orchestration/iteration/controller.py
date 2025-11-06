"""
Iteration Controller for multi-turn refinement of legal answers.

This module provides the IterationController class which manages:
- Iteration state across refinement cycles
- Stopping criteria evaluation
- User and RLCF feedback integration
- Refinement instruction generation for next iteration
"""

import logging
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .models import (
    IterationContext,
    IterationMetrics,
    UserFeedback,
    RLCFQualityScore,
    StoppingCriteria
)


logger = logging.getLogger(__name__)


class IterationController:
    """
    Manages multi-turn refinement of legal answers.

    The Iteration Controller coordinates the refinement process by:
    1. Tracking iteration state across cycles
    2. Evaluating stopping criteria (6 different conditions)
    3. Incorporating user feedback into next iteration
    4. Coordinating RLCF quality evaluation
    5. Generating refinement instructions for Router/Experts
    6. Detecting convergence and quality plateaus

    Stopping Criteria (evaluated in priority order):
    1. MAX_ITERATIONS: Hard limit reached
    2. HIGH_CONFIDENCE: Confidence + consensus thresholds met
    3. RLCF_APPROVED: RLCF quality score ≥ threshold
    4. USER_SATISFIED: User rating ≥ threshold
    5. NO_IMPROVEMENT: Recent iterations show no significant improvement
    6. CONVERGED: Metrics stable across convergence window
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Iteration Controller.

        Args:
            config: Configuration dict with stopping criteria thresholds
        """
        self.config = config or {}
        self.logger = logging.getLogger("iteration_controller")

        # Load stopping criteria from config
        self.stopping_criteria = StoppingCriteria(
            confidence_threshold=self.config.get("confidence_threshold", 0.85),
            consensus_threshold=self.config.get("consensus_threshold", 0.80),
            quality_threshold=self.config.get("quality_threshold", 0.80),
            user_rating_threshold=self.config.get("user_rating_threshold", 4.0),
            min_improvement_delta=self.config.get("min_improvement_delta", 0.05),
            convergence_window=self.config.get("convergence_window", 2)
        )

        self.logger.info(
            f"IterationController initialized with stopping criteria: "
            f"confidence≥{self.stopping_criteria.confidence_threshold}, "
            f"consensus≥{self.stopping_criteria.consensus_threshold}, "
            f"quality≥{self.stopping_criteria.quality_threshold}"
        )

        # RLCF processor (injected via DI if needed)
        self.rlcf_processor = None

    # ========================================================================
    # Session Management
    # ========================================================================

    async def start_iteration_session(
        self,
        query: str,
        query_context: Dict[str, Any],
        max_iterations: int = 3,
        trace_id: Optional[str] = None
    ) -> IterationContext:
        """
        Start new iteration session.

        Args:
            query: Original legal query
            query_context: QueryContext from preprocessing
            max_iterations: Maximum refinement cycles (default: 3)
            trace_id: Optional trace ID for provenance

        Returns:
            Initialized IterationContext
        """
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        if trace_id is None:
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"

        context = IterationContext(
            session_id=session_id,
            trace_id=trace_id,
            original_query=query,
            query_context=query_context,
            max_iterations=max_iterations,
            status="PENDING"
        )

        self.logger.info(
            f"Started iteration session {session_id} for query: '{query[:50]}...' "
            f"(max_iterations={max_iterations})"
        )

        return context

    async def process_iteration(
        self,
        context: IterationContext,
        provisional_answer: Dict[str, Any],
        execution_plan: Dict[str, Any],
        execution_time_ms: float
    ) -> IterationContext:
        """
        Process single iteration result.

        Updates the context with:
        - New iteration history entry
        - Metrics from provisional answer
        - Current best answer

        Args:
            context: Current iteration context
            provisional_answer: Answer from Synthesizer (as dict)
            execution_plan: ExecutionPlan used (as dict)
            execution_time_ms: Total execution time

        Returns:
            Updated IterationContext
        """
        self.logger.info(
            f"Processing iteration {context.current_iteration} for session {context.session_id}"
        )

        # Extract metrics from provisional answer
        metrics = IterationMetrics(
            iteration_number=context.current_iteration,
            confidence=provisional_answer.get("confidence", 0.5),
            consensus_level=provisional_answer.get("consensus_level", 0.5),
            rlcf_quality_score=None,  # Will be filled by RLCF evaluation
            user_rating=None,  # Will be filled by user feedback
            convergence_indicators={},
            execution_time_ms=execution_time_ms
        )

        # Add to history
        context.add_history(
            execution_plan=execution_plan,
            provisional_answer=provisional_answer,
            metrics=metrics
        )

        # Update status
        context.status = "IN_PROGRESS"

        self.logger.info(
            f"Iteration {context.current_iteration} processed: "
            f"confidence={metrics.confidence:.2f}, "
            f"consensus={metrics.consensus_level:.2f}, "
            f"time={execution_time_ms:.0f}ms"
        )

        return context

    # ========================================================================
    # Stopping Criteria Evaluation
    # ========================================================================

    async def should_continue_iteration(
        self,
        context: IterationContext
    ) -> Tuple[bool, str]:
        """
        Evaluate if iteration should continue.

        Checks all 6 stopping criteria in priority order.

        Args:
            context: Current iteration context

        Returns:
            (should_continue: bool, reason: str)
        """
        should_stop, reason = self._evaluate_stopping_criteria(context)

        if should_stop:
            self.logger.info(
                f"Session {context.session_id}: Stopping iteration. Reason: {reason}"
            )
            return (False, reason)
        else:
            self.logger.info(
                f"Session {context.session_id}: Continuing iteration (current: {context.current_iteration}/{context.max_iterations})"
            )
            return (True, reason)

    def _evaluate_stopping_criteria(
        self,
        context: IterationContext
    ) -> Tuple[bool, str]:
        """
        Comprehensive stopping criteria evaluation.

        Stop conditions (priority order):
        1. MAX_ITERATIONS: Hard limit reached
        2. HIGH_CONFIDENCE: Confidence ≥ threshold AND consensus ≥ threshold
        3. RLCF_APPROVED: RLCF quality score ≥ threshold
        4. USER_SATISFIED: User rating ≥ threshold
        5. NO_IMPROVEMENT: Last N iterations show no significant improvement
        6. CONVERGED: Metrics stable across convergence window

        Args:
            context: Iteration context

        Returns:
            (should_stop: bool, reason: str)
        """
        # 1. Check max iterations
        if context.current_iteration >= context.max_iterations:
            return (True, "MAX_ITERATIONS_REACHED")

        # Need at least one iteration to evaluate other criteria
        if not context.current_metrics:
            return (False, "FIRST_ITERATION_PENDING")

        # 2. Check high confidence + consensus
        if (context.current_metrics.confidence >= self.stopping_criteria.confidence_threshold
            and context.current_metrics.consensus_level >= self.stopping_criteria.consensus_threshold):
            return (True, "HIGH_CONFIDENCE_AND_CONSENSUS")

        # 3. Check RLCF approval
        if context.current_metrics.rlcf_quality_score:
            if context.current_metrics.rlcf_quality_score >= self.stopping_criteria.quality_threshold:
                return (True, "RLCF_QUALITY_APPROVED")

        # 4. Check user satisfaction
        if context.current_metrics.user_rating:
            if context.current_metrics.user_rating >= self.stopping_criteria.user_rating_threshold:
                return (True, "USER_SATISFIED")

        # 5. Check improvement trend (need at least 2 iterations)
        if len(context.history) >= 2:
            improvement = self._calculate_improvement(context)
            if improvement < self.stopping_criteria.min_improvement_delta:
                self.logger.info(
                    f"Improvement delta: {improvement:.3f} < threshold {self.stopping_criteria.min_improvement_delta}"
                )
                return (True, "NO_SIGNIFICANT_IMPROVEMENT")

        # 6. Check convergence (stability over window)
        if len(context.history) >= self.stopping_criteria.convergence_window:
            if self._is_converged(context):
                return (True, "METRICS_CONVERGED")

        # Continue iterating
        return (False, "CONTINUE_REFINEMENT")

    def _calculate_improvement(self, context: IterationContext) -> float:
        """
        Calculate improvement from previous iteration.

        Improvement metric:
        Δ = (current_confidence - previous_confidence) +
            (current_consensus - previous_consensus) / 2

        Args:
            context: Iteration context

        Returns:
            Improvement delta (can be negative)
        """
        if len(context.history) < 2:
            return 1.0  # First iteration, assume high improvement

        current = context.history[-1].metrics
        previous = context.history[-2].metrics

        confidence_delta = current.confidence - previous.confidence
        consensus_delta = current.consensus_level - previous.consensus_level

        improvement = (confidence_delta + consensus_delta) / 2.0

        self.logger.debug(
            f"Improvement calculation: "
            f"Δconfidence={confidence_delta:.3f}, "
            f"Δconsensus={consensus_delta:.3f}, "
            f"Δtotal={improvement:.3f}"
        )

        return improvement

    def _is_converged(self, context: IterationContext) -> bool:
        """
        Check if metrics have converged (stable).

        Convergence: confidence and consensus vary by < 0.05
        across convergence_window iterations.

        Args:
            context: Iteration context

        Returns:
            True if converged (metrics stable)
        """
        window = self.stopping_criteria.convergence_window
        recent_history = context.history[-window:]

        confidences = [h.metrics.confidence for h in recent_history]
        consensuses = [h.metrics.consensus_level for h in recent_history]

        confidence_variance = max(confidences) - min(confidences)
        consensus_variance = max(consensuses) - min(consensuses)

        converged = (confidence_variance < 0.05 and consensus_variance < 0.05)

        if converged:
            self.logger.info(
                f"Metrics converged: "
                f"confidence_variance={confidence_variance:.3f}, "
                f"consensus_variance={consensus_variance:.3f}"
            )

        return converged

    # ========================================================================
    # Feedback Integration
    # ========================================================================

    async def incorporate_user_feedback(
        self,
        context: IterationContext,
        feedback: UserFeedback
    ) -> IterationContext:
        """
        Incorporate user feedback for next iteration.

        Adds feedback to context and updates current metrics with user rating.

        Args:
            context: Current iteration context
            feedback: User feedback on latest answer

        Returns:
            Updated context with feedback incorporated
        """
        self.logger.info(
            f"Session {context.session_id}: Incorporating user feedback "
            f"(rating={feedback.quality_rating:.1f}, "
            f"missing_info={len(feedback.missing_information)})"
        )

        # Add feedback to context
        context.add_user_feedback(feedback)

        # Update current metrics with user rating
        if context.current_metrics:
            context.current_metrics.user_rating = feedback.quality_rating

        self.logger.debug(
            f"User feedback details: "
            f"missing={feedback.missing_information}, "
            f"incorrect_claims={len(feedback.incorrect_claims)}, "
            f"suggestions='{feedback.suggested_improvements[:100]}'"
        )

        return context

    async def evaluate_answer_quality_rlcf(
        self,
        context: IterationContext,
        answer: Dict[str, Any]
    ) -> RLCFQualityScore:
        """
        Evaluate answer quality using RLCF.

        Submits answer to RLCF community for expert evaluation.
        Uses existing RLCFFeedbackProcessor from Phase 1.

        Args:
            context: Iteration context
            answer: ProvisionalAnswer dict to evaluate

        Returns:
            RLCFQualityScore with aggregated expert votes

        Note:
            This is a placeholder. Full RLCF integration requires:
            1. Creating RLCF task for answer evaluation
            2. Collecting expert votes asynchronously
            3. Aggregating votes with authority weighting
            4. Detecting controversies
        """
        self.logger.info(
            f"Session {context.session_id}: Evaluating answer quality with RLCF"
        )

        # Placeholder implementation
        # In production, this would:
        # 1. Submit answer to RLCF system
        # 2. Wait for expert votes (or return immediately and poll later)
        # 3. Aggregate votes with RLCFFeedbackProcessor
        # 4. Return RLCFQualityScore

        # For now, create mock RLCF score
        mock_score = RLCFQualityScore(
            answer_id=answer.get("trace_id", "unknown"),
            expert_votes=[],
            aggregated_score=0.80,  # Mock score
            consensus_level=0.85,
            controversy_detected=False,
            controversy_details={}
        )

        self.logger.warning(
            "RLCF evaluation is using mock data. "
            "Full RLCF integration requires RLCFFeedbackProcessor setup."
        )

        # Add to context
        context.add_rlcf_evaluation(mock_score)

        return mock_score

    # ========================================================================
    # Refinement Instructions Generation
    # ========================================================================

    async def generate_refinement_instructions(
        self,
        context: IterationContext
    ) -> Dict[str, Any]:
        """
        Generate refinement instructions for next iteration.

        Based on:
        - User feedback (what's missing/wrong)
        - RLCF evaluation (expert concerns)
        - Previous iteration limitations

        These instructions are passed to:
        - Router: to decide which agents to activate
        - Experts: to address specific concerns

        Args:
            context: Iteration context with feedback

        Returns:
            Refinement instructions dict
        """
        self.logger.info(
            f"Session {context.session_id}: Generating refinement instructions "
            f"for iteration {context.current_iteration + 1}"
        )

        refinement_context = {
            "iteration_number": context.current_iteration + 1,
            "previous_answer_summary": self._summarize_previous_answer(context),
            "user_feedback_summary": self._summarize_user_feedback(context),
            "rlcf_concerns": self._extract_rlcf_concerns(context),
            "expert_limitations": self._collect_expert_limitations(context),
            "missing_information": self._identify_missing_info(context),
            "refinement_instructions": self._generate_instructions(context)
        }

        self.logger.debug(
            f"Refinement instructions: {refinement_context['refinement_instructions'][:200]}"
        )

        return refinement_context

    def _summarize_previous_answer(self, context: IterationContext) -> str:
        """Summarize previous answer (first 500 chars)."""
        if not context.current_answer:
            return "No previous answer."

        final_answer = context.current_answer.get("final_answer", "")
        return final_answer[:500] + ("..." if len(final_answer) > 500 else "")

    def _summarize_user_feedback(self, context: IterationContext) -> str:
        """Summarize all user feedback into instructions."""
        if not context.all_feedback:
            return "No user feedback yet."

        latest_feedback = context.all_feedback[-1]

        summary_parts = []

        if latest_feedback.missing_information:
            summary_parts.append(
                f"Informazioni mancanti: {', '.join(latest_feedback.missing_information)}"
            )

        if latest_feedback.incorrect_claims:
            summary_parts.append(
                f"Claim potenzialmente errati: {len(latest_feedback.incorrect_claims)} identificati"
            )

        if latest_feedback.suggested_improvements:
            summary_parts.append(
                f"Suggerimento utente: {latest_feedback.suggested_improvements}"
            )

        if not summary_parts:
            return f"Rating utente: {latest_feedback.quality_rating:.1f}/5.0 (nessun feedback specifico)"

        return "; ".join(summary_parts)

    def _extract_rlcf_concerns(self, context: IterationContext) -> str:
        """Extract concerns from RLCF evaluation."""
        if not context.all_rlcf_scores:
            return "No RLCF evaluation yet."

        latest_rlcf = context.all_rlcf_scores[-1]

        if latest_rlcf.controversy_detected:
            return (
                f"RLCF ha rilevato controversia: "
                f"{latest_rlcf.controversy_details.get('description', 'Dettagli non disponibili')}"
            )
        elif latest_rlcf.aggregated_score < 0.70:
            return (
                f"RLCF score basso ({latest_rlcf.aggregated_score:.2f}): "
                f"Gli esperti hanno segnalato problemi di qualità."
            )
        else:
            return f"RLCF score: {latest_rlcf.aggregated_score:.2f} (accettabile)"

    def _collect_expert_limitations(self, context: IterationContext) -> List[str]:
        """Collect limitations from all experts in previous iteration."""
        if not context.history:
            return []

        latest_iteration = context.history[-1]
        provisional_answer = latest_iteration.provisional_answer

        # Extract limitations from provenance
        limitations = []
        provenance = provisional_answer.get("provenance", [])

        for claim in provenance:
            expert_support = claim.get("expert_support", [])
            for support in expert_support:
                expert_type = support.get("expert", "")
                reasoning = support.get("reasoning", "")

                if "limita" in reasoning.lower() or "ignora" in reasoning.lower():
                    limitations.append(f"{expert_type}: {reasoning}")

        return limitations[:5]  # Top 5 limitations

    def _identify_missing_info(self, context: IterationContext) -> List[str]:
        """Identify missing information from feedback."""
        missing_info = []

        # From user feedback
        for feedback in context.all_feedback:
            missing_info.extend(feedback.missing_information)

        # Deduplicate
        return list(set(missing_info))

    def _generate_instructions(self, context: IterationContext) -> str:
        """Generate structured refinement instructions."""
        instructions_parts = []

        # User feedback
        if context.all_feedback:
            latest_feedback = context.all_feedback[-1]
            if latest_feedback.missing_information:
                instructions_parts.append(
                    f"RECUPERARE: {', '.join(latest_feedback.missing_information)}"
                )

            if latest_feedback.suggested_improvements:
                instructions_parts.append(
                    f"CONSIDERARE: {latest_feedback.suggested_improvements}"
                )

        # RLCF concerns
        if context.all_rlcf_scores:
            latest_rlcf = context.all_rlcf_scores[-1]
            if latest_rlcf.aggregated_score < 0.75:
                instructions_parts.append(
                    "MIGLIORARE QUALITÀ: RLCF score sotto soglia, verificare completezza e correttezza"
                )

        # Expert limitations
        limitations = self._collect_expert_limitations(context)
        if limitations:
            instructions_parts.append(
                f"SUPERARE LIMITAZIONI: {limitations[0]}"  # Top limitation
            )

        if not instructions_parts:
            return "Nessuna istruzione specifica. Continuare con raffinamento generale."

        return " | ".join(instructions_parts)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_session_summary(self, context: IterationContext) -> Dict[str, Any]:
        """
        Get summary of iteration session.

        Args:
            context: Iteration context

        Returns:
            Summary dict with key metrics and status
        """
        return {
            "session_id": context.session_id,
            "trace_id": context.trace_id,
            "query": context.original_query,
            "current_iteration": context.current_iteration,
            "max_iterations": context.max_iterations,
            "status": context.status,
            "stop_reason": context.stop_reason,
            "current_confidence": context.current_metrics.confidence if context.current_metrics else None,
            "current_consensus": context.current_metrics.consensus_level if context.current_metrics else None,
            "user_feedbacks_count": len(context.all_feedback),
            "rlcf_evaluations_count": len(context.all_rlcf_scores),
            "total_iterations": len(context.history),
            "created_at": context.created_at,
            "updated_at": context.updated_at
        }
