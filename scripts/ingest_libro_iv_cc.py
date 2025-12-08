#!/usr/bin/env python3
"""
Ingestion Libro IV Codice Civile
================================

Ingestion completa del Libro IV del Codice Civile (Obbligazioni, Art. 1173-2059)
usando LegalKnowledgeGraph API con multi-source embeddings.

Segue EXPERIMENT_STRATEGY.md: esperimento isolato con naming convenzionale.

Usage:
    # Full ingestion (richiede ~15-20 ore con Brocardi)
    python scripts/ingest_libro_iv_cc.py

    # Test veloce (10 articoli, skip Brocardi)
    python scripts/ingest_libro_iv_cc.py --limit 10 --skip-brocardi

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
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt import LegalKnowledgeGraph, MerltConfig


# Configurazione (secondo EXPERIMENT_STRATEGY.md)
DEFAULT_GRAPH_NAME = "merl_t_exp_libro_iv_cc"
DEFAULT_COLLECTION = "exp_libro_iv_cc"
TIPO_ATTO = "codice civile"

# Articoli Libro IV CC (Delle Obbligazioni): 1173-2059
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
    total_embeddings: int = 0
    brocardi_enriched: int = 0
    nodes_created: int = 0
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
            "embeddings": {
                "total": self.total_embeddings,
            },
            "enrichment": {
                "brocardi_enriched": self.brocardi_enriched,
                "nodes_created": self.nodes_created,
            },
            "errors": self.errors[:20],  # Primi 20 errori
        }


async def main():
    parser = argparse.ArgumentParser(description="Ingestion Libro IV Codice Civile")
    parser.add_argument("--limit", type=int, default=None, help="Limit to N articles")
    parser.add_argument("--skip-brocardi", action="store_true", help="Skip Brocardi enrichment")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip embeddings")
    parser.add_argument("--start-from", type=int, default=0, help="Start from article index")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--graph", default=DEFAULT_GRAPH_NAME, help="FalkorDB graph name")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Qdrant collection name")
    args = parser.parse_args()

    graph_name = args.graph
    collection_name = args.collection

    print("=" * 70)
    print("INGESTION LIBRO IV CODICE CIVILE")
    print("Esperimento isolato secondo EXPERIMENT_STRATEGY.md")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"FalkorDB Graph: {graph_name}")
    print(f"Qdrant Collection: {collection_name}")
    print(f"Options: limit={args.limit}, brocardi={not args.skip_brocardi}, embeddings={not args.skip_embeddings}")

    # Prepara lista articoli
    articles = [str(n) for n in LIBRO_IV_RANGE]
    if args.start_from > 0:
        articles = articles[args.start_from:]
        print(f"   Resuming from index {args.start_from}")
    if args.limit:
        articles = articles[:args.limit]

    print(f"\nArticoli da processare: {len(articles)}")
    if articles:
        print(f"   Da Art. {articles[0]} a Art. {articles[-1]}")

    if args.dry_run:
        print("\n*** DRY RUN - Nessuna modifica ***")
        print(f"\nProcesserebbe {len(articles)} articoli")
        print("Primi 10:")
        for art in articles[:10]:
            print(f"  - Art. {art}")
        return

    # Inizializza metrics
    metrics = IngestionMetrics()
    metrics.start_time = datetime.now().isoformat()
    metrics.total_articles = len(articles)

    # Connetti a LegalKnowledgeGraph
    print("\n1. Connessione ai backend...")
    config = MerltConfig(
        graph_name=graph_name,
        qdrant_collection=collection_name,
    )

    kg = LegalKnowledgeGraph(config)
    await kg.connect()
    print(f"   Connesso: FalkorDB ({graph_name}), Qdrant ({collection_name})")

    # Processa articoli
    print(f"\n2. Processing {len(articles)} articoli...")
    print("   (Multi-source embeddings: norma + spiegazione + ratio + massime)")
    print()

    start_time = time.time()

    for i, articolo in enumerate(articles):
        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(articles) - i - 1) / rate if rate > 0 else 0
            print(f"   [{i+1}/{len(articles)}] Art. {articolo} - {rate:.2f} art/s, ETA: {eta/60:.0f}min")

        try:
            result = await kg.ingest_norm(
                tipo_atto=TIPO_ATTO,
                articolo=articolo,
                include_brocardi=not args.skip_brocardi,
                include_embeddings=not args.skip_embeddings,
                include_bridge=True,
                include_multivigenza=False,  # Skip per esperimento
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
                metrics.total_embeddings += result.embeddings_upserted
                if result.brocardi_enriched:
                    metrics.brocardi_enriched += 1

        except Exception as e:
            metrics.articles_failed += 1
            metrics.errors.append({
                "article": articolo,
                "error": str(e)[:200]
            })

        # Rate limiting per Brocardi
        if not args.skip_brocardi:
            await asyncio.sleep(1.0)
            if (i + 1) % 20 == 0:
                await asyncio.sleep(3.0)

    # Finalizza metrics
    metrics.end_time = datetime.now().isoformat()
    metrics.duration_seconds = time.time() - start_time

    # Validazione
    print("\n3. Validazione...")

    result = await kg.falkordb.query("MATCH (n) RETURN count(n) as c")
    total_nodes = result[0]['c'] if result else 0

    result = await kg.falkordb.query("MATCH (n:Norma) WHERE n.numero_articolo IS NOT NULL RETURN count(n) as c")
    article_nodes = result[0]['c'] if result else 0

    result = await kg.falkordb.query("MATCH ()-[r]->() RETURN count(r) as c")
    total_rels = result[0]['c'] if result else 0

    print(f"   FalkorDB: {total_nodes} nodi, {article_nodes} articoli, {total_rels} relazioni")

    # Qdrant stats
    from qdrant_client import QdrantClient
    qdrant = QdrantClient(host="localhost", port=6333)
    try:
        info = qdrant.get_collection(collection_name)
        print(f"   Qdrant: {info.points_count} embeddings")
    except Exception:
        print(f"   Qdrant: collection non trovata")

    # Salva metrics
    print("\n4. Salvataggio metrics...")
    metrics_path = Path("docs/experiments/libro_iv_cc_ingestion.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    metrics_data = {
        "experiment": "Libro IV CC Ingestion",
        "description": "Ingestion isolata Libro IV CC con multi-source embeddings",
        "config": {
            "graph": graph_name,
            "collection": collection_name,
            "limit": args.limit,
            "skip_brocardi": args.skip_brocardi,
            "skip_embeddings": args.skip_embeddings,
        },
        "metrics": metrics.to_dict(),
        "validation": {
            "total_nodes": total_nodes,
            "article_nodes": article_nodes,
            "total_relationships": total_rels,
        },
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics_data, f, indent=2, ensure_ascii=False)
    print(f"   Salvato: {metrics_path}")

    await kg.close()

    # Summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETATA")
    print("=" * 70)
    print(f"\nDurata: {metrics.duration_seconds:.1f}s ({metrics.duration_seconds/60:.1f} min)")
    print(f"Articoli: {metrics.articles_processed}/{metrics.total_articles} ({metrics.articles_failed} falliti)")
    print(f"Embeddings: {metrics.total_embeddings} (multi-source)")
    print(f"Brocardi: {metrics.brocardi_enriched} arricchiti")
    print(f"\nGraph: {graph_name}")
    print(f"Collection: {collection_name}")


if __name__ == "__main__":
    asyncio.run(main())
