#!/usr/bin/env python3
"""
Apply Multivigenza to existing Codice Penale articles.

Reads articles from FalkorDB graph and applies multivigenza tracking
without re-ingesting the text (which is already present).

Usage:
    python scripts/apply_multivigenza_cp.py
    python scripts/apply_multivigenza_cp.py --limit 10  # Test with 10 articles
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from falkordb import FalkorDB

import sys
sys.path.insert(0, '.')

from merlt.external_sources.visualex.tools.norma import NormaVisitata, Norma
from merlt.external_sources.visualex.scrapers.normattiva_scraper import NormattivaScraper
from merlt.preprocessing.multivigenza_pipeline import MultivigenzaPipeline
from merlt.storage import FalkorDBClient, FalkorDBConfig


# Config
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380
GRAPH_NAME = "merl_t_test"

# Delays for rate limiting
DELAY_BETWEEN_ARTICLES = 1.0
BATCH_DELAY = 3.0
BATCH_SIZE = 10


async def main():
    parser = argparse.ArgumentParser(description="Apply multivigenza to CP articles")
    parser.add_argument("--limit", type=int, help="Limit to N articles")
    args = parser.parse_args()

    print("=" * 70)
    print("APPLY MULTIVIGENZA - CODICE PENALE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Connect to FalkorDB
    print("\n1. Connecting to services...")
    config = FalkorDBConfig(host=FALKORDB_HOST, port=FALKORDB_PORT, graph_name=GRAPH_NAME)
    client = FalkorDBClient(config)
    await client.connect()
    print(f"   FalkorDB: {GRAPH_NAME}")

    # Initialize scrapers
    scraper = NormattivaScraper()
    print("   NormattivaScraper ready")

    pipeline = MultivigenzaPipeline(falkordb_client=client, scraper=scraper)
    print("   MultivigenzaPipeline ready")

    # Get articles from graph
    print("\n2. Loading articles from graph...")
    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = fb.select_graph(GRAPH_NAME)

    result = graph.query("""
        MATCH (art:Norma {tipo_documento: 'articolo'})
        RETURN art.numero_articolo as numero
        ORDER BY 
            CASE WHEN art.numero_articolo CONTAINS 'bis' THEN 1
                 WHEN art.numero_articolo CONTAINS 'ter' THEN 2
                 ELSE 0 END,
            toInteger(replace(replace(replace(art.numero_articolo, ' bis', ''), ' ter', ''), ' quater', ''))
    """)

    articles = [row[0] for row in result.result_set]
    if args.limit:
        articles = articles[:args.limit]

    print(f"   Found {len(articles)} articles")

    # Process multivigenza
    print(f"\n3. Applying multivigenza to {len(articles)} articles...")
    print("   (this may take several minutes)")

    stats = {
        "processed": 0,
        "with_modifications": 0,
        "total_modifiche": 0,
        "atti_creati": 0,
        "relazioni_create": 0,
        "errors": []
    }

    import time
    start_time = time.time()

    for i, numero in enumerate(articles):
        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(articles) - i - 1) / rate if rate > 0 else 0
            print(f"   [{i+1}/{len(articles)}] Art. {numero} - {rate:.2f} art/s, ETA: {eta:.0f}s")

        try:
            # Create NormaVisitata for codice penale
            numero_norm = numero.replace(' ', '-')
            norma = Norma(tipo_atto='codice penale', data=None, numero_atto=None)
            nv = NormaVisitata(norma=norma, numero_articolo=numero_norm)

            # Apply multivigenza
            mv_result = await pipeline.ingest_with_history(
                nv,
                fetch_all_versions=False,
                create_modifying_acts=True,
            )

            stats["processed"] += 1

            if mv_result.storia and mv_result.storia.modifiche:
                stats["with_modifications"] += 1
                stats["total_modifiche"] += len(mv_result.storia.modifiche)
                stats["atti_creati"] += len(mv_result.atti_modificanti_creati)
                stats["relazioni_create"] += len(mv_result.relazioni_create)

        except Exception as e:
            stats["errors"].append({"article": numero, "error": str(e)[:100]})

        # Rate limiting
        await asyncio.sleep(DELAY_BETWEEN_ARTICLES)

        # Batch delay
        if (i + 1) % BATCH_SIZE == 0:
            await asyncio.sleep(BATCH_DELAY)

    # Summary
    duration = time.time() - start_time

    print("\n" + "=" * 70)
    print("MULTIVIGENZA COMPLETED")
    print("=" * 70)
    print(f"\nDuration: {duration:.1f} seconds")
    print(f"Articles processed: {stats['processed']}/{len(articles)}")
    print(f"With modifications: {stats['with_modifications']}")
    print(f"Total modifiche: {stats['total_modifiche']}")
    print(f"Atti modificanti creati: {stats['atti_creati']}")
    print(f"Relazioni create: {stats['relazioni_create']}")
    print(f"Errors: {len(stats['errors'])}")

    # Verify in graph
    print("\n4. Verifying in graph...")
    result = graph.query("""
        MATCH (n:Norma {tipo_documento: 'atto_modificante'})
        RETURN count(n) as c
    """)
    atti_count = result.result_set[0][0] if result.result_set else 0
    print(f"   Atti modificanti nel grafo: {atti_count}")

    for rel_type in ['modifica', 'inserisce', 'abroga', 'sostituisce']:
        result = graph.query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
        count = result.result_set[0][0] if result.result_set else 0
        print(f"   :{rel_type}: {count}")

    # Save stats
    stats_path = Path("docs/experiments/EXP-006_libro_primo_cp/multivigenza_stats.json")
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "stats": stats
        }, f, indent=2, ensure_ascii=False)
    print(f"\n   Stats saved to: {stats_path}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
