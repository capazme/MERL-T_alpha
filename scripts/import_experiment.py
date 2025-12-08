#!/usr/bin/env python3
"""
Import Experiment Data
======================

Importa dati di un esperimento da backup JSON in FalkorDB + Qdrant.

Usage:
    python scripts/import_experiment.py --name costituzione --graph merl_t_exp_costituzione --collection exp_costituzione
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.storage.graph import FalkorDBClient, FalkorDBConfig


async def import_falkordb(graph_name: str, input_path: Path, clear_first: bool = True):
    """Import nodes and relationships into FalkorDB."""
    config = FalkorDBConfig(graph_name=graph_name)
    client = FalkorDBClient(config)
    await client.connect()

    # Load data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', {})
    relationships = data.get('relationships', [])

    print(f"  Loaded: {sum(len(v) for v in nodes.values())} nodes, {len(relationships)} relationships")

    # Clear graph if requested
    if clear_first:
        result = await client.query("MATCH (n) RETURN count(n) as c")
        existing = result[0]['c'] if result else 0
        if existing > 0:
            await client.query("MATCH (n) DETACH DELETE n")
            print(f"  Cleared {existing} existing nodes")

    # Import nodes by label
    for label, node_list in nodes.items():
        print(f"  Importing {len(node_list)} {label} nodes...")
        for node in node_list:
            # Build properties string
            props = {k: v for k, v in node.items() if v is not None}

            # Create node with all properties
            await client.query(
                f"CREATE (n:{label} $props)",
                {"props": props}
            )

    # Import relationships
    print(f"  Importing {len(relationships)} relationships...")
    imported_rels = 0
    for rel in relationships:
        try:
            await client.query(
                f"""
                MATCH (a {{URN: $from_urn}})
                MATCH (b {{URN: $to_urn}})
                CREATE (a)-[r:{rel['rel_type']}]->(b)
                SET r = $props
                """,
                {
                    "from_urn": rel['from_urn'],
                    "to_urn": rel['to_urn'],
                    "props": rel.get('rel_props', {}) or {}
                }
            )
            imported_rels += 1
        except Exception as e:
            # Skip if nodes not found
            pass

    print(f"    Imported {imported_rels} relationships")

    # Verify
    result = await client.query("MATCH (n) RETURN count(n) as c")
    total_nodes = result[0]['c'] if result else 0

    result = await client.query("MATCH ()-[r]->() RETURN count(r) as c")
    total_rels = result[0]['c'] if result else 0

    await client.close()

    return {"total_nodes": total_nodes, "total_relationships": total_rels}


def import_qdrant(collection_name: str, input_path: Path, clear_first: bool = True):
    """Import vectors into Qdrant collection."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    client = QdrantClient(host='localhost', port=6333)

    # Load data
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    points_data = data.get('points', [])
    vector_dim = data.get('stats', {}).get('vector_dimension', 1024)

    print(f"  Loaded: {len(points_data)} points (dim={vector_dim})")

    if not points_data:
        print("  No points to import")
        return {"total_points": 0}

    # Note: We only saved sample vectors (first 10 dims)
    # For full restore, we'd need to re-embed or save full vectors
    print("  WARNING: Backup contains sample vectors only (first 10 dims)")
    print("  Full vectors need to be re-generated from source text")

    # Create collection if needed
    collections = [c.name for c in client.get_collections().collections]

    if collection_name in collections:
        if clear_first:
            client.delete_collection(collection_name)
            print(f"  Deleted existing collection {collection_name}")

    if collection_name not in [c.name for c in client.get_collections().collections]:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE)
        )
        print(f"  Created collection {collection_name}")

    # For now, just recreate the payloads (vectors would need re-embedding)
    # This is a placeholder - in production you'd re-embed from text
    print("  Skipping vector import (would need re-embedding)")
    print("  Payloads available for re-embedding:")
    for p in points_data[:3]:
        print(f"    - {p['id']}: {p['payload'].get('text', '')[:50]}...")

    return {"total_points": 0, "note": "Vectors need re-embedding"}


async def main():
    parser = argparse.ArgumentParser(description="Import experiment data")
    parser.add_argument("--name", required=True, help="Experiment name")
    parser.add_argument("--graph", required=True, help="Target FalkorDB graph name")
    parser.add_argument("--collection", required=True, help="Target Qdrant collection name")
    parser.add_argument("--input-dir", default="data/backups/experiments", help="Input directory")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    parser.add_argument("--skip-vectors", action="store_true", help="Skip vector import")
    args = parser.parse_args()

    input_dir = Path(args.input_dir) / args.name

    if not input_dir.exists():
        print(f"ERROR: Experiment backup not found: {input_dir}")
        return

    print(f"\n{'='*60}")
    print(f"IMPORT EXPERIMENT: {args.name}")
    print(f"{'='*60}")
    print(f"Source: {input_dir}")
    print(f"Target Graph: {args.graph}")
    print(f"Target Collection: {args.collection}")

    # Import FalkorDB
    print(f"\n1. Importing FalkorDB graph...")
    graph_path = input_dir / "graph.json"
    if graph_path.exists():
        graph_stats = await import_falkordb(
            args.graph, graph_path,
            clear_first=not args.no_clear
        )
        print(f"   Result: {graph_stats['total_nodes']} nodes, {graph_stats['total_relationships']} relationships")
    else:
        print(f"   ERROR: {graph_path} not found")
        graph_stats = {}

    # Import Qdrant
    if not args.skip_vectors:
        print(f"\n2. Importing Qdrant collection...")
        vectors_path = input_dir / "vectors.json"
        if vectors_path.exists():
            vector_stats = import_qdrant(
                args.collection, vectors_path,
                clear_first=not args.no_clear
            )
        else:
            print(f"   ERROR: {vectors_path} not found")
            vector_stats = {}
    else:
        print(f"\n2. Skipping Qdrant (--skip-vectors)")
        vector_stats = {"skipped": True}

    print(f"\n{'='*60}")
    print("IMPORT COMPLETED")
    print(f"{'='*60}")
    print(f"Graph {args.graph}: {graph_stats.get('total_nodes', 0)} nodes")
    print(f"Note: Vectors need re-embedding from source text")


if __name__ == "__main__":
    asyncio.run(main())
