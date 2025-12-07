"""
Storage Service Interfaces
==========================

Abstract interfaces for storage layer components.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Unified search result from any storage backend."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    source: str  # "vector", "graph", "hybrid"


@dataclass
class GraphNode:
    """Node from graph database."""
    id: str
    label: str
    properties: Dict[str, Any]


@dataclass
class GraphEdge:
    """Edge from graph database."""
    source_id: str
    target_id: str
    relation_type: str
    properties: Dict[str, Any]


class IVectorDB(ABC):
    """Interface for vector database operations."""

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Semantic similarity search."""
        pass

    @abstractmethod
    async def insert(
        self,
        id: str,
        embedding: List[float],
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Insert a vector with metadata."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        pass


class IGraphDB(ABC):
    """Interface for graph database operations."""

    @abstractmethod
    async def query(
        self,
        cypher: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query."""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a single node by ID."""
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "both",  # "in", "out", "both"
        limit: int = 50
    ) -> List[GraphNode]:
        """Get neighboring nodes."""
        pass

    @abstractmethod
    async def shortest_path(
        self,
        start_id: str,
        end_id: str,
        max_hops: int = 3
    ) -> Optional[List[GraphNode]]:
        """Find shortest path between nodes."""
        pass

    @abstractmethod
    async def traverse(
        self,
        start_id: str,
        relation_weights: Dict[str, float],
        max_depth: int = 3,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Weighted traversal for expert-specific retrieval."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        pass


class IBridgeTable(ABC):
    """Interface for vector-graph bridge table."""

    @abstractmethod
    async def get_graph_nodes(
        self,
        chunk_id: str
    ) -> List[Dict[str, Any]]:
        """Get graph nodes linked to a vector chunk."""
        pass

    @abstractmethod
    async def get_chunks(
        self,
        node_id: str
    ) -> List[Dict[str, Any]]:
        """Get vector chunks linked to a graph node."""
        pass

    @abstractmethod
    async def link(
        self,
        chunk_id: str,
        node_id: str,
        relation_type: str,
        weight: float = 1.0
    ) -> bool:
        """Create a link between chunk and node."""
        pass

    @abstractmethod
    async def update_weight(
        self,
        chunk_id: str,
        node_id: str,
        delta: float,
        authority: float
    ) -> bool:
        """Update link weight from RLCF feedback."""
        pass


class IStorageService(ABC):
    """
    Unified storage service interface.

    Combines vector, graph, and bridge operations
    into a single coherent API.

    This is the main interface that experts and
    orchestration should use.
    """

    @abstractmethod
    async def hybrid_search(
        self,
        query_embedding: List[float],
        context_nodes: Optional[List[str]] = None,
        expert_type: Optional[str] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Hybrid search combining vector similarity and graph structure.

        Args:
            query_embedding: Query vector
            context_nodes: Entities from query (for graph scoring)
            expert_type: Expert type for traversal weights
            top_k: Number of results

        Returns:
            Results ranked by: alpha * similarity + (1-alpha) * graph_score
        """
        pass

    @abstractmethod
    async def get_norm_text(self, urn: str) -> Optional[str]:
        """Get exact text of a legal norm by URN."""
        pass

    @abstractmethod
    async def get_definitions(self, term: str) -> List[Dict[str, Any]]:
        """Get legal definitions for a term."""
        pass

    @abstractmethod
    async def get_related_norms(
        self,
        urn: str,
        relation_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get norms related to a given norm."""
        pass

    @abstractmethod
    async def get_cases_for_norm(
        self,
        urn: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get case law interpreting a norm."""
        pass

    @abstractmethod
    async def search_cases(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search case law database."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all storage components."""
        pass
