#!/usr/bin/env python3
"""
EXP-006: Ingest Libro Primo Codice Penale
==========================================

Ingestion completa del Libro Primo del Codice Penale (Art. 1-240, ~263 articoli)
con multivigenza ed enrichment da Brocardi.

Pipeline:
1. Load articoli da ground truth JSON
2. Clear grafo test
3. Create nodo CP (codice)
4. Per ogni articolo:
   a. Fetch testo da Normattiva
   b. Fetch enrichment da Brocardi (massime, spiegazione)
   c. Create nodo articolo nel grafo
   d. Apply multivigenza
5. Genera report metriche

Usage:
    python scripts/ingest_libro_primo_cp.py

    # Limita a N articoli (per test)
    python scripts/ingest_libro_primo_cp.py --limit 10

    # Salta multivigenza
    python scripts/ingest_libro_primo_cp.py --skip-multivigenza

    # Salta Brocardi enrichment
    python scripts/ingest_libro_primo_cp.py --skip-brocardi

    # Dry run
    python scripts/ingest_libro_primo_cp.py --dry-run
"""

import asyncio
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from falkordb import FalkorDB

# Imports locali
import sys
sys.path.insert(0, '.')

import aiohttp
from merlt.external_sources.visualex.tools.norma import NormaVisitata, Norma
from merlt.external_sources.visualex.scrapers.normattiva_scraper import NormattivaScraper
from merlt.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from merlt.preprocessing.multivigenza_pipeline import MultivigenzaPipeline
from merlt.storage import FalkorDBClient, FalkorDBConfig


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds, exponential backoff


async def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    """Execute async function with exponential backoff retry."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (BrokenPipeError, ConnectionError, aiohttp.ClientError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = RETRY_DELAY_BASE * (2 ** attempt)
                await asyncio.sleep(delay)
            continue
    raise last_error


# Configurazione
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380
GRAPH_NAME = "merl_t_test"

# Codice Penale - usa tipo_atto 'codice penale' per URN con allegato corretto
# URN risultante: regio.decreto:1930-10-19;1398:1 (allegato 1 = Codice Penale)
CP_TIPO_ATTO = "codice penale"  # Questo genera l'URN corretto con :1
CP_DATA = None  # Non servono per 'codice penale'
CP_NUMERO = None

# Paths
GROUND_TRUTH_PATH = Path("docs/experiments/EXP-006_libro_primo_cp/ground_truth.json")
METRICS_PATH = Path("docs/experiments/EXP-006_libro_primo_cp/ingestion_metrics.json")

# Rate limiting (increased for stability)
DELAY_BETWEEN_ARTICLES = 1.0  # seconds
BATCH_SIZE = 10  # articles per batch
DELAY_BETWEEN_BATCHES = 5  # seconds


@dataclass
class IngestionMetrics:
    """Track ingestion metrics."""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    total_articles: int = 0
    articles_processed: int = 0
    articles_failed: int = 0
    articles_skipped: int = 0

    brocardi_fetched: int = 0
    brocardi_failed: int = 0

    modifiche_totali: int = 0
    atti_modificanti_creati: int = 0
    relazioni_create: int = 0

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
                "skipped": self.articles_skipped,
                "success_rate": f"{self.articles_processed / max(1, self.total_articles) * 100:.1f}%",
            },
            "brocardi": {
                "fetched": self.brocardi_fetched,
                "failed": self.brocardi_failed,
            },
            "multivigenza": {
                "modifiche_totali": self.modifiche_totali,
                "atti_modificanti": self.atti_modificanti_creati,
                "relazioni": self.relazioni_create,
            },
            "errors": self.errors[:20],  # Limit to first 20 errors
        }


def load_ground_truth() -> List[Dict[str, Any]]:
    """Load articles from ground truth JSON."""
    with open(GROUND_TRUTH_PATH) as f:
        data = json.load(f)
    return data.get("articles", [])


async def clear_graph():
    """Clear all data from test graph."""
    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = fb.select_graph(GRAPH_NAME)

    result = graph.query("MATCH (n) RETURN count(n) as c")
    count = result.result_set[0][0] if result.result_set else 0

    if count > 0:
        graph.query("MATCH (n) DETACH DELETE n")
        print(f"   Deleted {count} nodes from {GRAPH_NAME}")
    else:
        print(f"   Graph {GRAPH_NAME} already empty")


async def create_cp_node(client: FalkorDBClient, timestamp: str) -> str:
    """Create main node for Codice Penale."""
    # URN per il Codice Penale (allegato :1 del R.D. 1398/1930)
    urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1930-10-19;1398:1"

    await client.query(
        """
        MERGE (cp:Norma {URN: $urn})
        ON CREATE SET
            cp.node_id = $urn,
            cp.tipo_documento = 'codice',
            cp.titolo = 'Codice Penale',
            cp.tipo_atto = 'codice penale',
            cp.data_pubblicazione = '1930-10-19',
            cp.numero_atto = '1398',
            cp.fonte = 'Normattiva',
            cp.created_at = $timestamp
        """,
        {"urn": urn, "timestamp": timestamp}
    )
    return urn


async def _fetch_article_impl(scraper: NormattivaScraper, nv: NormaVisitata):
    """Internal implementation for fetching article."""
    return await scraper.get_document(nv)


async def fetch_article_text(
    scraper: NormattivaScraper,
    numero_articolo: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch article text from Normattiva with retry.

    Returns:
        Tuple (testo, urn) or (None, None) on failure
    """
    # Normalize article number (remove spaces, handle bis/ter)
    numero_norm = numero_articolo.replace(' ', '-')

    # Usa 'codice penale' per generare URN corretto con allegato :1
    norma = Norma(tipo_atto='codice penale', data=None, numero_atto=None)
    nv = NormaVisitata(norma=norma, numero_articolo=numero_norm)

    try:
        testo, urn = await retry_with_backoff(_fetch_article_impl, scraper, nv)
        return testo, urn
    except Exception as e:
        return None, None


async def _fetch_brocardi_impl(scraper: BrocardiScraper, nv: NormaVisitata):
    """Internal implementation for fetching Brocardi info."""
    result = await scraper.do_know(nv)
    if not result:
        return None
    return await scraper.get_info(nv)


async def fetch_brocardi_enrichment(
    scraper: BrocardiScraper,
    numero_articolo: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetch enrichment from Brocardi (massime, spiegazione, ratio) with retry.

    Returns:
        Dict with enrichment data or None
    """
    norma = Norma(tipo_atto='codice penale', data=None, numero_atto=None)
    # Normalize article number
    numero_norm = numero_articolo.replace(' ', '-')
    nv = NormaVisitata(norma=norma, numero_articolo=numero_norm)

    try:
        result = await retry_with_backoff(_fetch_brocardi_impl, scraper, nv)
        if result is None:
            return None

        testo, info, url = result
        if info:
            return {
                "brocardi_url": url,
                "spiegazione": info.get("Spiegazione", ""),
                "ratio": info.get("Ratio", ""),
                "massime": info.get("Massime", []),
                "position": info.get("Position", ""),
            }
        return None
    except Exception:
        return None


async def create_article_node(
    client: FalkorDBClient,
    numero_articolo: str,
    testo: str,
    urn: str,
    position: str,
    brocardi_data: Optional[Dict[str, Any]],
    timestamp: str,
) -> None:
    """Create article node in graph."""
    params = {
        "urn": urn,
        "numero": numero_articolo,
        "testo": testo,
        "position": position,
        "timestamp": timestamp,
    }

    # Base query
    query = """
        MERGE (art:Norma {URN: $urn})
        ON CREATE SET
            art.node_id = $urn,
            art.tipo_documento = 'articolo',
            art.numero_articolo = $numero,
            art.testo_vigente = $testo,
            art.position = $position,
            art.fonte = 'Normattiva',
            art.created_at = $timestamp
    """

    # Add Brocardi enrichment if available
    if brocardi_data:
        params["brocardi_url"] = brocardi_data.get("brocardi_url", "")
        params["spiegazione"] = brocardi_data.get("spiegazione", "")[:5000]  # Limit size
        params["ratio"] = brocardi_data.get("ratio", "")[:2000]
        params["n_massime"] = len(brocardi_data.get("massime", []))

        query += """
            , art.brocardi_url = $brocardi_url
            , art.spiegazione = $spiegazione
            , art.ratio = $ratio
            , art.n_massime = $n_massime
        """

    await client.query(query, params)


async def link_article_to_cp(
    client: FalkorDBClient,
    article_urn: str,
    cp_urn: str,
) -> None:
    """Create :contiene relation between CP and article."""
    await client.query(
        """
        MATCH (cp:Norma {URN: $cp_urn})
        MATCH (art:Norma {URN: $art_urn})
        MERGE (cp)-[r:contiene]->(art)
        ON CREATE SET r.certezza = 1.0
        """,
        {"cp_urn": cp_urn, "art_urn": article_urn}
    )


async def process_article(
    article: Dict[str, Any],
    normattiva_scraper: NormattivaScraper,
    brocardi_scraper: BrocardiScraper,
    client: FalkorDBClient,
    multivigenza_pipeline: Optional[MultivigenzaPipeline],
    cp_urn: str,
    timestamp: str,
    skip_brocardi: bool = False,
    skip_multivigenza: bool = False,
) -> Dict[str, Any]:
    """
    Process a single article through the full pipeline.

    Returns:
        Dict with processing results
    """
    numero = article['number']
    position = article.get('position', '')

    result = {
        "numero": numero,
        "success": False,
        "brocardi_ok": False,
        "n_modifiche": 0,
        "n_atti": 0,
        "n_relazioni": 0,
        "error": None,
    }

    try:
        # 1. Fetch text from Normattiva
        testo, urn = await fetch_article_text(normattiva_scraper, numero)
        if not testo or not urn:
            result["error"] = "Failed to fetch from Normattiva"
            return result

        # 2. Fetch Brocardi enrichment (optional)
        brocardi_data = None
        if not skip_brocardi:
            brocardi_data = await fetch_brocardi_enrichment(brocardi_scraper, numero)
            result["brocardi_ok"] = brocardi_data is not None

        # 3. Create article node
        await create_article_node(
            client, numero, testo, urn, position, brocardi_data, timestamp
        )

        # 4. Link to CP
        await link_article_to_cp(client, urn, cp_urn)

        # 5. Apply multivigenza (optional)
        if not skip_multivigenza and multivigenza_pipeline:
            numero_norm = numero.replace(' ', '-')
            norma = Norma(tipo_atto=CP_TIPO_ATTO, data=CP_DATA, numero_atto=CP_NUMERO)
            nv = NormaVisitata(norma=norma, numero_articolo=numero_norm)

            try:
                mv_result = await multivigenza_pipeline.ingest_with_history(
                    nv,
                    fetch_all_versions=False,
                    create_modifying_acts=True,
                )
                result["n_modifiche"] = len(mv_result.storia.modifiche) if mv_result.storia else 0
                result["n_atti"] = len(mv_result.atti_modificanti_creati)
                result["n_relazioni"] = len(mv_result.relazioni_create)
            except Exception as e:
                # Non-fatal: article created but multivigenza failed
                result["error"] = f"Multivigenza failed: {str(e)[:100]}"

        result["success"] = True
        return result

    except Exception as e:
        result["error"] = str(e)[:200]
        return result


async def run_validation_queries(client: FalkorDBClient) -> Dict[str, Any]:
    """Run validation queries and return metrics."""
    metrics = {}

    # Node counts
    result = await client.query("MATCH (n:Norma) RETURN count(n) as c")
    metrics['total_nodes'] = result[0]['c'] if result else 0

    result = await client.query(
        "MATCH (n:Norma {tipo_documento: 'articolo'}) RETURN count(n) as c"
    )
    metrics['article_nodes'] = result[0]['c'] if result else 0

    result = await client.query(
        "MATCH (n:Norma {tipo_documento: 'atto_modificante'}) RETURN count(n) as c"
    )
    metrics['modifying_act_nodes'] = result[0]['c'] if result else 0

    # Relation counts
    for rel_type in ['modifica', 'inserisce', 'abroga', 'sostituisce', 'contiene']:
        result = await client.query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
        metrics[f'rel_{rel_type}'] = result[0]['c'] if result else 0

    # Articles with Brocardi enrichment
    result = await client.query("""
        MATCH (art:Norma {tipo_documento: 'articolo'})
        WHERE art.brocardi_url IS NOT NULL
        RETURN count(art) as c
    """)
    metrics['articles_with_brocardi'] = result[0]['c'] if result else 0

    return metrics


async def main():
    parser = argparse.ArgumentParser(description="EXP-006: Ingest Libro Primo Codice Penale")
    parser.add_argument("--limit", type=int, default=None, help="Limit to N articles")
    parser.add_argument("--skip-multivigenza", action="store_true", help="Skip multivigenza")
    parser.add_argument("--skip-brocardi", action="store_true", help="Skip Brocardi enrichment")
    parser.add_argument("--skip-clear", action="store_true", help="Don't clear existing data")
    parser.add_argument("--start-from", type=int, default=0, help="Start from article index (for resume)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("=" * 70)
    print("EXP-006: INGEST LIBRO PRIMO CODICE PENALE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Graph: {GRAPH_NAME}")
    print(f"Options: limit={args.limit}, skip_mv={args.skip_multivigenza}, skip_brocardi={args.skip_brocardi}")

    # Load ground truth
    print("\n1. Loading ground truth...")
    articles = load_ground_truth()
    if args.limit:
        articles = articles[:args.limit]

    # Handle start-from for resume
    if args.start_from > 0:
        articles = articles[args.start_from:]
        print(f"   Resuming from index {args.start_from}")

    print(f"   Loaded {len(articles)} articles to process")

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***")
        print(f"\nWould process {len(articles)} articles")
        print("First 5 articles:")
        for art in articles[:5]:
            print(f"  - Art. {art['number']}")
        return

    # Initialize metrics
    metrics = IngestionMetrics()
    metrics.start_time = datetime.now().isoformat()
    metrics.total_articles = len(articles)

    # Clear graph
    print("\n2. Preparing graph...")
    if not args.skip_clear:
        await clear_graph()
    else:
        print("   Skipping clear (--skip-clear)")

    # Connect to services
    print("\n3. Connecting to services...")
    config = FalkorDBConfig(
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        graph_name=GRAPH_NAME,
    )
    client = FalkorDBClient(config)
    await client.connect()
    print(f"   FalkorDB: {GRAPH_NAME}")

    normattiva_scraper = NormattivaScraper()
    print("   NormattivaScraper ready")

    brocardi_scraper = BrocardiScraper() if not args.skip_brocardi else None
    if brocardi_scraper:
        print("   BrocardiScraper ready")

    multivigenza_pipeline = None
    if not args.skip_multivigenza:
        multivigenza_pipeline = MultivigenzaPipeline(
            falkordb_client=client,
            scraper=normattiva_scraper
        )
        print("   MultivigenzaPipeline ready")

    # Create CP node
    print("\n4. Creating Codice Penale node...")
    timestamp = datetime.now().isoformat()
    cp_urn = await create_cp_node(client, timestamp)
    print(f"   Created: {cp_urn}")

    # Process articles
    print(f"\n5. Processing {len(articles)} articles...")
    print("   (this may take several minutes)")

    start_time = time.time()

    for i, article in enumerate(articles):
        numero = article['number']

        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(articles) - i - 1) / rate if rate > 0 else 0
            print(f"   [{i+1}/{len(articles)}] Art. {numero} - {rate:.1f} art/s, ETA: {eta:.0f}s")

        # Process article
        result = await process_article(
            article,
            normattiva_scraper,
            brocardi_scraper,
            client,
            multivigenza_pipeline,
            cp_urn,
            timestamp,
            skip_brocardi=args.skip_brocardi,
            skip_multivigenza=args.skip_multivigenza,
        )

        # Update metrics
        if result["success"]:
            metrics.articles_processed += 1
            if result["brocardi_ok"]:
                metrics.brocardi_fetched += 1
            metrics.modifiche_totali += result["n_modifiche"]
            metrics.atti_modificanti_creati += result["n_atti"]
            metrics.relazioni_create += result["n_relazioni"]
        else:
            metrics.articles_failed += 1
            metrics.errors.append({
                "article": numero,
                "error": result.get("error", "Unknown error")
            })

        # Rate limiting
        await asyncio.sleep(DELAY_BETWEEN_ARTICLES)

        # Batch delay
        if (i + 1) % BATCH_SIZE == 0:
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    # Finalize metrics
    metrics.end_time = datetime.now().isoformat()
    metrics.duration_seconds = time.time() - start_time

    # Validation
    print("\n6. Running validation queries...")
    validation = await run_validation_queries(client)

    print(f"\n   Nodes:")
    print(f"     - Total: {validation['total_nodes']}")
    print(f"     - Articles: {validation['article_nodes']}")
    print(f"     - Modifying acts: {validation['modifying_act_nodes']}")
    print(f"     - With Brocardi: {validation['articles_with_brocardi']}")

    print(f"\n   Relations:")
    print(f"     - :contiene: {validation['rel_contiene']}")
    print(f"     - :modifica: {validation['rel_modifica']}")
    print(f"     - :inserisce: {validation['rel_inserisce']}")
    print(f"     - :abroga: {validation['rel_abroga']}")

    # Save metrics
    print("\n7. Saving metrics...")
    metrics_data = {
        "experiment": "EXP-006",
        "description": "Libro Primo Codice Penale Ingestion",
        "config": {
            "graph": GRAPH_NAME,
            "limit": args.limit,
            "skip_multivigenza": args.skip_multivigenza,
            "skip_brocardi": args.skip_brocardi,
        },
        "metrics": metrics.to_dict(),
        "validation": validation,
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=2, ensure_ascii=False)
    print(f"   Saved to: {METRICS_PATH}")

    # Cleanup
    await client.close()

    # Summary
    print("\n" + "=" * 70)
    print("EXP-006 INGESTION COMPLETED")
    print("=" * 70)
    print(f"\nDuration: {metrics.duration_seconds:.1f} seconds")
    print(f"Articles: {metrics.articles_processed}/{metrics.total_articles} ({metrics.articles_failed} failed)")
    print(f"Brocardi: {metrics.brocardi_fetched} enriched")
    print(f"Multivigenza: {metrics.modifiche_totali} modifiche, {metrics.atti_modificanti_creati} atti")
    print(f"\nGraph: {GRAPH_NAME}")
    print(f"Metrics: {METRICS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
