"""
Bridge Table (v2)
=================

Maps vector chunks to graph nodes for hybrid retrieval.

The Bridge Table enables Graph-Aware Similarity Search by linking:
- chunk_id (Qdrant vectors)
- graph_node_id (FalkorDB nodes)
- relation_type (PRIMARY, CONCEPT, REFERENCE)
- weight (learnable via RLCF)

See docs/03-architecture/04-storage-layer.md for design details.

Schema:
    bridge_table (
        chunk_id UUID,
        graph_node_id VARCHAR(200),
        relation_type VARCHAR(50),
        weight FLOAT DEFAULT 1.0  -- Learnable!
    )
"""

from .table import BridgeTable, BridgeTableBuilder, BridgeEntry

__all__ = [
    "BridgeTable",
    "BridgeTableBuilder",
    "BridgeEntry",
]
