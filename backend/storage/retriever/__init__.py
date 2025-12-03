"""
Graph-Aware Retriever (v2)
==========================

Hybrid retrieval combining vector similarity and graph structure.

Final score = alpha * similarity_score + (1-alpha) * graph_score

Where:
- similarity_score: Cosine similarity from Qdrant
- graph_score: Path-based score from FalkorDB via Bridge Table
- alpha: Learnable parameter (default 0.7)

See docs/03-architecture/04-storage-layer.md for design details.
"""

from .retriever import (
    GraphAwareRetriever,
    RetrievalResult,
    RetrieverConfig,
    EXPERT_TRAVERSAL_WEIGHTS,
)

__all__ = [
    "GraphAwareRetriever",
    "RetrievalResult",
    "RetrieverConfig",
    "EXPERT_TRAVERSAL_WEIGHTS",
]
