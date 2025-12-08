#!/usr/bin/env python3
"""
Export Experiment Data
======================

Esporta dati da un esperimento (FalkorDB + Qdrant) in file JSON
per backup e successiva ricostruzione.

Usage:
    python scripts/export_experiment.py --name costituzione --graph merl_t_dev --collection merl_t_dev_chunks
    python scripts/export_experiment.py --name libro_iv --graph merl_t_libro_iv --collection merl_t_libro_iv_chunks
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.storage.graph import FalkorDBClient, FalkorDBConfig


async def export_falkordb(graph_name: str, output_path: Path):
    """Export all nodes and relationships from FalkorDB."""
    config = FalkorDBConfig(graph_name=graph_name)
    client = FalkorDBClient(config)
    await client.connect()

    # Export nodes by type
    nodes = {}

    # Get all node labels
    labels_result = await client.query("CALL db.labels()")
    labels = [r['label'] for r in labels_result] if labels_result else []

    print(f"  Found labels: {labels}")

    for label in labels:
        result = await client.query(f"MATCH (n:{label}) RETURN n")
        nodes[label] = []
        for record in result:
            node_data = dict(record['n'].properties) if hasattr(record['n'], 'properties') else record['n']
            nodes[label].append(node_data)
        print(f"    - {label}: {len(nodes[label])} nodes")

    # Export relationships
    relationships = []
    rel_result = await client.query("""
        MATCH (a)-[r]->(b)
        RETURN
            labels(a)[0] as from_label,
            a.URN as from_urn,
            type(r) as rel_type,
            properties(r) as rel_props,
            labels(b)[0] as to_label,
            b.URN as to_urn
    """)

    for record in rel_result:
        relationships.append({
            "from_label": record['from_label'],
            "from_urn": record['from_urn'],
            "rel_type": record['rel_type'],
            "rel_props": record['rel_props'],
            "to_label": record['to_label'],
            "to_urn": record['to_urn'],
        })

    print(f"    - Relationships: {len(relationships)}")

    await client.close()

    # Save to file
    export_data = {
        "graph_name": graph_name,
        "exported_at": datetime.now().isoformat(),
        "nodes": nodes,
        "relationships": relationships,
        "stats": {
            "total_nodes": sum(len(v) for v in nodes.values()),
            "total_relationships": len(relationships),
            "labels": labels,
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return export_data['stats']


def export_qdrant(collection_name: str, output_path: Path):
    """Export all vectors from Qdrant collection."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host='localhost', port=6333)

    # Check if collection exists
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        print(f"  Collection {collection_name} not found")
        return {"total_points": 0}

    # Get collection info
    info = client.get_collection(collection_name)
    total_points = info.points_count

    print(f"  Collection {collection_name}: {total_points} points")

    if total_points == 0:
        return {"total_points": 0}

    # Scroll through all points
    points = []
    offset = None
    batch_size = 100

    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        batch_points, next_offset = result

        for point in batch_points:
            points.append({
                "id": str(point.id),
                "payload": point.payload,
                "vector": point.vector[:10] if point.vector else None,  # Save only first 10 dims as sample
                "vector_dim": len(point.vector) if point.vector else 0,
            })

        if next_offset is None:
            break
        offset = next_offset

    print(f"    Exported {len(points)} points")

    # Save to file
    export_data = {
        "collection_name": collection_name,
        "exported_at": datetime.now().isoformat(),
        "points": points,
        "stats": {
            "total_points": len(points),
            "vector_dimension": points[0]["vector_dim"] if points else 0,
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    return export_data['stats']


async def main():
    parser = argparse.ArgumentParser(description="Export experiment data")
    parser.add_argument("--name", required=True, help="Experiment name (e.g., costituzione, libro_iv)")
    parser.add_argument("--graph", required=True, help="FalkorDB graph name")
    parser.add_argument("--collection", required=True, help="Qdrant collection name")
    parser.add_argument("--output-dir", default="data/backups/experiments", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"EXPORT EXPERIMENT: {args.name}")
    print(f"{'='*60}")
    print(f"Graph: {args.graph}")
    print(f"Collection: {args.collection}")
    print(f"Output: {output_dir}")

    # Export FalkorDB
    print(f"\n1. Exporting FalkorDB graph...")
    graph_path = output_dir / "graph.json"
    graph_stats = await export_falkordb(args.graph, graph_path)
    print(f"   Saved to: {graph_path}")

    # Export Qdrant
    print(f"\n2. Exporting Qdrant collection...")
    vectors_path = output_dir / "vectors.json"
    vector_stats = export_qdrant(args.collection, vectors_path)
    print(f"   Saved to: {vectors_path}")

    # Create metadata file
    print(f"\n3. Creating metadata...")
    metadata = {
        "experiment_name": args.name,
        "exported_at": datetime.now().isoformat(),
        "source": {
            "falkordb_graph": args.graph,
            "qdrant_collection": args.collection,
        },
        "stats": {
            "graph": graph_stats,
            "vectors": vector_stats,
        },
        "files": [
            "graph.json",
            "vectors.json",
            "metadata.json",
        ]
    }

    metadata_path = output_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"   Saved to: {metadata_path}")

    print(f"\n{'='*60}")
    print("EXPORT COMPLETED")
    print(f"{'='*60}")
    print(f"Files saved in: {output_dir}")
    print(f"  - graph.json: {graph_stats['total_nodes']} nodes, {graph_stats['total_relationships']} relationships")
    print(f"  - vectors.json: {vector_stats['total_points']} points")


if __name__ == "__main__":
    asyncio.run(main())
