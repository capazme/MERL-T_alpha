#!/usr/bin/env python3
"""
Ingestion Libro IV Codice Civile - Usando LegalKnowledgeGraph API
==================================================================

Ingestion completa del Libro IV del Codice Civile (Obbligazioni, Art. 1173-2059)
usando la nuova API unificata di merlt.

Usage:
    python scripts/ingest_libro_iv_cc.py

    # Limita a N articoli (per test)
    python scripts/ingest_libro_iv_cc.py --limit 10

    # Salta Brocardi enrichment (piu veloce)
    python scripts/ingest_libro_iv_cc.py --skip-brocardi

    # Resume da articolo specifico
    python scripts/ingest_libro_iv_cc.py --start-from 100

    # Dry run
    python scripts/ingest_libro_iv_cc.py --dry-run
"""

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import della libreria merlt
from merlt import LegalKnowledgeGraph, MerltConfig


# Configurazione
GRAPH_NAME = "merl_t_libro_iv"
TIPO_ATTO = "codice civile"

# Articoli Libro IV CC (Delle Obbligazioni): 1173-2059
# Range completo
LIBRO_IV_RANGE = list(range(1173, 2060))  # 887 articoli


@dataclass
class IngestionMetrics:
    """Track ingestion metrics."""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    total_articles: int = 0
    articles_processed: int = 0
    articles_failed: int = 0

    brocardi_enriched: int = 0
    nodes_created: int = 0
    chunks_created: int = 0

    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timing": {
                "start": self.start_time,
                "end": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
            "articles": {
                "total": self.total_articles,
                "processed": self.articles_processed,
                "failed": self.articles_failed,
                "success_rate": f"{self.articles_processed / max(1, self.total_articles) * 100:.1f}%",
            },
            "enrichment": {
                "brocardi_enriched": self.brocardi_enriched,
                "nodes_created": self.nodes_created,
                "chunks_created": self.chunks_created,
            },
            "errors": self.errors[:20],
        }


async def clear_graph(kg: LegalKnowledgeGraph):
    """Clear existing data from graph."""
    if kg.falkordb:
        result = await kg.falkordb.query("MATCH (n) RETURN count(n) as c")
        count = result[0]['c'] if result else 0

        if count > 0:
            await kg.falkordb.query("MATCH (n) DETACH DELETE n")
            print(f"   Deleted {count} nodes from graph")
        else:
            print("   Graph already empty")


async def create_codice_node(kg: LegalKnowledgeGraph, timestamp: str) -> str:
    """Create main node for Codice Civile."""
    urn = "urn:nir:stato:regio.decreto:1942-03-16;262:2"

    await kg.falkordb.query(
        """
        MERGE (cc:Norma {URN: $urn})
        ON CREATE SET
            cc.node_id = $urn,
            cc.tipo_documento = 'codice',
            cc.titolo = 'Codice Civile',
            cc.tipo_atto = 'codice civile',
            cc.data_pubblicazione = '1942-03-16',
            cc.numero_atto = '262',
            cc.allegato = '2',
            cc.fonte = 'Normattiva',
            cc.created_at = $timestamp
        """,
        {"urn": urn, "timestamp": timestamp}
    )
    return urn


async def create_libro_node(kg: LegalKnowledgeGraph, cc_urn: str, timestamp: str) -> str:
    """Create node for Libro IV."""
    urn = f"{cc_urn}~libroIV"

    await kg.falkordb.query(
        """
        MERGE (libro:Norma {URN: $urn})
        ON CREATE SET
            libro.node_id = $urn,
            libro.tipo_documento = 'libro',
            libro.numero = 'IV',
            libro.titolo = 'Delle obbligazioni',
            libro.fonte = 'Normattiva',
            libro.created_at = $timestamp
        """,
        {"urn": urn, "timestamp": timestamp}
    )

    # Link to codice
    await kg.falkordb.query(
        """
        MATCH (cc:Norma {URN: $cc_urn})
        MATCH (libro:Norma {URN: $libro_urn})
        MERGE (cc)-[r:contiene]->(libro)
        ON CREATE SET r.certezza = 1.0
        """,
        {"cc_urn": cc_urn, "libro_urn": urn}
    )

    return urn


async def main():
    parser = argparse.ArgumentParser(description="Ingestion Libro IV Codice Civile")
    parser.add_argument("--limit", type=int, default=None, help="Limit to N articles")
    parser.add_argument("--skip-brocardi", action="store_true", help="Skip Brocardi enrichment")
    parser.add_argument("--skip-clear", action="store_true", help="Don't clear existing data")
    parser.add_argument("--start-from", type=int, default=0, help="Start from article index")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("=" * 70)
    print("INGESTION LIBRO IV CODICE CIVILE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Graph: {GRAPH_NAME}")
    print(f"Options: limit={args.limit}, skip_brocardi={args.skip_brocardi}")

    # Prepare article list
    articles = [str(n) for n in LIBRO_IV_RANGE]
    if args.limit:
        articles = articles[:args.limit]
    if args.start_from > 0:
        articles = articles[args.start_from:]
        print(f"   Resuming from index {args.start_from}")

    print(f"\nArticles to process: {len(articles)} (Art. {articles[0]} - {articles[-1]})")

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***")
        print(f"\nWould process {len(articles)} articles")
        print("First 10 articles:")
        for art in articles[:10]:
            print(f"  - Art. {art}")
        return

    # Initialize metrics
    metrics = IngestionMetrics()
    metrics.start_time = datetime.now().isoformat()
    metrics.total_articles = len(articles)

    # Initialize LegalKnowledgeGraph
    print("\n1. Connecting to storage backends...")
    config = MerltConfig(
        falkordb_host="localhost",
        falkordb_port=6380,
        graph_name=GRAPH_NAME,
        qdrant_host="localhost",
        qdrant_port=6333,
        postgres_host="localhost",
        postgres_port=5433,
        postgres_database="rlcf_dev",
        postgres_user="dev",
        postgres_password="devpassword",
    )

    kg = LegalKnowledgeGraph(config)
    await kg.connect()
    print(f"   Connected to: FalkorDB ({GRAPH_NAME}), Qdrant, PostgreSQL")

    # Clear graph
    print("\n2. Preparing graph...")
    if not args.skip_clear:
        await clear_graph(kg)
    else:
        print("   Skipping clear (--skip-clear)")

    # Create structure nodes
    print("\n3. Creating Codice Civile structure...")
    timestamp = datetime.now().isoformat()
    cc_urn = await create_codice_node(kg, timestamp)
    print(f"   Created: Codice Civile")

    libro_urn = await create_libro_node(kg, cc_urn, timestamp)
    print(f"   Created: Libro IV - Delle obbligazioni")

    # Process articles
    print(f"\n4. Processing {len(articles)} articles...")
    print("   (questo richiede diversi minuti)")

    start_time = time.time()

    for i, articolo in enumerate(articles):
        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(articles) - i - 1) / rate if rate > 0 else 0
            print(f"   [{i+1}/{len(articles)}] Art. {articolo} - {rate:.2f} art/s, ETA: {eta:.0f}s")

        try:
            # Use LegalKnowledgeGraph.ingest_norm()
            result = await kg.ingest_norm(
                tipo_atto=TIPO_ATTO,
                articolo=articolo,
                include_brocardi=not args.skip_brocardi,
                include_embeddings=True,
                include_bridge=True,
                include_multivigenza=False,  # Skip per ora
            )

            if result.errors and any("Fatal" in e for e in result.errors):
                metrics.articles_failed += 1
                metrics.errors.append({
                    "article": articolo,
                    "error": result.errors[0][:200]
                })
            else:
                metrics.articles_processed += 1
                metrics.nodes_created += len(result.nodes_created)
                metrics.chunks_created += result.chunks_created
                if result.brocardi_enriched:
                    metrics.brocardi_enriched += 1

                # Link to Libro IV
                if result.article_urn:
                    await kg.falkordb.query(
                        """
                        MATCH (libro:Norma {URN: $libro_urn})
                        MATCH (art:Norma {URN: $art_urn})
                        MERGE (libro)-[r:contiene]->(art)
                        ON CREATE SET r.certezza = 1.0
                        """,
                        {"libro_urn": libro_urn, "art_urn": result.article_urn}
                    )

        except Exception as e:
            metrics.articles_failed += 1
            metrics.errors.append({
                "article": articolo,
                "error": str(e)[:200]
            })

        # Rate limiting
        await asyncio.sleep(1.0)

        # Batch delay every 20 articles
        if (i + 1) % 20 == 0:
            await asyncio.sleep(3.0)

    # Finalize metrics
    metrics.end_time = datetime.now().isoformat()
    metrics.duration_seconds = time.time() - start_time

    # Validation
    print("\n5. Running validation queries...")

    result = await kg.falkordb.query("MATCH (n) RETURN count(n) as c")
    total_nodes = result[0]['c'] if result else 0

    result = await kg.falkordb.query(
        "MATCH (n:Norma {tipo_documento: 'articolo'}) RETURN count(n) as c"
    )
    article_nodes = result[0]['c'] if result else 0

    result = await kg.falkordb.query("MATCH ()-[r:contiene]->() RETURN count(r) as c")
    contiene_rels = result[0]['c'] if result else 0

    print(f"\n   Graph stats:")
    print(f"     - Total nodes: {total_nodes}")
    print(f"     - Article nodes: {article_nodes}")
    print(f"     - :contiene relations: {contiene_rels}")

    # Save metrics
    print("\n6. Saving metrics...")
    metrics_path = Path("docs/experiments/libro_iv_ingestion_metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_data = {
        "experiment": "Libro IV CC Ingestion",
        "description": "Ingestion Libro IV Codice Civile con LegalKnowledgeGraph API",
        "config": {
            "graph": GRAPH_NAME,
            "limit": args.limit,
            "skip_brocardi": args.skip_brocardi,
        },
        "metrics": metrics.to_dict(),
        "validation": {
            "total_nodes": total_nodes,
            "article_nodes": article_nodes,
            "contiene_relations": contiene_rels,
        },
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics_data, f, indent=2, ensure_ascii=False)
    print(f"   Saved to: {metrics_path}")

    # Cleanup
    await kg.close()

    # Summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETED")
    print("=" * 70)
    print(f"\nDuration: {metrics.duration_seconds:.1f} seconds ({metrics.duration_seconds/60:.1f} minutes)")
    print(f"Articles: {metrics.articles_processed}/{metrics.total_articles} ({metrics.articles_failed} failed)")
    print(f"Brocardi: {metrics.brocardi_enriched} enriched")
    print(f"Nodes created: {metrics.nodes_created}")
    print(f"Chunks created: {metrics.chunks_created}")
    print(f"\nGraph: {GRAPH_NAME}")


if __name__ == "__main__":
    asyncio.run(main())
