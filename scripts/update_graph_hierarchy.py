#!/usr/bin/env python3
"""
Update Graph Hierarchy
======================

Adds missing Titolo, Capo, Sezione nodes to FalkorDB graph
using positions extracted from Normattiva via treextractor.

Run: python scripts/update_graph_hierarchy.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
from typing import Dict, Set, Optional
from dataclasses import dataclass

# Suppress verbose logging
import structlog
class SilentLogger:
    def info(self, *args, **kwargs): pass
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass
    def bind(self, *args, **kwargs): return self

import backend.external_sources.visualex.tools.treextractor as treextractor
treextractor.log = SilentLogger()

from backend.external_sources.visualex.tools.treextractor import (
    get_hierarchical_tree,
    get_article_position,
    NormTree,
)
from backend.storage.falkordb.client import FalkorDBClient
from backend.preprocessing.ingestion_pipeline_v2 import IngestionPipelineV2


@dataclass
class HierarchyStats:
    titoli_created: int = 0
    capi_created: int = 0
    sezioni_created: int = 0
    relations_created: int = 0
    articles_updated: int = 0


async def main():
    print("=" * 60)
    print("Update Graph Hierarchy")
    print("=" * 60)

    # Connect to FalkorDB
    print("\n[1/5] Connecting to FalkorDB...")
    client = FalkorDBClient()
    await client.connect()
    print("  ✓ Connected")

    # Load NormTree from Normattiva
    print("\n[2/5] Loading NormTree from Normattiva...")
    codice_url = 'https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262'
    tree, article_count = await get_hierarchical_tree(codice_url)

    if isinstance(tree, str):
        print(f"  ✗ Error: {tree}")
        return

    print(f"  ✓ Loaded tree with {article_count} articles")

    # Get all article numbers from the graph
    print("\n[3/5] Getting articles from graph...")
    result = await client.query("""
        MATCH (n:Norma)
        WHERE n.tipo_documento = 'articolo'
        RETURN n.numero_articolo as num, n.URN as urn
    """)

    articles = [(row['num'], row['urn']) for row in result]
    print(f"  ✓ Found {len(articles)} articles in graph")

    # Create hierarchy nodes
    print("\n[4/5] Creating hierarchy nodes...")
    stats = HierarchyStats()

    codice_urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2"
    pipeline = IngestionPipelineV2()

    # Track created nodes to avoid duplicates
    created_nodes: Set[str] = set()

    # Get existing hierarchy nodes
    existing = await client.query("""
        MATCH (n:Norma)
        WHERE n.tipo_documento IN ['libro', 'titolo', 'capo', 'sezione']
        RETURN n.URN as urn
    """)
    for row in existing:
        created_nodes.add(row['urn'])
    print(f"  Existing hierarchy nodes: {len(created_nodes)}")

    for i, (article_num, article_urn) in enumerate(articles):
        if i % 100 == 0:
            print(f"  Processing article {i+1}/{len(articles)}...")

        # Get position from treextractor
        position = get_article_position(tree, str(article_num))
        if not position:
            continue

        # Extract hierarchy URNs
        hierarchy = pipeline._extract_hierarchy_urns(codice_urn, position)

        # Create Titolo node if missing
        if hierarchy.titolo and hierarchy.titolo not in created_nodes:
            titolo_title = pipeline._extract_hierarchy_title(position, 'titolo')
            await create_hierarchy_node(
                client, hierarchy.titolo, 'titolo', titolo_title,
                hierarchy.libro, codice_urn
            )
            created_nodes.add(hierarchy.titolo)
            stats.titoli_created += 1

        # Create Capo node if missing
        if hierarchy.capo and hierarchy.capo not in created_nodes:
            capo_title = pipeline._extract_hierarchy_title(position, 'capo')
            parent_urn = hierarchy.titolo or hierarchy.libro or codice_urn
            await create_hierarchy_node(
                client, hierarchy.capo, 'capo', capo_title,
                parent_urn, codice_urn
            )
            created_nodes.add(hierarchy.capo)
            stats.capi_created += 1

        # Create Sezione node if missing
        if hierarchy.sezione and hierarchy.sezione not in created_nodes:
            sezione_title = pipeline._extract_hierarchy_title(position, 'sezione')
            parent_urn = hierarchy.capo or hierarchy.titolo or hierarchy.libro or codice_urn
            await create_hierarchy_node(
                client, hierarchy.sezione, 'sezione', sezione_title,
                parent_urn, codice_urn
            )
            created_nodes.add(hierarchy.sezione)
            stats.sezioni_created += 1

        # Create :contiene relation from closest parent to article
        closest_parent = hierarchy.closest_parent(codice_urn)
        if closest_parent != codice_urn:  # Skip if only codice is parent
            await create_contiene_relation(client, closest_parent, article_urn)
            stats.relations_created += 1

        stats.articles_updated += 1

    # Print results
    print("\n[5/5] Results")
    print("=" * 60)
    print(f"  Titoli created:    {stats.titoli_created}")
    print(f"  Capi created:      {stats.capi_created}")
    print(f"  Sezioni created:   {stats.sezioni_created}")
    print(f"  Relations created: {stats.relations_created}")
    print(f"  Articles updated:  {stats.articles_updated}")
    print("=" * 60)

    # Verify final state
    result = await client.query("""
        MATCH (n:Norma)
        WHERE n.tipo_documento IN ['libro', 'titolo', 'capo', 'sezione']
        RETURN n.tipo_documento as tipo, count(n) as count
        ORDER BY count DESC
    """)
    print("\nFinal hierarchy node counts:")
    for row in result:
        print(f"  {row['tipo']}: {row['count']}")

    await client.close()
    print("\n✓ Done!")


async def create_hierarchy_node(
    client: FalkorDBClient,
    urn: str,
    tipo: str,
    titolo: Optional[str],
    parent_urn: str,
    codice_urn: str,
):
    """Create a hierarchy node (titolo, capo, sezione) in the graph."""
    now = datetime.now(timezone.utc).isoformat()

    # Create node
    await client.query(f"""
        MERGE (n:Norma {{URN: $urn}})
        ON CREATE SET
            n.node_id = $urn,
            n.url = $urn,
            n.tipo_documento = $tipo,
            n.titolo = $titolo,
            n.fonte = 'Normattiva',
            n.created_at = $now,
            n.updated_at = $now
    """, {
        'urn': urn,
        'tipo': tipo,
        'titolo': titolo or '',
        'now': now,
    })

    # Create :contiene relation from parent
    await client.query("""
        MATCH (parent:Norma {URN: $parent_urn})
        MATCH (child:Norma {URN: $child_urn})
        MERGE (parent)-[:contiene]->(child)
    """, {
        'parent_urn': parent_urn,
        'child_urn': urn,
    })


async def create_contiene_relation(
    client: FalkorDBClient,
    parent_urn: str,
    child_urn: str,
):
    """Create :contiene relation from hierarchy node to article."""
    await client.query("""
        MATCH (parent:Norma {URN: $parent_urn})
        MATCH (child:Norma {URN: $child_urn})
        MERGE (parent)-[:contiene]->(child)
    """, {
        'parent_urn': parent_urn,
        'child_urn': child_urn,
    })


if __name__ == "__main__":
    asyncio.run(main())
