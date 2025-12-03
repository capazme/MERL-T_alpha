"""
RLCF Service Interfaces
=======================

Abstract interfaces for learning layer components.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class FeedbackLevel(Enum):
    """Level at which feedback applies."""
    RETRIEVAL = "retrieval"      # Source relevance
    REASONING = "reasoning"      # Expert correctness
    SYNTHESIS = "synthesis"      # Final answer quality


class FeedbackType(Enum):
    """Type of feedback."""
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    CORRECTION = "correction"
    ELABORATION = "elaboration"


@dataclass
class Feedback:
    """Feedback from an expert user."""
    id: str
    query_id: str
    user_id: str
    level: FeedbackLevel
    feedback_type: FeedbackType
    target_id: str  # What is being evaluated (source_id, expert_type, answer_id)
    value: float  # -1 to 1
    comment: Optional[str] = None
    correction_text: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserAuthority:
    """Authority score for a user."""
    user_id: str
    overall_authority: float  # 0 to 1
    level_authority: Dict[str, float]  # Per FeedbackLevel
    domain_authority: Dict[str, float]  # Per legal domain
    feedback_count: int
    last_updated: datetime


class IAuthorityCalculator(ABC):
    """
    Interface for authority calculation.

    Computes user authority based on:
    - Background credentials (B_u)
    - Track record (T_u)
    - Peer recognition (P_u)

    A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
    """

    @abstractmethod
    async def get_authority(
        self,
        user_id: str,
        level: Optional[FeedbackLevel] = None,
        domain: Optional[str] = None
    ) -> float:
        """
        Get authority score for a user.

        Args:
            user_id: User identifier
            level: Specific level (retrieval/reasoning/synthesis)
            domain: Specific legal domain

        Returns:
            Authority score (0 to 1)
        """
        pass

    @abstractmethod
    async def update_authority(
        self,
        user_id: str,
        feedback_quality: float,
        peer_agreement: float
    ) -> UserAuthority:
        """
        Update user authority based on feedback quality.

        Args:
            user_id: User identifier
            feedback_quality: How good was their feedback (0-1)
            peer_agreement: Agreement with other experts (0-1)

        Returns:
            Updated authority record
        """
        pass


class IRLCFService(ABC):
    """
    Interface for RLCF (Reinforcement Learning from Community Feedback) service.

    Handles:
    1. Collecting feedback from expert users
    2. Aggregating feedback weighted by authority
    3. Propagating learning signals to model parameters
    """

    @abstractmethod
    async def submit_feedback(self, feedback: Feedback) -> bool:
        """
        Submit feedback from a user.

        Args:
            feedback: Feedback object

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def get_aggregated_feedback(
        self,
        target_id: str,
        level: FeedbackLevel
    ) -> Dict[str, Any]:
        """
        Get aggregated feedback for a target.

        Args:
            target_id: What to get feedback for
            level: Feedback level

        Returns:
            Aggregated score with confidence and breakdown
        """
        pass

    @abstractmethod
    async def compute_learning_signal(
        self,
        query_id: str
    ) -> Dict[str, float]:
        """
        Compute learning signals for a query.

        Aggregates all feedback and computes gradients for:
        - theta_traverse (graph traversal weights)
        - theta_gating (expert gating weights)
        - theta_rerank (re-ranking weights)

        Args:
            query_id: Query to compute signals for

        Returns:
            Dict of parameter -> gradient
        """
        pass

    @abstractmethod
    async def apply_learning(
        self,
        learning_signals: Dict[str, float],
        learning_rate: float = 0.01
    ) -> bool:
        """
        Apply learning signals to model parameters.

        Args:
            learning_signals: Gradients for each parameter
            learning_rate: How much to update

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        pass
