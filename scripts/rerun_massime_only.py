#!/usr/bin/env python3
"""
Re-Run Massime Only - Clean AttoGiudiziario Nodes
=================================================

Script per rifare SOLO i nodi AttoGiudiziario senza toccare Norma e Dottrina.
Utilizza il BrocardiScraper fixato con parsing strutturato delle massime.

Steps:
1. Delete existing AttoGiudiziario nodes (with dirty data)
2. Delete :interpreta relations
3. Re-scrape massime from Brocardi using fixed scraper
4. Create new AttoGiudiziario nodes with clean data

Usage:
    python scripts/rerun_massime_only.py [--start N] [--end M] [--dry-run]

Example:
    python scripts/rerun_massime_only.py --start 1453 --end 1456  # Test batch
    python scripts/rerun_massime_only.py  # Full re-run
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.storage.falkordb import FalkorDBClient, FalkorDBConfig
from merlt.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from merlt.external_sources.visualex.tools.norma import Norma, NormaVisitata

# Configure logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/rerun_massime_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class MassimeRerunner:
    """Re-runs massime ingestion only, keeping Norma and Dottrina intact."""

    LIBRO_IV_START = 1173
    LIBRO_IV_END = 2059

    # Rate limiting
    BROCARDI_DELAY = 1.5
    BATCH_PAUSE_INTERVAL = 50
    BATCH_PAUSE_SECONDS = 30
    PROGRESS_LOG_INTERVAL = 10

    def __init__(self, falkordb_client: FalkorDBClient, dry_run: bool = False):
        self.falkordb = falkordb_client
        self.dry_run = dry_run
        self.scraper = BrocardiScraper()

        # Stats
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "deleted_nodes": 0,
            "deleted_relations": 0,
            "articles_processed": 0,
            "massime_created": 0,
            "errors": []
        }

        # Codice Civile info
        self.codice_info = {
            "tipo_atto": "codice civile",
            "data": "1942-03-16",
            "numero_atto": "262"
        }

    def _build_urn_from_article(self, article_num: str) -> str:
        return f"https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art{article_num}"

    def _build_norma_visitata(self, article_num: str) -> NormaVisitata:
        norma = Norma(
            tipo_atto=self.codice_info["tipo_atto"],
            data=self.codice_info["data"],
            numero_atto=self.codice_info["numero_atto"]
        )
        return NormaVisitata(
            norma=norma,
            numero_articolo=article_num,
            allegato=None
        )

    async def cleanup_existing(self) -> tuple[int, int]:
        """Delete all existing AttoGiudiziario nodes and :interpreta relations."""

        if self.dry_run:
            logger.info("[DRY RUN] Would delete AttoGiudiziario nodes and :interpreta relations")
            return 0, 0

        # Count before deletion
        count_result = await self.falkordb.query(
            "MATCH (a:AttoGiudiziario) RETURN count(a) as cnt"
        )
        existing_nodes = count_result[0]['cnt'] if count_result else 0

        rel_result = await self.falkordb.query(
            "MATCH ()-[r:interpreta]->() RETURN count(r) as cnt"
        )
        existing_rels = rel_result[0]['cnt'] if rel_result else 0

        logger.info(f"Found {existing_nodes} AttoGiudiziario nodes to delete")
        logger.info(f"Found {existing_rels} :interpreta relations to delete")

        # Delete relations first
        await self.falkordb.query("MATCH ()-[r:interpreta]->() DELETE r")

        # Delete nodes
        await self.falkordb.query("MATCH (a:AttoGiudiziario) DELETE a")

        logger.info("Cleanup completed")
        return existing_nodes, existing_rels

    def _parse_massima_dict(self, massima: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse massima from new BrocardiScraper format."""
        autorita = massima.get("autorita", "")
        numero = massima.get("numero", "")
        anno = massima.get("anno", "")
        testo = massima.get("massima", "")

        if not testo:
            return None

        # Determine materia from autorita
        materia = "Diritto civile"
        materia_code = "civ"
        if autorita:
            autorita_lower = autorita.lower()
            if "pen" in autorita_lower:
                materia = "Diritto penale"
                materia_code = "pen"
            elif "lav" in autorita_lower:
                materia = "Diritto del lavoro"
                materia_code = "lav"

        # Generate unique node_id
        node_id = f"atto:cass:{materia_code}:{numero}:{anno}" if numero and anno else f"atto:generic:{hash(testo) % 1000000}"

        # Estremi
        if numero and anno:
            estremi = f"{autorita} n. {numero}/{anno}".strip()
        else:
            estremi = autorita or "Giurisprudenza"

        return {
            "node_id": node_id,
            "estremi": estremi,
            "descrizione": testo[:500] if len(testo) > 500 else testo,
            "organo_emittente": "Corte di Cassazione" if autorita and "cass" in autorita.lower() else "Giurisprudenza",
            "data": anno,
            "numero": numero,
            "anno": anno,
            "tipologia": "sentenza",
            "materia": materia,
            "massima_text": testo
        }

    async def create_massime_for_article(
        self,
        norma_urn: str,
        article_num: str,
        massime: List[Dict[str, Any]]
    ) -> int:
        """Create AttoGiudiziario nodes for massime list."""

        if self.dry_run:
            return len(massime)

        count = 0
        timestamp = datetime.now().isoformat()

        for massima in massime:
            # Handle both dict (new format) and string (old format)
            if isinstance(massima, dict):
                parsed = self._parse_massima_dict(massima)
            else:
                # Skip string format - we're using new scraper
                continue

            if not parsed:
                continue

            try:
                await self.falkordb.query("""
                    MERGE (a:AttoGiudiziario {node_id: $node_id})
                    ON CREATE SET
                        a.estremi = $estremi,
                        a.descrizione = $descrizione,
                        a.organo_emittente = $organo,
                        a.tipologia = $tipologia,
                        a.materia = $materia,
                        a.data = $data,
                        a.numero_sentenza = $numero,
                        a.anno = $anno,
                        a.massima = $massima_text,
                        a.fonte = 'Brocardi.it',
                        a.created_at = $timestamp
                    WITH a
                    MATCH (n:Norma {URN: $norma_urn})
                    MERGE (a)-[r:interpreta]->(n)
                    ON CREATE SET
                        r.tipo_interpretazione = 'giurisprudenziale',
                        r.fonte_relazione = 'Brocardi.it',
                        r.certezza = 'esplicita'
                """, {
                    "node_id": parsed["node_id"],
                    "estremi": parsed["estremi"],
                    "descrizione": parsed["descrizione"],
                    "organo": parsed.get("organo_emittente", ""),
                    "tipologia": parsed.get("tipologia", "sentenza"),
                    "materia": parsed.get("materia", ""),
                    "data": parsed.get("data", ""),
                    "numero": parsed.get("numero", ""),
                    "anno": parsed.get("anno", ""),
                    "massima_text": parsed.get("massima_text", ""),
                    "norma_urn": norma_urn,
                    "timestamp": timestamp
                })
                count += 1
            except Exception as e:
                logger.warning(f"Error creating massima for {article_num}: {e}")

        return count

    async def process_article(self, article_num: str) -> int:
        """Process single article - scrape and create massime."""
        urn = self._build_urn_from_article(article_num)

        try:
            norma_visitata = self._build_norma_visitata(article_num)
            position, brocardi_info, brocardi_url = await self.scraper.get_info(norma_visitata)

            if not brocardi_info:
                return 0

            massime = brocardi_info.get("Massime", [])
            if not massime:
                return 0

            count = await self.create_massime_for_article(urn, article_num, massime)
            return count

        except Exception as e:
            logger.error(f"Error processing article {article_num}: {e}")
            self.stats["errors"].append({"article": article_num, "error": str(e)})
            return 0

    async def run(self, start_article: int = None, end_article: int = None):
        """Run the massime re-ingestion."""
        start = start_article or self.LIBRO_IV_START
        end = end_article or self.LIBRO_IV_END

        logger.info("=" * 60)
        logger.info("MASSIME RE-RUN - AttoGiudiziario Only")
        logger.info("=" * 60)
        logger.info(f"Range: Art. {start} - Art. {end}")
        logger.info(f"Dry run: {self.dry_run}")

        # Step 1: Cleanup
        logger.info("\n[Step 1/2] Cleaning up existing AttoGiudiziario nodes...")
        deleted_nodes, deleted_rels = await self.cleanup_existing()
        self.stats["deleted_nodes"] = deleted_nodes
        self.stats["deleted_relations"] = deleted_rels

        # Step 2: Re-scrape and create
        logger.info("\n[Step 2/2] Re-scraping massime from Brocardi...")
        articles = list(range(start, end + 1))
        total = len(articles)

        for i, art_num in enumerate(articles, 1):
            self.stats["articles_processed"] += 1

            # Progress
            if i % self.PROGRESS_LOG_INTERVAL == 0:
                logger.info(
                    f"Progress: {i}/{total} ({100*i/total:.1f}%) - "
                    f"Massime created: {self.stats['massime_created']}"
                )

            # Batch pause
            if i > 0 and i % self.BATCH_PAUSE_INTERVAL == 0:
                logger.info(f"Batch pause: {self.BATCH_PAUSE_SECONDS}s...")
                await asyncio.sleep(self.BATCH_PAUSE_SECONDS)

            # Process
            count = await self.process_article(str(art_num))
            self.stats["massime_created"] += count

            # Rate limiting
            await asyncio.sleep(self.BROCARDI_DELAY)

        # Summary
        self.stats["end_time"] = datetime.now().isoformat()
        logger.info("\n" + "=" * 60)
        logger.info("COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Deleted AttoGiudiziario nodes: {self.stats['deleted_nodes']}")
        logger.info(f"Deleted :interpreta relations: {self.stats['deleted_relations']}")
        logger.info(f"Articles processed: {self.stats['articles_processed']}")
        logger.info(f"Massime created: {self.stats['massime_created']}")
        logger.info(f"Errors: {len(self.stats['errors'])}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description="Re-run massime only")
    parser.add_argument("--start", type=int, default=1173, help="Start article")
    parser.add_argument("--end", type=int, default=2059, help="End article")
    parser.add_argument("--dry-run", action="store_true", help="No database writes")
    args = parser.parse_args()

    # Initialize FalkorDB
    falkordb_config = FalkorDBConfig(
        host="localhost",
        port=6380,
        graph_name="merl_t_legal"
    )
    falkordb = FalkorDBClient(falkordb_config)
    await falkordb.connect()
    logger.info("Connected to FalkorDB")

    try:
        runner = MassimeRerunner(falkordb, dry_run=args.dry_run)
        await runner.run(start_article=args.start, end_article=args.end)
    finally:
        await falkordb.close()


if __name__ == "__main__":
    asyncio.run(main())
