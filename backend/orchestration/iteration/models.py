"""
Data models for Iteration Controller.

This module defines all Pydantic models for:
- User feedback
- RLCF quality evaluation
- Iteration metrics and history
- Iteration context (complete state)
- Stopping criteria configuration
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# Feedback Models
# ============================================================================

class UserFeedback(BaseModel):
    """
    User feedback on a ProvisionalAnswer.

    Captures user satisfaction and specific issues to address
    in next iteration.
    """
    feedback_id: str
    iteration_number: int

    # Quality rating
    quality_rating: float = Field(ge=1.0, le=5.0, description="1-5 star rating")

    # Specific feedback
    missing_information: List[str] = Field(
        default_factory=list,
        description="What information is missing from the answer"
    )
    incorrect_claims: List[str] = Field(
        default_factory=list,
        description="claim_ids of incorrect or questionable claims"
    )
    suggested_improvements: str = Field(
        default="",
        description="Free-text suggestions from user"
    )

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_id": "fb-12345",
                "iteration_number": 1,
                "quality_rating": 3.5,
                "missing_information": ["Giurisprudenza recente", "Eccezioni"],
                "incorrect_claims": [],
                "suggested_improvements": "Vorrei sapere se ci sono eccezioni recenti alla nullità",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class RLCFQualityScore(BaseModel):
    """
    RLCF community evaluation of answer quality.

    Uses existing RLCFFeedbackProcessor to aggregate expert votes
    on answer quality, correctness, and completeness.
    """
    answer_id: str

    # Expert votes
    expert_votes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Raw expert votes from RLCF community"
    )

    # Aggregated metrics
    aggregated_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Authority-weighted quality score (0.0-1.0)"
    )
    consensus_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Expert consensus level (Shannon entropy based)"
    )

    # Controversy detection
    controversy_detected: bool = Field(
        default=False,
        description="Whether RLCF detected controversy"
    )
    controversy_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details of controversy if detected"
    )

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "answer_id": "trace-12345",
                "expert_votes": [],
                "aggregated_score": 0.82,
                "consensus_level": 0.88,
                "controversy_detected": False,
                "controversy_details": {},
                "timestamp": "2025-01-15T10:35:00Z"
            }
        }


# ============================================================================
# Iteration Tracking Models
# ============================================================================

class IterationMetrics(BaseModel):
    """
    Metrics for a single iteration.

    Used to track quality, confidence, and convergence indicators
    across iterations.
    """
    iteration_number: int

    # Core metrics (from Synthesizer)
    confidence: float = Field(ge=0.0, le=1.0)
    consensus_level: float = Field(ge=0.0, le=1.0)

    # Quality metrics (optional, from RLCF)
    rlcf_quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="RLCF community quality score"
    )

    # User metrics (optional)
    user_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="User satisfaction rating (1-5)"
    )

    # Convergence indicators
    convergence_indicators: Dict[str, float] = Field(
        default_factory=dict,
        description="Various convergence metrics (improvement_delta, stability, etc.)"
    )

    # Performance
    execution_time_ms: float = Field(
        ge=0.0,
        description="Total execution time for this iteration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "iteration_number": 1,
                "confidence": 0.82,
                "consensus_level": 0.78,
                "rlcf_quality_score": 0.80,
                "user_rating": 3.5,
                "convergence_indicators": {
                    "improvement_delta": 0.15,
                    "stability_score": 0.0
                },
                "execution_time_ms": 5420.5
            }
        }


class IterationHistory(BaseModel):
    """
    Record of a single iteration.

    Captures complete execution trace: what was executed, what was
    produced, and what feedback was received.
    """
    iteration_number: int

    # Execution artifacts
    execution_plan: Dict[str, Any] = Field(
        description="ExecutionPlan used for this iteration"
    )
    provisional_answer: Dict[str, Any] = Field(
        description="ProvisionalAnswer produced by Synthesizer"
    )

    # Metrics
    metrics: IterationMetrics

    # Feedback (optional, collected after iteration completes)
    user_feedback: Optional[UserFeedback] = None
    rlcf_evaluation: Optional[RLCFQualityScore] = None

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        json_schema_extra = {
            "example": {
                "iteration_number": 1,
                "execution_plan": {"router_decision": "..."},
                "provisional_answer": {"final_answer": "..."},
                "metrics": {"confidence": 0.82, "consensus_level": 0.78},
                "user_feedback": None,
                "rlcf_evaluation": None,
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


# ============================================================================
# Iteration Context (Main State Model)
# ============================================================================

class IterationContext(BaseModel):
    """
    Complete iteration state across refinement cycles.

    This is the main state object that tracks:
    - Original query (immutable)
    - Iteration history
    - Current state and best answer
    - Accumulated feedback
    - Status and stop reason

    Managed by IterationController.
    """
    # Session identification
    session_id: str
    trace_id: str

    # Original query (immutable across iterations)
    original_query: str
    query_context: Dict[str, Any] = Field(
        description="QueryContext from preprocessing (intent, entities, etc.)"
    )

    # Iteration tracking
    current_iteration: int = Field(default=1, ge=1)
    max_iterations: int = Field(default=3, ge=1, le=10)

    # History
    history: List[IterationHistory] = Field(
        default_factory=list,
        description="Complete history of all iterations"
    )

    # Current best answer
    current_answer: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current best ProvisionalAnswer"
    )
    current_metrics: Optional[IterationMetrics] = Field(
        default=None,
        description="Metrics for current best answer"
    )

    # Accumulated feedback (across all iterations)
    all_feedback: List[UserFeedback] = Field(
        default_factory=list,
        description="All user feedback received"
    )
    all_rlcf_scores: List[RLCFQualityScore] = Field(
        default_factory=list,
        description="All RLCF evaluations"
    )

    # State machine
    status: Literal[
        "PENDING",          # Session started, no iterations yet
        "IN_PROGRESS",      # Currently executing iteration
        "CONVERGED",        # Stopped due to convergence
        "MAX_ITERATIONS",   # Stopped due to max iterations
        "USER_SATISFIED",   # Stopped due to user satisfaction
        "COMPLETED"         # Manually marked as complete
    ] = "PENDING"

    stop_reason: Optional[str] = Field(
        default=None,
        description="Detailed reason for stopping (if stopped)"
    )

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()

    def add_history(
        self,
        execution_plan: Dict[str, Any],
        provisional_answer: Dict[str, Any],
        metrics: IterationMetrics
    ):
        """
        Add iteration to history.

        Args:
            execution_plan: ExecutionPlan dict
            provisional_answer: ProvisionalAnswer dict
            metrics: IterationMetrics
        """
        history_entry = IterationHistory(
            iteration_number=self.current_iteration,
            execution_plan=execution_plan,
            provisional_answer=provisional_answer,
            metrics=metrics
        )

        self.history.append(history_entry)
        self.current_answer = provisional_answer
        self.current_metrics = metrics
        self.update_timestamp()

    def add_user_feedback(self, feedback: UserFeedback):
        """Add user feedback to context."""
        self.all_feedback.append(feedback)

        # Also add to latest history entry if exists
        if self.history:
            self.history[-1].user_feedback = feedback

        self.update_timestamp()

    def add_rlcf_evaluation(self, evaluation: RLCFQualityScore):
        """Add RLCF evaluation to context."""
        self.all_rlcf_scores.append(evaluation)

        # Also add to latest history entry if exists
        if self.history:
            self.history[-1].rlcf_evaluation = evaluation

        # Update current metrics with RLCF score
        if self.current_metrics:
            self.current_metrics.rlcf_quality_score = evaluation.aggregated_score

        self.update_timestamp()

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess-12345",
                "trace_id": "trace-12345",
                "original_query": "È valido un contratto verbale per vendita immobile?",
                "query_context": {"intent": "legal_validity", "complexity": 0.7},
                "current_iteration": 2,
                "max_iterations": 3,
                "history": [],
                "current_answer": None,
                "current_metrics": None,
                "all_feedback": [],
                "all_rlcf_scores": [],
                "status": "IN_PROGRESS",
                "stop_reason": None,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }


# ============================================================================
# Stopping Criteria Configuration
# ============================================================================

class StoppingCriteria(BaseModel):
    """
    Configuration for iteration stopping criteria.

    Defines thresholds for various stop conditions:
    - Confidence and consensus thresholds
    - RLCF quality threshold
    - User satisfaction threshold
    - Improvement tracking
    - Convergence detection
    """
    # Confidence-based stop
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Stop if confidence ≥ this value"
    )

    # Consensus-based stop
    consensus_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Stop if expert consensus ≥ this value"
    )

    # Quality-based stop (RLCF)
    quality_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Stop if RLCF quality score ≥ this value"
    )

    # User satisfaction stop
    user_rating_threshold: float = Field(
        default=4.0,
        ge=1.0,
        le=5.0,
        description="Stop if user rating ≥ this value (1-5 scale)"
    )

    # Improvement tracking
    min_improvement_delta: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Stop if improvement < this value between iterations"
    )

    # Convergence detection
    convergence_window: int = Field(
        default=2,
        ge=2,
        le=10,
        description="Number of iterations to check for stability"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "confidence_threshold": 0.85,
                "consensus_threshold": 0.80,
                "quality_threshold": 0.80,
                "user_rating_threshold": 4.0,
                "min_improvement_delta": 0.05,
                "convergence_window": 2
            }
        }
