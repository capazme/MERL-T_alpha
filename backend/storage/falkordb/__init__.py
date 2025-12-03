"""
FalkorDB Client (v2)
====================

Graph database client replacing Neo4j.
FalkorDB is 496x faster for traversal queries and Cypher-compatible.

See docs/03-architecture/04-storage-layer.md for design details.

Usage (when implemented):
    from backend.storage.falkordb import FalkorDBClient

    client = FalkorDBClient(host="localhost", port=6379)

    # Cypher queries (same as Neo4j)
    results = await client.query('''
        MATCH (n:Norma {id: $norm_id})-[:INTERPRETA]-(s:Sentenza)
        RETURN s
    ''', {"norm_id": "art_1453_cc"})
"""

from .client import FalkorDBClient, FalkorDBConfig

__all__ = [
    "FalkorDBClient",
    "FalkorDBConfig",
]
