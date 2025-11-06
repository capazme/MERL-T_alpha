"""
Reasoning Experts for Legal Analysis

This module contains 4 reasoning experts based on Italian legal tradition:
- LiteralInterpreter: Positivismo Giuridico (strict textual analysis)
- SystemicTeleological: Teleologia Giuridica (purpose-oriented interpretation)
- PrinciplesBalancer: Costituzionalismo (constitutional principle balancing)
- PrecedentAnalyst: Empirismo Giuridico (case law analysis)

Each expert analyzes the same query using different legal reasoning methodologies.
"""

from .base import (
    ReasoningExpert,
    ExpertContext,
    ExpertOpinion,
    LegalBasis,
    ReasoningStep,
    ConfidenceFactors
)

from .literal_interpreter import LiteralInterpreter
from .systemic_teleological import SystemicTeleological
from .principles_balancer import PrinciplesBalancer
from .precedent_analyst import PrecedentAnalyst
from .synthesizer import Synthesizer, ProvisionalAnswer

__all__ = [
    # Base classes
    "ReasoningExpert",
    "ExpertContext",
    "ExpertOpinion",
    "LegalBasis",
    "ReasoningStep",
    "ConfidenceFactors",

    # Experts
    "LiteralInterpreter",
    "SystemicTeleological",
    "PrinciplesBalancer",
    "PrecedentAnalyst",

    # Synthesizer
    "Synthesizer",
    "ProvisionalAnswer",
]
