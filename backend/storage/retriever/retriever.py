"""
GraphAwareRetriever
====================

Hybrid retrieval combining Qdrant vector search with FalkorDB graph structure.

Core algorithm:
1. Vector search in Qdrant (semantic similarity)
2. For each result, find linked graph nodes via Bridge Table
3. Compute graph score based on shortest path to context nodes
4. Combine: final_score = α * similarity_score + (1-α) * graph_score
5. Re-rank and return top-k

See docs/03-architecture/04-storage-layer.md for design details.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from .models import (
    RetrievalResult,
    VectorSearchResult,
    GraphPath,
    RetrieverConfig,
    EXPERT_TRAVERSAL_WEIGHTS
)
from ..bridge import BridgeTable
from ..falkordb import FalkorDBClient

logger = logging.getLogger(__name__)


class GraphAwareRetriever:
    """
    Hybrid retriever combining vector similarity and graph structure.

    Flow:
        Query → Vector Search (Qdrant)
                       ↓
                 Chunk IDs
                       ↓
        Bridge Table → Graph Nodes (FalkorDB)
                       ↓
        Graph Score Calculation (shortest path)
                       ↓
        Hybrid Score = α * sim + (1-α) * graph
                       ↓
                Re-ranked Results

    Example:
        >>> retriever = GraphAwareRetriever(
        ...     vector_db=qdrant_client,
        ...     graph_db=falkordb_client,
        ...     bridge_table=bridge_table
        ... )
        >>> results = await retriever.retrieve(
        ...     query_embedding=embedding,
        ...     context_nodes=["urn:norma:cc:art1453"],
        ...     expert_type="LiteralExpert"
        ... )
    """

    def __init__(
        self,
        vector_db: Any,  # Qdrant client (not typed to avoid dependency)
        graph_db: FalkorDBClient,
        bridge_table: BridgeTable,
        config: Optional[RetrieverConfig] = None
    ):
        """
        Initialize GraphAwareRetriever.

        Args:
            vector_db: Qdrant client for vector search
            graph_db: FalkorDB client for graph traversal
            bridge_table: Bridge table for chunk→node mapping
            config: Retriever configuration (default: alpha=0.7)
        """
        self.vector_db = vector_db
        self.graph_db = graph_db
        self.bridge = bridge_table
        self.config = config or RetrieverConfig()

        logger.info(
            f"GraphAwareRetriever initialized - "
            f"alpha={self.config.alpha}, "
            f"over_retrieve={self.config.over_retrieve_factor}x, "
            f"max_hops={self.config.max_graph_hops}"
        )

    async def retrieve(
        self,
        query_embedding: List[float],
        context_nodes: Optional[List[str]] = None,
        expert_type: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Perform hybrid retrieval combining vector similarity and graph structure.

        Args:
            query_embedding: Query vector from embedding model (e.g., E5-large)
            context_nodes: Graph node URNs extracted from query via NER
                           Example: ["urn:norma:cc:art1453", "urn:concetto:contratto"]
            expert_type: Expert type for traversal weights (LiteralExpert, SystemicExpert, etc.)
            top_k: Number of results to return (default from config)

        Returns:
            List of RetrievalResult sorted by final_score (descending)

        Example:
            >>> context_nodes = ["urn:norma:cc:art1453"]  # Art. 1453 c.c.
            >>> results = await retriever.retrieve(
            ...     query_embedding=embed("termini risoluzione contratto"),
            ...     context_nodes=context_nodes,
            ...     expert_type="LiteralExpert",
            ...     top_k=10
            ... )
        """
        if top_k is None:
            top_k = 20

        logger.debug(
            f"retrieve() - context_nodes={len(context_nodes or [])}, "
            f"expert={expert_type}, top_k={top_k}"
        )

        # STEP 1: Vector search (over-retrieve for re-ranking)
        vector_results = await self._vector_search(
            query_embedding,
            limit=top_k * self.config.over_retrieve_factor
        )

        logger.debug(f"Vector search returned {len(vector_results)} candidates")

        # STEP 2: Graph enrichment
        enriched_results = []

        for vr in vector_results:
            # Find graph nodes linked to this chunk
            linked_nodes = await self.bridge.get_nodes_for_chunk(vr.chunk_id)

            # Compute graph score
            graph_score = await self._compute_graph_score(
                chunk_nodes=[node["graph_node_urn"] for node in linked_nodes],
                context_nodes=context_nodes or [],
                expert_type=expert_type
            )

            # Combine scores
            final_score = self._combine_scores(vr.similarity_score, graph_score)

            enriched_results.append(RetrievalResult(
                chunk_id=vr.chunk_id,
                text=vr.text,
                similarity_score=vr.similarity_score,
                graph_score=graph_score,
                final_score=final_score,
                linked_nodes=linked_nodes,
                metadata=vr.metadata
            ))

        # STEP 3: Re-rank by final_score
        enriched_results.sort(key=lambda x: x.final_score, reverse=True)

        top_results = enriched_results[:top_k]

        if top_results:
            avg_score = sum(r.final_score for r in top_results) / len(top_results)
            logger.info(
                f"retrieve() - returned {len(top_results)} results "
                f"(avg final_score={avg_score:.3f})"
            )
        else:
            logger.info("retrieve() - returned 0 results")

        return top_results

    async def _vector_search(
        self,
        query_embedding: List[float],
        limit: int
    ) -> List[VectorSearchResult]:
        """
        Step 1: Vector similarity search in Qdrant.

        Args:
            query_embedding: Query vector
            limit: Number of results to retrieve

        Returns:
            List of VectorSearchResult with chunk_id, text, similarity_score
        """
        if self.vector_db is None:
            logger.warning("vector_db not configured, returning empty results")
            return []

        # Qdrant search API
        # NOTE: Actual implementation depends on Qdrant client
        # This is a generic interface
        try:
            results = await self.vector_db.search(
                collection_name="legal_chunks",
                query_vector=query_embedding,
                limit=limit
            )

            return [
                VectorSearchResult(
                    chunk_id=UUID(r.id),
                    text=r.payload.get("text", ""),
                    similarity_score=r.score,
                    metadata=r.payload
                )
                for r in results
            ]

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _compute_graph_score(
        self,
        chunk_nodes: List[str],
        context_nodes: List[str],
        expert_type: Optional[str] = None
    ) -> float:
        """
        Step 2: Compute graph-based relevance score.

        Algorithm:
            1. For each (chunk_node, context_node) pair:
               - Find shortest path in graph (max_hops)
               - Score path based on length + relation weights
            2. Return max score across all pairs

        Args:
            chunk_nodes: Graph node URNs linked to the chunk
            context_nodes: Graph node URNs from query context
            expert_type: Expert type for relation weights

        Returns:
            Graph score in [0, 1]
        """
        if not self.config.enable_graph_enrichment:
            return self.config.default_graph_score

        if not context_nodes or not chunk_nodes:
            return self.config.default_graph_score

        max_score = 0.0

        for chunk_node in chunk_nodes:
            for context_node in context_nodes:
                # Find shortest path
                path = await self._find_shortest_path(
                    chunk_node,
                    context_node,
                    max_hops=self.config.max_graph_hops
                )

                if path:
                    path_score = self._score_path(path, expert_type)
                    max_score = max(max_score, path_score)

        return max_score if max_score > 0 else self.config.default_graph_score

    async def _find_shortest_path(
        self,
        source: str,
        target: str,
        max_hops: int
    ) -> Optional[GraphPath]:
        """
        Find shortest path between two nodes in FalkorDB.

        Args:
            source: Source node URN
            target: Target node URN
            max_hops: Maximum path length

        Returns:
            GraphPath or None if no path exists
        """
        try:
            result = await self.graph_db.shortest_path(
                start_node_urn=source,
                end_node_urn=target,
                max_hops=max_hops
            )

            if result and result.get("path"):
                path_data = result["path"]
                return GraphPath(
                    source_node=source,
                    target_node=target,
                    edges=path_data.get("edges", []),
                    length=path_data.get("length", 0)
                )

            return None

        except Exception as e:
            logger.debug(f"No path found {source} → {target}: {e}")
            return None

    def _score_path(
        self,
        path: GraphPath,
        expert_type: Optional[str] = None
    ) -> float:
        """
        Score a graph path based on length and relation weights.

        Formula:
            score = (1 / (length + 1)) * relation_bonus

        Where relation_bonus is the product of expert-specific weights
        for each edge type in the path.

        Args:
            path: GraphPath to score
            expert_type: Expert type for traversal weights

        Returns:
            Path score in [0, 1]
        """
        # Base score: shorter path = higher score
        distance_score = 1.0 / (path.length + 1)

        # Relation bonus: weighted by expert preferences
        relation_bonus = 1.0

        if expert_type and expert_type in EXPERT_TRAVERSAL_WEIGHTS:
            weights = EXPERT_TRAVERSAL_WEIGHTS[expert_type]

            for edge in path.edges:
                edge_type = edge.get("type", "")
                weight = weights.get(edge_type, weights.get("default", 0.5))
                relation_bonus *= weight

        return distance_score * relation_bonus

    def _combine_scores(
        self,
        similarity_score: float,
        graph_score: float
    ) -> float:
        """
        Step 3: Combine similarity and graph scores.

        Formula:
            final_score = α * similarity_score + (1-α) * graph_score

        Args:
            similarity_score: Cosine similarity from vector search [0-1]
            graph_score: Path-based score from graph [0-1]

        Returns:
            Combined score [0-1]
        """
        return (
            self.config.alpha * similarity_score +
            (1 - self.config.alpha) * graph_score
        )

    def update_alpha(self, feedback_correlation: float, authority: float):
        """
        Update alpha parameter based on RLCF feedback.

        Learnable parameter adjustment:
            - If graph_score correlates with relevance → decrease alpha (more graph weight)
            - If similarity_score correlates with relevance → increase alpha (more vector weight)

        Args:
            feedback_correlation: Correlation between graph_score and user feedback [-1, 1]
            authority: Authority score of feedback provider [0, 1]
        """
        if feedback_correlation > 0.5:
            # Graph score is useful, increase its weight
            delta = -0.01 * authority
        else:
            # Similarity score is more useful
            delta = 0.01 * authority

        # Update with bounds [0.3, 0.9]
        self.config.alpha = max(0.3, min(0.9, self.config.alpha + delta))

        logger.info(
            f"update_alpha() - new alpha={self.config.alpha:.3f} "
            f"(correlation={feedback_correlation:.3f}, authority={authority:.3f})"
        )
