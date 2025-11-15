"""
VectorDB Agent for Semantic Search

This agent performs semantic search over legal documents using Qdrant vector database.

Supported Search Patterns:
- P1 (Semantic): Pure vector search using E5-large embeddings
- P3 (Filtered): Vector search + metadata filtering
- P4 (Reranked): Initial retrieval + cross-encoder reranking

Task Types:
- semantic_search: Query → Embedding → Vector search → Top-K results
- filtered_search: Semantic search + metadata filters (document_type, temporal_metadata, etc.)
- reranked_search: Semantic search (top-100) → Cross-encoder reranking (top-10)

Reference: orchestration_config.yaml (lines 74-85)
"""

import logging
import time
from typing import List, Dict, Any, Optional
import asyncio

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Filter,
        FieldCondition,
        MatchValue,
        MatchAny,
        Range,
        SearchRequest,
        ScoredPoint
    )
except ImportError:
    raise ImportError(
        "qdrant-client is required for VectorDBAgent. "
        "Install with: pip install qdrant-client"
    )

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None  # Optional dependency for P4

from .base import RetrievalAgent, AgentTask, AgentResult
from backend.orchestration.services.embedding_service import EmbeddingService
from backend.orchestration.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


class VectorDBAgent(RetrievalAgent):
    """
    Retrieval agent for semantic search using Qdrant vector database.

    Implements 3 search patterns:
    - P1 (Semantic): Pure vector similarity search
    - P3 (Filtered): Vector search + metadata filtering
    - P4 (Reranked): Initial retrieval + cross-encoder reranking

    Usage:
        agent = VectorDBAgent(
            qdrant_client=qdrant_client,
            embedding_service=embedding_service,
            config=config
        )

        tasks = [
            AgentTask(
                task_type="semantic_search",
                params={
                    "query": "Cos'è il contratto?",
                    "top_k": 10
                }
            )
        ]

        result = await agent.execute(tasks)
    """

    SUPPORTED_TASKS = [
        "semantic_search",   # P1: Pure vector search
        "filtered_search",   # P3: Vector + metadata filters
        "reranked_search"    # P4: Retrieval + reranking
    ]

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize VectorDBAgent.

        Args:
            qdrant_client: Qdrant client (deprecated, use qdrant_service)
            qdrant_service: QdrantService instance (if None, will be created lazily)
            embedding_service: EmbeddingService instance
            config: Agent configuration from orchestration_config.yaml
        """
        super().__init__(agent_name="vectordb_agent", config=config)

        # Qdrant setup (lazy initialization)
        if qdrant_service:
            self.qdrant_service = qdrant_service
            self.qdrant_client = qdrant_service.client
            self.collection_name = qdrant_service.collection_name
        elif qdrant_client:
            # Fallback: direct client (deprecated)
            self.qdrant_client = qdrant_client
            self.qdrant_service = None
            self.collection_name = config.get("collection_name", "legal_corpus") if config else "legal_corpus"
        else:
            # Will be initialized lazily in execute() if needed
            self.qdrant_service = None
            self.qdrant_client = None
            self.collection_name = config.get("collection_name", "legal_corpus") if config else "legal_corpus"

        # Embedding service
        self.embedding_service = embedding_service or EmbeddingService.get_instance()

        # Configuration
        self.max_results = config.get("max_results", 10) if config else 10
        self.default_search_pattern = config.get("default_pattern", "semantic") if config else "semantic"
        self.rerank_top_k = config.get("rerank_top_k", 5) if config else 5

        # Cross-encoder for P4 (reranking)
        self.cross_encoder = None
        if CrossEncoder:
            try:
                # Lightweight cross-encoder for reranking
                self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                logger.info("Cross-encoder loaded for reranking")
            except Exception as e:
                logger.warning(f"Could not load cross-encoder: {e}")

        logger.info(f"VectorDBAgent initialized with collection: {self.collection_name}")

    async def execute(self, tasks: List[AgentTask]) -> AgentResult:
        """
        Execute vector search tasks.

        Args:
            tasks: List of retrieval tasks

        Returns:
            AgentResult with search results
        """
        start_time = time.time()
        all_results = []
        errors = []

        # Lazy initialization of Qdrant service
        if self.qdrant_service is None and self.qdrant_client is None:
            try:
                logger.info("Initializing QdrantService with defaults from env vars")
                self.qdrant_service = QdrantService()
                self.qdrant_client = self.qdrant_service.client
                self.collection_name = self.qdrant_service.collection_name
            except Exception as e:
                error_msg = f"Failed to initialize QdrantService: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return AgentResult(
                    agent_name=self.agent_name,
                    success=False,
                    data=[],
                    errors=[error_msg],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    tasks_executed=0
                )

        # Validate tasks
        for task in tasks:
            if task.task_type not in self.SUPPORTED_TASKS:
                errors.append(
                    f"Unsupported task type: {task.task_type}. "
                    f"Supported: {', '.join(self.SUPPORTED_TASKS)}"
                )
                continue

            try:
                # Execute task based on type
                if task.task_type == "semantic_search":
                    results = await self._semantic_search(task.params)
                elif task.task_type == "filtered_search":
                    results = await self._filtered_search(task.params)
                elif task.task_type == "reranked_search":
                    results = await self._reranked_search(task.params)
                else:
                    # Should never reach here due to validation above
                    results = []

                all_results.extend(results)

            except Exception as e:
                error_msg = f"Error executing {task.task_type}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        execution_time_ms = (time.time() - start_time) * 1000

        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) == 0,
            data=all_results,
            errors=errors,
            execution_time_ms=execution_time_ms,
            tasks_executed=len(tasks)
        )

    async def _semantic_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Pattern P1: Pure vector search.

        Encodes query → Searches Qdrant → Returns top-K results.

        Args:
            params: {
                "query": str,
                "top_k": int (optional, default: self.max_results),
                "score_threshold": float (optional, minimum similarity score)
            }

        Returns:
            List of search results with text, score, and metadata
        """
        query = params.get("query")
        if not query:
            raise ValueError("Query is required for semantic_search")

        top_k = params.get("top_k", self.max_results)
        score_threshold = params.get("score_threshold", 0.0)

        logger.info(f"Semantic search: '{query}' (top_k={top_k})")

        # Encode query
        query_vector = await self.embedding_service.encode_query_async(query)

        # Search Qdrant
        search_results = await asyncio.to_thread(
            self.qdrant_client.search,
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False  # Don't return vectors in response
        )

        # Format results
        results = []
        for hit in search_results:
            results.append({
                "id": hit.id,
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": {
                    "document_type": hit.payload.get("document_type"),
                    "temporal_metadata": hit.payload.get("temporal_metadata"),
                    "classification": hit.payload.get("classification"),
                    "authority_metadata": hit.payload.get("authority_metadata"),
                    "entities_extracted": hit.payload.get("entities_extracted")
                },
                "search_pattern": "semantic"
            })

        logger.info(f"Semantic search returned {len(results)} results")
        return results

    async def _filtered_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Pattern P3: Vector search + metadata filtering.

        Supports filtering by:
        - document_type: "norm" | "jurisprudence" | "doctrine"
        - temporal_metadata.is_current: bool
        - classification.legal_area: str
        - classification.complexity_level: int (range)

        Args:
            params: {
                "query": str,
                "top_k": int (optional),
                "filters": {
                    "document_type": str | List[str],
                    "is_current": bool,
                    "legal_area": str | List[str],
                    "complexity_level": int | {"gte": int, "lte": int},
                    ...
                }
            }

        Returns:
            List of filtered search results
        """
        query = params.get("query")
        if not query:
            raise ValueError("Query is required for filtered_search")

        top_k = params.get("top_k", self.max_results)
        filters_dict = params.get("filters", {})

        logger.info(f"Filtered search: '{query}' with filters: {filters_dict}")

        # Encode query
        query_vector = await self.embedding_service.encode_query_async(query)

        # Build Qdrant filter
        qdrant_filter = self._build_filter(filters_dict)

        # Search with filter
        search_results = await asyncio.to_thread(
            self.qdrant_client.search,
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )

        # Format results
        results = []
        for hit in search_results:
            results.append({
                "id": hit.id,
                "text": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": {
                    "document_type": hit.payload.get("document_type"),
                    "temporal_metadata": hit.payload.get("temporal_metadata"),
                    "classification": hit.payload.get("classification"),
                    "authority_metadata": hit.payload.get("authority_metadata"),
                    "entities_extracted": hit.payload.get("entities_extracted")
                },
                "search_pattern": "filtered",
                "applied_filters": filters_dict
            })

        logger.info(f"Filtered search returned {len(results)} results")
        return results

    async def _reranked_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Pattern P4: Initial retrieval + cross-encoder reranking.

        Two-stage retrieval:
        1. Vector search (top-100, fast)
        2. Cross-encoder reranking (top-10, slower but more accurate)

        Requires cross-encoder model to be loaded.

        Args:
            params: {
                "query": str,
                "top_k": int (optional, final results after reranking),
                "initial_top_k": int (optional, initial retrieval size, default: 100),
                "score_threshold": float (optional)
            }

        Returns:
            List of reranked search results
        """
        query = params.get("query")
        if not query:
            raise ValueError("Query is required for reranked_search")

        top_k = params.get("top_k", self.rerank_top_k)
        initial_top_k = params.get("initial_top_k", 100)
        score_threshold = params.get("score_threshold", 0.0)

        logger.info(f"Reranked search: '{query}' (initial: {initial_top_k}, final: {top_k})")

        # Stage 1: Initial retrieval (vector search)
        query_vector = await self.embedding_service.encode_query_async(query)

        search_results = await asyncio.to_thread(
            self.qdrant_client.search,
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=initial_top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False
        )

        if not search_results:
            logger.info("No results from initial retrieval")
            return []

        # Stage 2: Reranking with cross-encoder
        if self.cross_encoder is None:
            logger.warning("Cross-encoder not available, returning initial results (top-K)")
            # Fallback: return top-K from initial results
            results = []
            for hit in search_results[:top_k]:
                results.append({
                    "id": hit.id,
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "metadata": {
                        "document_type": hit.payload.get("document_type"),
                        "temporal_metadata": hit.payload.get("temporal_metadata"),
                        "classification": hit.payload.get("classification"),
                        "authority_metadata": hit.payload.get("authority_metadata"),
                        "entities_extracted": hit.payload.get("entities_extracted")
                    },
                    "search_pattern": "semantic_fallback",
                    "reranked": False
                })
            return results

        # Prepare query-document pairs for cross-encoder
        pairs = [[query, hit.payload.get("text", "")] for hit in search_results]

        # Rerank with cross-encoder
        logger.info(f"Reranking {len(pairs)} candidates with cross-encoder")
        rerank_scores = await asyncio.to_thread(
            self.cross_encoder.predict,
            pairs
        )

        # Combine original results with rerank scores
        reranked_results = []
        for hit, rerank_score in zip(search_results, rerank_scores):
            reranked_results.append({
                "hit": hit,
                "vector_score": hit.score,
                "rerank_score": float(rerank_score)
            })

        # Sort by rerank score (descending)
        reranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Take top-K after reranking
        final_results = []
        for item in reranked_results[:top_k]:
            hit = item["hit"]
            final_results.append({
                "id": hit.id,
                "text": hit.payload.get("text", ""),
                "score": item["rerank_score"],  # Use rerank score as primary
                "vector_score": item["vector_score"],  # Keep original score
                "metadata": {
                    "document_type": hit.payload.get("document_type"),
                    "temporal_metadata": hit.payload.get("temporal_metadata"),
                    "classification": hit.payload.get("classification"),
                    "authority_metadata": hit.payload.get("authority_metadata"),
                    "entities_extracted": hit.payload.get("entities_extracted")
                },
                "search_pattern": "reranked",
                "reranked": True
            })

        logger.info(f"Reranked search returned {len(final_results)} results")
        return final_results

    def _build_filter(self, filters_dict: Dict[str, Any]) -> Optional[Filter]:
        """
        Build Qdrant filter from dictionary.

        Supported filters:
        - document_type: str | List[str]
        - is_current: bool
        - legal_area: str | List[str]
        - complexity_level: int | {"gte": int, "lte": int}

        Args:
            filters_dict: Dictionary of filter conditions

        Returns:
            Qdrant Filter object or None if no filters
        """
        if not filters_dict:
            return None

        conditions = []

        # Filter by document_type
        if "document_type" in filters_dict:
            doc_type = filters_dict["document_type"]
            if isinstance(doc_type, list):
                conditions.append(
                    FieldCondition(
                        key="document_type",
                        match=MatchAny(any=doc_type)
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="document_type",
                        match=MatchValue(value=doc_type)
                    )
                )

        # Filter by is_current (temporal metadata)
        if "is_current" in filters_dict:
            conditions.append(
                FieldCondition(
                    key="temporal_metadata.is_current",
                    match=MatchValue(value=filters_dict["is_current"])
                )
            )

        # Filter by legal_area
        if "legal_area" in filters_dict:
            legal_area = filters_dict["legal_area"]
            if isinstance(legal_area, list):
                conditions.append(
                    FieldCondition(
                        key="classification.legal_area",
                        match=MatchAny(any=legal_area)
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="classification.legal_area",
                        match=MatchValue(value=legal_area)
                    )
                )

        # Filter by complexity_level (range)
        if "complexity_level" in filters_dict:
            complexity = filters_dict["complexity_level"]
            if isinstance(complexity, dict):
                # Range filter: {"gte": 1, "lte": 3}
                conditions.append(
                    FieldCondition(
                        key="classification.complexity_level",
                        range=Range(
                            gte=complexity.get("gte"),
                            lte=complexity.get("lte")
                        )
                    )
                )
            else:
                # Exact match
                conditions.append(
                    FieldCondition(
                        key="classification.complexity_level",
                        match=MatchValue(value=complexity)
                    )
                )

        if not conditions:
            return None

        # Combine conditions with AND logic
        return Filter(must=conditions)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"VectorDBAgent("
            f"collection={self.collection_name}, "
            f"max_results={self.max_results}, "
            f"patterns={', '.join(self.SUPPORTED_TASKS)})"
        )
