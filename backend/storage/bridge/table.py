"""
Bridge Table
============

PostgreSQL table mapping vector chunks to graph nodes.

Enables hybrid retrieval by linking Qdrant vectors to FalkorDB nodes.
Weights are learnable via RLCF feedback.

See docs/03-architecture/04-storage-layer.md for design details.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BridgeEntry:
    """Single entry in the Bridge Table."""
    chunk_id: str
    graph_node_id: str
    relation_type: str  # PRIMARY, CONCEPT, REFERENCE, INTERPRETS
    weight: float = 1.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BridgeTable:
    """
    Bridge Table for vector-graph integration.

    v2 PLACEHOLDER - To be implemented with SQLAlchemy.

    Schema:
        CREATE TABLE bridge_table (
            id UUID PRIMARY KEY,
            chunk_id UUID NOT NULL,
            graph_node_id VARCHAR(200) NOT NULL,
            relation_type VARCHAR(50) NOT NULL,
            weight FLOAT DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(chunk_id, graph_node_id, relation_type)
        );

    Example:
        bridge = BridgeTable(db_session)

        # Get graph nodes for a chunk
        nodes = await bridge.get_nodes_for_chunk(chunk_id)

        # Get chunks for a graph node
        chunks = await bridge.get_chunks_for_node(node_id)

        # Update weight from RLCF feedback
        await bridge.update_weight(chunk_id, node_id, delta=0.1, authority=0.8)
    """

    def __init__(self, db_session=None):
        self.db_session = db_session
        logger.info("BridgeTable initialized (PLACEHOLDER)")

    async def get_nodes_for_chunk(
        self,
        chunk_id: str
    ) -> List[Tuple[str, str, float]]:
        """
        Get all graph nodes linked to a chunk.

        Args:
            chunk_id: Vector chunk ID

        Returns:
            List of (node_id, relation_type, weight)
        """
        # v2 PLACEHOLDER
        logger.warning(
            f"BridgeTable.get_nodes_for_chunk() - PLACEHOLDER. chunk={chunk_id}"
        )
        return []

    async def get_chunks_for_node(
        self,
        node_id: str
    ) -> List[Tuple[str, str, float]]:
        """
        Get all chunks linked to a graph node.

        Args:
            node_id: Graph node ID

        Returns:
            List of (chunk_id, relation_type, weight)
        """
        # v2 PLACEHOLDER
        logger.warning(
            f"BridgeTable.get_chunks_for_node() - PLACEHOLDER. node={node_id}"
        )
        return []

    async def insert(self, entry: BridgeEntry):
        """Insert a new bridge entry."""
        # v2 PLACEHOLDER
        logger.info(
            f"BridgeTable.insert() - PLACEHOLDER. "
            f"chunk={entry.chunk_id}, node={entry.graph_node_id}"
        )

    async def insert_batch(self, entries: List[BridgeEntry]):
        """Insert multiple bridge entries."""
        # v2 PLACEHOLDER
        logger.info(
            f"BridgeTable.insert_batch() - PLACEHOLDER. count={len(entries)}"
        )

    async def update_weight(
        self,
        chunk_id: str,
        node_id: str,
        delta: float,
        authority: float
    ):
        """
        Update weight from RLCF feedback.

        new_weight = clamp(old_weight + delta * authority, 0.0, 1.0)

        Args:
            chunk_id: Vector chunk ID
            node_id: Graph node ID
            delta: Weight change (-1.0 to 1.0)
            authority: Expert authority (0.0 to 1.0)
        """
        # v2 PLACEHOLDER
        effective_delta = delta * authority
        logger.info(
            f"BridgeTable.update_weight() - PLACEHOLDER. "
            f"chunk={chunk_id}, node={node_id}, delta={effective_delta:.3f}"
        )


class BridgeTableBuilder:
    """
    Builds Bridge Table entries during document ingestion.

    v2 PLACEHOLDER - To be implemented.

    For each chunk:
    1. Extract entities (NER)
    2. Resolve entities to graph nodes
    3. Calculate initial weight
    4. Insert into bridge_table
    """

    def __init__(self, bridge_table: BridgeTable, entity_resolver=None):
        self.bridge_table = bridge_table
        self.entity_resolver = entity_resolver
        logger.info("BridgeTableBuilder initialized (PLACEHOLDER)")

    async def build_for_chunk(
        self,
        chunk_id: str,
        chunk_text: str,
        source_urn: Optional[str] = None,
        entities: Optional[List[Dict]] = None
    ) -> List[BridgeEntry]:
        """
        Build bridge entries for a chunk.

        Args:
            chunk_id: Vector chunk ID
            chunk_text: Chunk text content
            source_urn: Source document URN (if known)
            entities: Pre-extracted entities (optional)

        Returns:
            List of BridgeEntry objects created
        """
        # v2 PLACEHOLDER
        logger.warning(
            f"BridgeTableBuilder.build_for_chunk() - PLACEHOLDER. "
            f"chunk={chunk_id}"
        )
        return []
