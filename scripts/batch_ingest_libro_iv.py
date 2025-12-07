#!/usr/bin/env python3
"""
Batch Ingestion - Libro IV Codice Civile
=========================================

EXP-001: Ingestion 887 articoli (Art. 1173-2059)

Features:
- MERGE per collision-resistance (idempotente)
- Incremental enrichment (ON CREATE/ON MATCH)
- Progress tracking e error recovery
- Rate limiting per Normattiva

Usage:
    python scripts/batch_ingest_libro_iv.py [--start N] [--end M] [--dry-run]

Example:
    python scripts/batch_ingest_libro_iv.py --start 1173 --end 1200  # Test batch
    python scripts/batch_ingest_libro_iv.py  # Full ingestion
"""

import asyncio
import argparse
import logging
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.storage.falkordb import FalkorDBClient, FalkorDBConfig
from merlt.storage.bridge import BridgeTable, BridgeTableConfig, BridgeBuilder
from merlt.preprocessing.ingestion_pipeline_v2 import IngestionPipelineV2, IngestionResult
from merlt.preprocessing.visualex_ingestion import VisualexArticle, NormaMetadata
from merlt.external_sources.visualex.scrapers.normattiva_scraper import NormattivaScraper
from merlt.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from merlt.external_sources.visualex.tools.norma import Norma, NormaVisitata
from merlt.external_sources.visualex.tools import urngenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/ingestion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics for the ingestion process."""
    start_time: str
    end_time: Optional[str] = None
    articles_attempted: int = 0
    articles_success: int = 0
    articles_failed: int = 0
    articles_skipped: int = 0
    chunks_created: int = 0
    nodes_created: int = 0
    relations_created: int = 0
    bridge_mappings: int = 0
    brocardi_enriched: int = 0
    errors: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def add_error(self, article_num: str, error: str):
        self.errors.append({
            "article": article_num,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BatchIngestionRunner:
    """
    Runner for batch ingestion of Libro IV articles.

    Collision-resistant design:
    - Uses MERGE for all node creation (idempotent)
    - ON CREATE SET: initial properties
    - ON MATCH SET: update timestamps, enrichment
    - URN as primary key (guaranteed unique)

    Incremental enrichment support:
    - Re-running adds missing properties without overwriting existing
    - Future LLM enrichment: add ConcettoGiuridico via MERGE
    - Manual doctrine: add Dottrina nodes linking to existing Norma
    - Bridge Table: supports multiple mappings per chunk (additivo)

    Example future enrichment:
        # LLM concept extraction
        MATCH (art:Norma {URN: $urn})
        MERGE (c:ConcettoGiuridico {node_id: $concept_id})
        ON CREATE SET c.denominazione = $name, c.fonte = 'llm_extraction'
        MERGE (art)-[:disciplina]->(c)

        # Manual doctrine
        MERGE (d:Dottrina {node_id: $dottrina_id})
        ON CREATE SET d.titolo = $title, d.autore = $author, d.fonte = 'manuale'
        MATCH (art:Norma {URN: $article_urn})
        MERGE (d)-[:commenta]->(art)
    """

    # Libro IV articles range
    LIBRO_IV_START = 1173
    LIBRO_IV_END = 2059

    # Rate limiting
    NORMATTIVA_DELAY = 1.0  # seconds between requests
    BROCARDI_DELAY = 0.5

    # Batch settings
    PROGRESS_LOG_INTERVAL = 10  # Log every N articles
    BRIDGE_BATCH_SIZE = 50

    def __init__(
        self,
        falkordb_client: FalkorDBClient,
        bridge_table: BridgeTable,
        dry_run: bool = False
    ):
        self.falkordb = falkordb_client
        self.bridge = bridge_table
        self.dry_run = dry_run

        # Initialize scrapers
        self.normattiva_scraper = NormattivaScraper()
        self.brocardi_scraper = BrocardiScraper()

        # Initialize pipeline (without falkordb if dry_run)
        self.pipeline = IngestionPipelineV2(
            falkordb_client=None if dry_run else falkordb_client
        )

        # Initialize bridge builder
        self.bridge_builder = BridgeBuilder(bridge_table) if not dry_run else None

        # Stats
        self.stats = IngestionStats(start_time=datetime.now().isoformat())

        # Codice Civile base info
        self.codice_info = {
            "tipo_atto": "codice civile",
            "data": "1942-03-16",
            "numero_atto": "262",
            "allegato": "2"  # Allegato 2 del R.D. 262/1942
        }

        logger.info(f"BatchIngestionRunner initialized (dry_run={dry_run})")

    async def ensure_hierarchy_nodes(self) -> Tuple[str, str, str]:
        """
        Ensure Codice, Libro IV, and hierarchy nodes exist.
        Uses MERGE for idempotency.

        Returns:
            (codice_urn, libro_urn, None) - titolo created per-article
        """
        # Generate Codice URN
        codice_urn = urngenerator.generate_urn(
            act_type=self.codice_info["tipo_atto"],
            date=self.codice_info["data"],
            act_number=self.codice_info["numero_atto"],
            article=None,
            urn_flag=True
        )

        if not self.dry_run:
            timestamp = datetime.now().isoformat()

            # MERGE Codice Civile root
            await self.falkordb.query("""
                MERGE (codice:Norma {URN: $urn})
                ON CREATE SET
                    codice.node_id = $urn,
                    codice.tipo_documento = 'codice',
                    codice.denominazione = 'Codice Civile',
                    codice.estremi = 'R.D. 16 marzo 1942, n. 262',
                    codice.data_pubblicazione = '1942-03-16',
                    codice.stato = 'vigente',
                    codice.fonte = 'normattiva',
                    codice.created_at = $timestamp
                ON MATCH SET
                    codice.updated_at = $timestamp
            """, {"urn": codice_urn, "timestamp": timestamp})

            # MERGE Libro IV
            libro_urn = f"{codice_urn}~libro4"
            await self.falkordb.query("""
                MERGE (libro:Norma {URN: $urn})
                ON CREATE SET
                    libro.node_id = $urn,
                    libro.tipo_documento = 'libro',
                    libro.denominazione = 'Libro IV - Delle obbligazioni',
                    libro.numero_libro = 4,
                    libro.created_at = $timestamp
                ON MATCH SET
                    libro.updated_at = $timestamp
            """, {"urn": libro_urn, "timestamp": timestamp})

            # MERGE Codice -> Libro relation
            await self.falkordb.query("""
                MATCH (codice:Norma {URN: $codice_urn})
                MATCH (libro:Norma {URN: $libro_urn})
                MERGE (codice)-[r:contiene]->(libro)
                ON CREATE SET r.certezza = 'esplicita'
            """, {"codice_urn": codice_urn, "libro_urn": libro_urn})

            logger.info(f"Hierarchy nodes ensured: Codice + Libro IV")
        else:
            libro_urn = f"{codice_urn}~libro4"
            logger.info(f"[DRY RUN] Would create hierarchy: {codice_urn[:50]}...")

        return codice_urn, libro_urn, None

    async def fetch_article_data(self, article_num: str) -> Optional[VisualexArticle]:
        """
        Fetch article from Normattiva + Brocardi.

        Returns:
            VisualexArticle or None if failed
        """
        try:
            # Create Norma object for scrapers
            norma = Norma(
                tipo_atto=self.codice_info["tipo_atto"],
                data=self.codice_info["data"],
                numero_atto=self.codice_info["numero_atto"]
            )

            # Note: allegato is already included in codici_urn map (map.py)
            # Don't pass it again or it gets duplicated (:2:2~art...)
            norma_visitata = NormaVisitata(
                norma=norma,
                numero_articolo=article_num,
                allegato=None  # Already in codici_urn as `:2`
            )

            # Fetch from Normattiva
            article_text, urn = await self.normattiva_scraper.get_document(norma_visitata)
            await asyncio.sleep(self.NORMATTIVA_DELAY)  # Rate limit

            if not article_text or "not found" in article_text.lower():
                logger.warning(f"Article {article_num} not found on Normattiva")
                return None

            # Fetch Brocardi info (optional enrichment)
            brocardi_info = None
            try:
                _, brocardi_data, _ = await self.brocardi_scraper.get_info(norma_visitata)
                if brocardi_data:
                    brocardi_info = brocardi_data
                    logger.debug(f"Art. {article_num}: Brocardi enrichment found")
                await asyncio.sleep(self.BROCARDI_DELAY)
            except Exception as e:
                logger.debug(f"Art. {article_num}: No Brocardi data ({e})")

            # Create metadata
            metadata = NormaMetadata(
                tipo_atto=self.codice_info["tipo_atto"],
                data=self.codice_info["data"],
                numero_atto=self.codice_info["numero_atto"],
                numero_articolo=article_num,
                allegato=self.codice_info["allegato"]
            )

            return VisualexArticle(
                metadata=metadata,
                article_text=article_text,
                url=urn,
                brocardi_info=brocardi_info
            )

        except Exception as e:
            logger.error(f"Error fetching article {article_num}: {e}")
            self.stats.add_error(article_num, str(e))
            return None

    async def ingest_article(
        self,
        article: VisualexArticle,
        codice_urn: str
    ) -> Optional[IngestionResult]:
        """
        Ingest a single article using the v2 pipeline.

        Returns:
            IngestionResult or None if failed
        """
        try:
            # Run pipeline (creates graph nodes if not dry_run)
            result = await self.pipeline.ingest_article(
                article=article,
                create_graph_nodes=not self.dry_run
            )

            # Insert bridge mappings
            if not self.dry_run and result.bridge_mappings:
                inserted = await self.bridge_builder.insert_mappings(
                    result.bridge_mappings,
                    batch_size=self.BRIDGE_BATCH_SIZE
                )
                self.stats.bridge_mappings += inserted

            # Update stats
            self.stats.chunks_created += len(result.chunks)
            self.stats.nodes_created += len(result.nodes_created)
            self.stats.relations_created += len(result.relations_created)
            if result.brocardi_enriched:
                self.stats.brocardi_enriched += 1

            return result

        except Exception as e:
            logger.error(f"Error ingesting article {article.metadata.numero_articolo}: {e}")
            self.stats.add_error(article.metadata.numero_articolo, str(e))
            return None

    async def run(
        self,
        start_article: int = None,
        end_article: int = None
    ) -> IngestionStats:
        """
        Run batch ingestion.

        Args:
            start_article: First article number (default: 1173)
            end_article: Last article number (default: 2059)

        Returns:
            IngestionStats with results
        """
        start = start_article or self.LIBRO_IV_START
        end = end_article or self.LIBRO_IV_END

        logger.info(f"Starting batch ingestion: Art. {start} - Art. {end}")
        logger.info(f"Dry run: {self.dry_run}")

        # Ensure hierarchy
        codice_urn, libro_urn, _ = await self.ensure_hierarchy_nodes()

        # Generate article list
        # Note: Some articles may be missing (abrogated, etc.)
        articles_to_process = list(range(start, end + 1))
        total = len(articles_to_process)

        logger.info(f"Processing {total} potential articles")

        # Process articles
        for i, art_num in enumerate(articles_to_process, 1):
            art_str = str(art_num)
            self.stats.articles_attempted += 1

            # Progress log
            if i % self.PROGRESS_LOG_INTERVAL == 0:
                logger.info(
                    f"Progress: {i}/{total} ({100*i/total:.1f}%) - "
                    f"Success: {self.stats.articles_success}, "
                    f"Failed: {self.stats.articles_failed}, "
                    f"Skipped: {self.stats.articles_skipped}"
                )

            # Fetch article
            article = await self.fetch_article_data(art_str)

            if article is None:
                self.stats.articles_skipped += 1
                continue

            # Ingest
            result = await self.ingest_article(article, codice_urn)

            if result:
                self.stats.articles_success += 1
                logger.debug(
                    f"Art. {art_str}: {len(result.chunks)} chunks, "
                    f"{len(result.nodes_created)} nodes, "
                    f"brocardi={result.brocardi_enriched}"
                )
            else:
                self.stats.articles_failed += 1

        # Finalize
        self.stats.end_time = datetime.now().isoformat()

        # Log summary
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Articles attempted: {self.stats.articles_attempted}")
        logger.info(f"Articles success: {self.stats.articles_success}")
        logger.info(f"Articles failed: {self.stats.articles_failed}")
        logger.info(f"Articles skipped: {self.stats.articles_skipped}")
        logger.info(f"Chunks created: {self.stats.chunks_created}")
        logger.info(f"Nodes created: {self.stats.nodes_created}")
        logger.info(f"Relations created: {self.stats.relations_created}")
        logger.info(f"Bridge mappings: {self.stats.bridge_mappings}")
        logger.info(f"Brocardi enriched: {self.stats.brocardi_enriched}")
        logger.info(f"Errors: {len(self.stats.errors)}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description="Batch ingestion Libro IV")
    parser.add_argument("--start", type=int, default=1173, help="Start article")
    parser.add_argument("--end", type=int, default=2059, help="End article")
    parser.add_argument("--dry-run", action="store_true", help="No database writes")
    parser.add_argument("--output", type=str, default="logs/ingestion_stats.json", help="Stats output file")
    args = parser.parse_args()

    # Ensure logs directory
    Path("logs").mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("EXP-001: Batch Ingestion Libro IV")
    logger.info("=" * 60)

    # Initialize connections
    falkordb_config = FalkorDBConfig(
        host="localhost",
        port=6380,
        graph_name="merl_t_legal"
    )
    falkordb = FalkorDBClient(falkordb_config)
    await falkordb.connect()
    logger.info("Connected to FalkorDB")

    bridge_config = BridgeTableConfig(
        host="localhost",
        port=5433,
        database="rlcf_dev",
        user="dev",
        password="devpassword"
    )
    bridge = BridgeTable(bridge_config)
    await bridge.connect()
    logger.info("Connected to Bridge Table")

    try:
        # Run ingestion
        runner = BatchIngestionRunner(
            falkordb_client=falkordb,
            bridge_table=bridge,
            dry_run=args.dry_run
        )

        stats = await runner.run(
            start_article=args.start,
            end_article=args.end
        )

        # Save stats
        with open(args.output, 'w') as f:
            json.dump(stats.to_dict(), f, indent=2, default=str)
        logger.info(f"Stats saved to {args.output}")

    finally:
        await falkordb.close()
        await bridge.close()
        logger.info("Connections closed")


if __name__ == "__main__":
    asyncio.run(main())
