"""
Expert Gating Network (v2)
==========================

Mixture of Experts gating for legal reasoning experts.

Components:
- ExpertGatingNetwork: Neural network that weights expert contributions
- GatingTrainer: RLCF-based training for gating weights

See docs/03-architecture/02-orchestration-layer.md for design details.

Usage (when implemented):
    from backend.orchestration.gating import ExpertGatingNetwork

    gating = ExpertGatingNetwork(input_dim=1024, num_experts=4)
    weights = gating(query_embedding)  # [w_literal, w_systemic, w_principles, w_precedent]
"""

from .gating_network import ExpertGatingNetwork, GatingConfig

__all__ = [
    "ExpertGatingNetwork",
    "GatingConfig",
]
