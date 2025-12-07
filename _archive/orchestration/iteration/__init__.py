"""
Iteration module for multi-turn refinement of legal answers.

This module provides:
- IterationContext: State management across refinement cycles
- IterationController: Main controller for iteration logic
- Stopping criteria: Multiple criteria for convergence detection
- Feedback integration: User and RLCF feedback incorporation
"""

from .models import (
    UserFeedback,
    RLCFQualityScore,
    IterationMetrics,
    IterationHistory,
    IterationContext,
    StoppingCriteria
)

from .controller import IterationController

__all__ = [
    "UserFeedback",
    "RLCFQualityScore",
    "IterationMetrics",
    "IterationHistory",
    "IterationContext",
    "StoppingCriteria",
    "IterationController"
]
