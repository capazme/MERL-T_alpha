#!/usr/bin/env python3
"""
EXP-008: Ingestion Costituzione Italiana Completa

Ingestion end-to-end della Costituzione Italiana (139 articoli) con:
- Graph: Nodi articolo + relazioni gerarchiche (FalkorDB)
- Embeddings: Vettori semantici (Qdrant)
- Bridge Table: Mapping chunk <-> nodo (PostgreSQL)
- Multivigenza: Tracking modifiche costituzionali

Usa LegalKnowledgeGraph come entry point unificato.

Usage:
    python scripts/ingest_costituzione.py
    python scripts/ingest_costituzione.py --dry-run
    python scripts/ingest_costituzione.py --start 1 --end 12
"""

import asyncio
import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from merlt import LegalKnowledgeGraph, MerltConfig
from merlt.core.legal_knowledge_graph import UnifiedIngestionResult

import structlog
log = structlog.get_logger()


@dataclass
class ArticleMetrics:
    """Metriche per singolo articolo."""
    numero: str
    success: bool = False
    time_seconds: float = 0.0
    nodes_created: int = 0
    relations_created: int = 0
    embeddings_upserted: int = 0
    bridge_mappings: int = 0
    modifiche_count: int = 0
    brocardi_enriched: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionMetrics:
    """Metriche complessive dell'ingestion."""
    start_time: str
    end_time: str = ""
    total_articles: int = 139
    articles_processed: int = 0
    articles_success: int = 0
    articles_with_errors: int = 0
    total_nodes: int = 0
    total_relations: int = 0
    total_embeddings: int = 0
    total_bridge_mappings: int = 0
    articles_with_modifiche: int = 0
    total_modifiche: int = 0
    articles: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def ingest_article(
    kg: LegalKnowledgeGraph,
    articolo: str,
    dry_run: bool = False
) -> ArticleMetrics:
    """
    Ingest singolo articolo della Costituzione.

    Args:
        kg: LegalKnowledgeGraph connesso
        articolo: Numero articolo (es. "1", "117")
        dry_run: Se True, non scrive su storage

    Returns:
        ArticleMetrics con risultati
    """
    metrics = ArticleMetrics(numero=articolo)
    start = time.time()

    try:
        if dry_run:
            log.info(f"[DRY-RUN] Art. {articolo} - skip ingestion")
            metrics.success = True
            metrics.time_seconds = time.time() - start
            return metrics

        result = await kg.ingest_norm(
            tipo_atto="costituzione",
            articolo=articolo,
            include_brocardi=True,
            include_embeddings=True,
            include_bridge=True,
            include_multivigenza=True,
        )

        # Popola metriche
        metrics.success = len(result.errors) == 0
        metrics.nodes_created = len(result.nodes_created)
        metrics.relations_created = len(result.relations_created)
        metrics.embeddings_upserted = result.embeddings_upserted
        metrics.bridge_mappings = result.bridge_mappings_inserted
        metrics.modifiche_count = result.modifiche_count
        metrics.brocardi_enriched = result.brocardi_enriched
        metrics.errors = result.errors

    except Exception as e:
        log.error(f"Art. {articolo}: {e}")
        metrics.errors.append(str(e))

    metrics.time_seconds = time.time() - start
    return metrics


async def ingest_costituzione(
    start_article: int = 1,
    end_article: int = 139,
    dry_run: bool = False,
    delay: float = 1.0,
) -> IngestionMetrics:
    """
    Ingest della Costituzione Italiana completa.

    Args:
        start_article: Articolo iniziale (default 1)
        end_article: Articolo finale (default 139)
        dry_run: Se True, non scrive su storage
        delay: Delay tra articoli in secondi

    Returns:
        IngestionMetrics con risultati completi
    """
    metrics = IngestionMetrics(
        start_time=datetime.now().isoformat(),
        total_articles=end_article - start_article + 1,
    )

    # Configura LegalKnowledgeGraph per ambiente test
    config = MerltConfig(
        graph_name="merl_t_test",
        qdrant_collection="merl_t_test_chunks",
        postgres_database="rlcf_dev",
    )

    kg = LegalKnowledgeGraph(config)

    try:
        print("=" * 60)
        print("EXP-008: Ingestion Costituzione Italiana Completa")
        print("=" * 60)
        print(f"Articoli: {start_article} - {end_article}")
        print(f"Dry run: {dry_run}")
        print(f"Delay: {delay}s")
        print("=" * 60)

        if not dry_run:
            print("\nConnessione storage backends...")
            await kg.connect()
            print("Connesso a FalkorDB, Qdrant, PostgreSQL")

        print(f"\nIngestion di {metrics.total_articles} articoli...\n")

        for art_num in range(start_article, end_article + 1):
            articolo = str(art_num)

            # Progresso
            progress = (art_num - start_article + 1) / metrics.total_articles * 100
            print(f"[{progress:5.1f}%] Art. {articolo}...", end=" ", flush=True)

            # Ingest
            art_metrics = await ingest_article(kg, articolo, dry_run)
            metrics.articles.append(art_metrics.to_dict())
            metrics.articles_processed += 1

            if art_metrics.success:
                metrics.articles_success += 1
                metrics.total_nodes += art_metrics.nodes_created
                metrics.total_relations += art_metrics.relations_created
                metrics.total_embeddings += art_metrics.embeddings_upserted
                metrics.total_bridge_mappings += art_metrics.bridge_mappings
                metrics.total_modifiche += art_metrics.modifiche_count
                if art_metrics.modifiche_count > 0:
                    metrics.articles_with_modifiche += 1

                status = "OK"
                if art_metrics.modifiche_count > 0:
                    status += f" (modifiche: {art_metrics.modifiche_count})"
                if art_metrics.brocardi_enriched:
                    status += " [Brocardi]"
            else:
                metrics.articles_with_errors += 1
                status = f"ERROR: {art_metrics.errors[0][:50] if art_metrics.errors else 'unknown'}"

            print(f"{status} ({art_metrics.time_seconds:.1f}s)")

            # Rate limiting
            if art_num < end_article and not dry_run:
                await asyncio.sleep(delay)

    finally:
        if kg.is_connected:
            await kg.close()

    metrics.end_time = datetime.now().isoformat()
    return metrics


def print_summary(metrics: IngestionMetrics):
    """Stampa summary finale."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tempo totale: {metrics.start_time} -> {metrics.end_time}")
    print(f"Articoli processati: {metrics.articles_processed}/{metrics.total_articles}")
    print(f"Articoli OK: {metrics.articles_success}")
    print(f"Articoli con errori: {metrics.articles_with_errors}")
    print(f"Error rate: {metrics.articles_with_errors / max(metrics.articles_processed, 1) * 100:.1f}%")
    print()
    print(f"Nodi FalkorDB: {metrics.total_nodes}")
    print(f"Relazioni FalkorDB: {metrics.total_relations}")
    print(f"Embeddings Qdrant: {metrics.total_embeddings}")
    print(f"Bridge mappings: {metrics.total_bridge_mappings}")
    print()
    print(f"Articoli con modifiche: {metrics.articles_with_modifiche}")
    print(f"Totale modifiche: {metrics.total_modifiche}")
    print("=" * 60)


def save_metrics(metrics: IngestionMetrics, output_path: str):
    """Salva metriche in JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\nMetriche salvate in: {output_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Ingestion Costituzione Italiana completa"
    )
    parser.add_argument(
        "--start", type=int, default=1,
        help="Articolo iniziale (default: 1)"
    )
    parser.add_argument(
        "--end", type=int, default=139,
        help="Articolo finale (default: 139)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Esegui senza scrivere su storage"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Delay tra articoli in secondi (default: 1.0)"
    )
    parser.add_argument(
        "--output", type=str,
        default="docs/experiments/costituzione_ingestion_metrics.json",
        help="Path output metriche JSON"
    )

    args = parser.parse_args()

    # Esegui ingestion
    metrics = await ingest_costituzione(
        start_article=args.start,
        end_article=args.end,
        dry_run=args.dry_run,
        delay=args.delay,
    )

    # Summary
    print_summary(metrics)

    # Salva metriche
    if not args.dry_run:
        save_metrics(metrics, args.output)


if __name__ == "__main__":
    asyncio.run(main())
