"""
Expert Service Interfaces
=========================

Abstract interfaces for reasoning layer components.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ExpertQuery:
    """Query context for an expert."""
    query_text: str
    query_embedding: List[float]
    context_nodes: List[str] = field(default_factory=list)
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpertOpinionResult:
    """Result from an expert analysis."""
    expert_type: str
    conclusion: str
    confidence: float
    legal_basis: List[Dict[str, Any]]
    reasoning_steps: List[str]
    sources_used: List[str]
    limitations: List[str]
    execution_time_ms: float
    trace_id: Optional[str] = None


class IExpert(ABC):
    """
    Interface for a legal reasoning expert.

    Each expert implements a specific interpretive methodology:
    - Literal: Positivismo Giuridico (text-based)
    - Systemic: Teleologia Giuridica (purpose-based)
    - Principles: Costituzionalismo (constitutional balancing)
    - Precedent: Empirismo Giuridico (case law analysis)
    """

    @property
    @abstractmethod
    def expert_type(self) -> str:
        """Expert type identifier."""
        pass

    @abstractmethod
    async def analyze(self, query: ExpertQuery) -> ExpertOpinionResult:
        """
        Analyze a legal query and produce an opinion.

        The expert:
        1. Uses its tools to retrieve relevant sources
        2. Applies its interpretive methodology
        3. Produces a structured opinion

        Args:
            query: Query context with text, embedding, entities

        Returns:
            Structured opinion with conclusion, basis, confidence
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if expert service is healthy."""
        pass


class IExpertGating(ABC):
    """
    Interface for expert gating network.

    Determines how much weight to give each expert
    based on query characteristics.
    """

    @abstractmethod
    def compute_weights(
        self,
        query_embedding: List[float],
        query_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Compute expert weights for a query.

        Args:
            query_embedding: Query vector
            query_metadata: Optional query characteristics

        Returns:
            Dict mapping expert_type to weight (sums to 1.0)
        """
        pass

    @abstractmethod
    def update_from_feedback(
        self,
        query_embedding: List[float],
        expert_performance: Dict[str, float],
        feedback_authority: float
    ) -> None:
        """
        Update gating weights from RLCF feedback.

        Args:
            query_embedding: Query that was evaluated
            expert_performance: Score for each expert (0-1)
            feedback_authority: Authority of feedback source
        """
        pass


@dataclass
class SynthesisResult:
    """Result from expert synthesis."""
    final_answer: str
    confidence: float
    consensus_level: float  # 0 = full disagreement, 1 = full agreement
    expert_contributions: Dict[str, float]  # Weight given to each expert
    key_points: List[str]
    dissenting_views: List[Dict[str, str]]  # {expert, view}
    trace_id: Optional[str] = None


class ISynthesizer(ABC):
    """
    Interface for expert opinion synthesizer.

    Combines multiple expert opinions into a coherent answer,
    handling both convergent and divergent scenarios.
    """

    @abstractmethod
    async def synthesize(
        self,
        query: ExpertQuery,
        expert_opinions: List[ExpertOpinionResult],
        expert_weights: Dict[str, float]
    ) -> SynthesisResult:
        """
        Synthesize expert opinions into final answer.

        Args:
            query: Original query
            expert_opinions: Opinions from each expert
            expert_weights: Gating weights for each expert

        Returns:
            Synthesized answer with confidence and provenance
        """
        pass
