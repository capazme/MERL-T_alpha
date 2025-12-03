"""
Reasoning Experts for Legal Analysis (v2)
==========================================

This module contains expert agents with autonomous tools.

v2 Architecture:
- ExpertWithTools: Base class for autonomous experts
- Each expert has tools for retrieval specific to their perspective
- Expert-specific traversal weights (theta_traverse)

See docs/03-architecture/03-reasoning-layer.md for v2 design.

Expert Types:
- LiteralInterpreterV2: Positivismo Giuridico (text-based)
- SystemicTeleologicalV2: Teleologia Giuridica (purpose-based)
- PrinciplesBalancerV2: Costituzionalismo (constitutional balancing)
- PrecedentAnalystV2: Empirismo Giuridico (case law analysis)
"""

# Base classes and data models (from v1, still valid)
from .base import (
    ReasoningExpert,
    ExpertContext,
    ExpertOpinion,
    LegalBasis,
    ReasoningStep,
    ConfidenceFactors
)

# Synthesizer (to be adapted for v2)
from .synthesizer import Synthesizer, ProvisionalAnswer

# v2 Expert with Tools
from .expert_with_tools import (
    ExpertWithTools,
    Tool,
    TraversalWeights,
    LiteralInterpreterV2,
    SystemicTeleologicalV2,
    PrinciplesBalancerV2,
    PrecedentAnalystV2,
)

__all__ = [
    # Base classes (v1, still valid)
    "ReasoningExpert",
    "ExpertContext",
    "ExpertOpinion",
    "LegalBasis",
    "ReasoningStep",
    "ConfidenceFactors",

    # Synthesizer
    "Synthesizer",
    "ProvisionalAnswer",

    # v2 Expert with Tools
    "ExpertWithTools",
    "Tool",
    "TraversalWeights",
    "LiteralInterpreterV2",
    "SystemicTeleologicalV2",
    "PrinciplesBalancerV2",
    "PrecedentAnalystV2",
]
