#!/usr/bin/env python3
"""
Batch Brocardi Enrichment - EXP-002
====================================

Arricchisce i nodi Norma esistenti con dati da Brocardi.it:
- Relazioni storiche (Guardasigilli 1941/1942)
- Ratio Legis e Spiegazione
- Massime giurisprudenziali
- Articoli citati (crea relazioni :cita)

Usage:
    python scripts/batch_enrich_brocardi.py [--start N] [--end M] [--dry-run]

Example:
    python scripts/batch_enrich_brocardi.py --start 1173 --end 1200  # Test batch
    python scripts/batch_enrich_brocardi.py  # Full enrichment
"""

import asyncio
import argparse
import logging
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.falkordb import FalkorDBClient, FalkorDBConfig
from backend.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from backend.external_sources.visualex.tools.norma import Norma, NormaVisitata

# Configure logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/enrich_brocardi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


# Regex per parsing massime (Cass. civ. n. 24819/2024)
MASSIMA_PATTERN = re.compile(
    r'^(Cass\.?\s*(civ|pen|lav)?\.?\s*(Sez\.?\s*[\w\s]+)?\s*n\.?\s*(\d+)/(\d{4}))\s*(.+)$',
    re.IGNORECASE | re.DOTALL
)


@dataclass
class EnrichmentStats:
    """Statistics for the enrichment process."""
    start_time: str
    end_time: Optional[str] = None
    articles_attempted: int = 0
    articles_enriched: int = 0
    articles_skipped: int = 0
    articles_failed: int = 0

    # Proprieta' aggiornate su Norma
    relazioni_libro: int = 0
    relazioni_codice: int = 0
    ratio_legis: int = 0

    # Nuovi nodi creati
    dottrina_created: int = 0
    atto_giudiziario_created: int = 0

    # Relazioni create
    cita_relations: int = 0
    commenta_relations: int = 0
    interpreta_relations: int = 0

    errors: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(self, article_num: str, error: str):
        self.errors.append({
            "article": article_num,
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BrocardiEnrichmentRunner:
    """
    Runner for Brocardi enrichment of existing Norma nodes.

    Mapping (da docs/experiments/EXP-002_brocardi_enrichment/MAPPING.md):

    1. Norma properties update:
       - relazione_libro_obbligazioni (Relazione 1941)
       - relazione_codice_civile (Relazione 1942)
       - ratio_legis
       - brocardi_url, brocardi_enriched_at

    2. Dottrina nodes (nuovo):
       - Spiegazione → 1 nodo Dottrina
       - Brocardi[] → N nodi Dottrina (massime latine)

    3. AttoGiudiziario nodes (nuovo):
       - Massime[] → N nodi AttoGiudiziario

    4. Relations:
       - articoli_citati → :cita (Norma→Norma)
       - Spiegazione/Brocardi → :commenta (Dottrina→Norma)
       - Massime → :interpreta (AttoGiudiziario→Norma)
    """

    LIBRO_IV_START = 1173
    LIBRO_IV_END = 2059

    # Rate limiting (Brocardi piu' conservativo)
    BROCARDI_DELAY = 1.5
    BATCH_PAUSE_INTERVAL = 50
    BATCH_PAUSE_SECONDS = 30

    PROGRESS_LOG_INTERVAL = 10

    def __init__(
        self,
        falkordb_client: FalkorDBClient,
        dry_run: bool = False
    ):
        self.falkordb = falkordb_client
        self.dry_run = dry_run

        # Initialize scraper
        self.scraper = BrocardiScraper()

        # Stats
        self.stats = EnrichmentStats(start_time=datetime.now().isoformat())

        # Codice Civile info (per costruire NormaVisitata)
        self.codice_info = {
            "tipo_atto": "codice civile",
            "data": "1942-03-16",
            "numero_atto": "262"
        }

        logger.info(f"BrocardiEnrichmentRunner initialized (dry_run={dry_run})")

    def _build_urn_from_article(self, article_num: str) -> str:
        """Costruisce URN per un articolo del Codice Civile."""
        # Formato da EXP-001 (come salvato in FalkorDB):
        # https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art{num}
        return f"https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art{article_num}"

    def _build_norma_visitata(self, article_num: str) -> NormaVisitata:
        """Costruisce NormaVisitata per lo scraper."""
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

    def _parse_massima(self, massima_text: str) -> Optional[Dict[str, Any]]:
        """
        Parsa una massima giurisprudenziale.

        Input: "Cass. civ. n. 24819/2024 L'obbligazione alternativa presuppone..."
        Output: dict con estremi, descrizione, organo, anno, numero, materia
        """
        match = MASSIMA_PATTERN.match(massima_text.strip())
        if match:
            estremi = match.group(1).strip()
            materia_raw = match.group(2) or ""
            sezione = match.group(3) or ""
            numero = match.group(4)
            anno = match.group(5)
            testo = match.group(6).strip()

            # Map materia
            materia_map = {
                "civ": "Diritto civile",
                "pen": "Diritto penale",
                "lav": "Diritto del lavoro"
            }
            materia = materia_map.get(materia_raw.lower(), "Diritto civile")

            return {
                "node_id": f"atto:cass:{materia_raw or 'civ'}:{numero}:{anno}",
                "estremi": estremi,
                "descrizione": testo[:500] if len(testo) > 500 else testo,
                "organo_emittente": "Corte di Cassazione",
                "data": anno,
                "numero": numero,
                "tipologia": "sentenza",
                "materia": materia,
                "sezione": sezione.strip() if sezione else None
            }

        # Se non matcha, crea un node_id generico
        return {
            "node_id": f"atto:generic:{hash(massima_text) % 1000000}",
            "estremi": massima_text[:50],
            "descrizione": massima_text[:500] if len(massima_text) > 500 else massima_text,
            "organo_emittente": "Giurisprudenza",
            "tipologia": "massima"
        }

    async def update_norma_properties(
        self,
        urn: str,
        brocardi_info: Dict[str, Any],
        brocardi_url: str
    ) -> bool:
        """Aggiorna le proprieta' del nodo Norma con i dati Brocardi."""

        if self.dry_run:
            logger.debug(f"[DRY RUN] Would update Norma {urn}")
            return True

        timestamp = datetime.now().isoformat()
        params = {
            "urn": urn,
            "brocardi_url": brocardi_url,
            "timestamp": timestamp
        }

        # Estrai relazioni
        relazioni = brocardi_info.get("Relazioni", [])
        for rel in relazioni:
            if rel.get("tipo") == "libro_obbligazioni":
                params["rel_libro"] = rel.get("testo", "")
                params["para_libro"] = rel.get("numero_paragrafo", "")
                self.stats.relazioni_libro += 1
            elif rel.get("tipo") == "codice_civile":
                params["rel_codice"] = rel.get("testo", "")
                params["para_codice"] = rel.get("numero_paragrafo", "")
                self.stats.relazioni_codice += 1

        # Ratio
        if brocardi_info.get("Ratio"):
            params["ratio"] = brocardi_info["Ratio"]
            self.stats.ratio_legis += 1

        try:
            # Cypher: MERGE su Norma esistente
            await self.falkordb.query("""
                MATCH (n:Norma {URN: $urn})
                SET n.brocardi_url = $brocardi_url,
                    n.brocardi_enriched_at = $timestamp
            """ + ("""
                , n.relazione_libro_obbligazioni = $rel_libro
                , n.relazione_paragrafo_libro = $para_libro
            """ if "rel_libro" in params else "") + ("""
                , n.relazione_codice_civile = $rel_codice
                , n.relazione_paragrafo_codice = $para_codice
            """ if "rel_codice" in params else "") + ("""
                , n.ratio_legis = $ratio
            """ if "ratio" in params else ""),
            params)

            return True

        except Exception as e:
            logger.error(f"Error updating Norma {urn}: {e}")
            return False

    async def create_cita_relations(
        self,
        source_urn: str,
        brocardi_info: Dict[str, Any]
    ) -> int:
        """Crea relazioni :cita verso articoli citati nelle Relazioni."""

        if self.dry_run:
            return 0

        count = 0
        relazioni = brocardi_info.get("Relazioni", [])

        for rel in relazioni:
            fonte = "relazione_guardasigilli_1941" if rel.get("tipo") == "libro_obbligazioni" else "relazione_guardasigilli_1942"
            paragrafo = rel.get("numero_paragrafo", "")

            for art_citato in rel.get("articoli_citati", []):
                numero = art_citato.get("numero", "")
                if not numero:
                    continue

                # Costruisci URN target
                target_urn = self._build_urn_from_article(numero)

                # Skip self-citations (articolo non puo' citare se stesso)
                if source_urn == target_urn:
                    logger.debug(f"Skipping self-citation for {numero}")
                    continue

                try:
                    await self.falkordb.query("""
                        MATCH (source:Norma {URN: $source_urn})
                        MATCH (target:Norma {URN: $target_urn})
                        MERGE (source)-[r:cita]->(target)
                        ON CREATE SET
                            r.tipo_citazione = 'riferimento',
                            r.fonte_relazione = $fonte,
                            r.paragrafo_riferimento = $paragrafo,
                            r.certezza = 'esplicita',
                            r.data_decorrenza = date('1942-04-04')
                    """, {
                        "source_urn": source_urn,
                        "target_urn": target_urn,
                        "fonte": fonte,
                        "paragrafo": f"§{paragrafo}" if paragrafo else None
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"Error creating cita relation {source_urn} -> {target_urn}: {e}")

        return count

    async def create_dottrina_nodes(
        self,
        norma_urn: str,
        article_num: str,
        brocardi_info: Dict[str, Any]
    ) -> int:
        """Crea nodi Dottrina per Spiegazione e Brocardi (massime latine)."""

        if self.dry_run:
            return 0

        count = 0
        timestamp = datetime.now().isoformat()

        # 1. Spiegazione -> Dottrina
        if brocardi_info.get("Spiegazione"):
            spiegazione = brocardi_info["Spiegazione"]
            node_id = f"dottrina:brocardi:spiegazione:{article_num}"

            try:
                await self.falkordb.query("""
                    MERGE (d:Dottrina {node_id: $node_id})
                    ON CREATE SET
                        d.titolo = $titolo,
                        d.autore = 'Brocardi.it',
                        d.descrizione = $descrizione,
                        d.fonte = 'Brocardi.it',
                        d.tipo = 'commentario_online',
                        d.created_at = $timestamp
                    WITH d
                    MATCH (n:Norma {URN: $norma_urn})
                    MERGE (d)-[r:commenta]->(n)
                    ON CREATE SET
                        r.fonte_relazione = 'Brocardi.it',
                        r.certezza = 'esplicita'
                """, {
                    "node_id": node_id,
                    "titolo": f"Spiegazione Art. {article_num} c.c.",
                    "descrizione": spiegazione[:500] if len(spiegazione) > 500 else spiegazione,
                    "norma_urn": norma_urn,
                    "timestamp": timestamp
                })
                count += 1
                self.stats.commenta_relations += 1
            except Exception as e:
                logger.warning(f"Error creating Dottrina for Spiegazione {article_num}: {e}")

        # 2. Brocardi (massime latine) -> Dottrina
        for i, brocardo in enumerate(brocardi_info.get("Brocardi", [])):
            node_id = f"dottrina:brocardo:{article_num}:{i}"

            try:
                await self.falkordb.query("""
                    MERGE (d:Dottrina {node_id: $node_id})
                    ON CREATE SET
                        d.titolo = $titolo,
                        d.autore = 'Tradizione giuridica romana',
                        d.descrizione = $descrizione,
                        d.fonte = 'Brocardi.it',
                        d.tipo = 'brocardo',
                        d.created_at = $timestamp
                    WITH d
                    MATCH (n:Norma {URN: $norma_urn})
                    MERGE (d)-[r:commenta]->(n)
                    ON CREATE SET
                        r.fonte_relazione = 'Brocardi.it',
                        r.certezza = 'esplicita'
                """, {
                    "node_id": node_id,
                    "titolo": brocardo[:50] if len(brocardo) > 50 else brocardo,
                    "descrizione": brocardo,
                    "norma_urn": norma_urn,
                    "timestamp": timestamp
                })
                count += 1
                self.stats.commenta_relations += 1
            except Exception as e:
                logger.warning(f"Error creating Dottrina for Brocardo {article_num}:{i}: {e}")

        return count

    async def create_atto_giudiziario_nodes(
        self,
        norma_urn: str,
        article_num: str,
        brocardi_info: Dict[str, Any]
    ) -> int:
        """Crea nodi AttoGiudiziario per Massime giurisprudenziali."""

        if self.dry_run:
            return 0

        count = 0
        timestamp = datetime.now().isoformat()

        for massima_text in brocardi_info.get("Massime", []):
            parsed = self._parse_massima(massima_text)
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
                    "data": parsed.get("data"),
                    "norma_urn": norma_urn,
                    "timestamp": timestamp
                })
                count += 1
                self.stats.interpreta_relations += 1
            except Exception as e:
                logger.warning(f"Error creating AttoGiudiziario for massima {article_num}: {e}")

        return count

    async def enrich_article(self, article_num: str) -> bool:
        """
        Arricchisce un singolo articolo con dati Brocardi.

        Returns:
            True se arricchito con successo, False altrimenti
        """
        urn = self._build_urn_from_article(article_num)

        try:
            # Costruisci NormaVisitata per lo scraper
            norma_visitata = self._build_norma_visitata(article_num)

            # Fetch Brocardi info
            position, brocardi_info, brocardi_url = await self.scraper.get_info(norma_visitata)

            if not brocardi_info:
                logger.debug(f"Art. {article_num}: No Brocardi data available")
                return False

            # 1. Update Norma properties
            await self.update_norma_properties(urn, brocardi_info, brocardi_url)

            # 2. Create cita relations
            cita_count = await self.create_cita_relations(urn, brocardi_info)
            self.stats.cita_relations += cita_count

            # 3. Create Dottrina nodes
            dottrina_count = await self.create_dottrina_nodes(urn, article_num, brocardi_info)
            self.stats.dottrina_created += dottrina_count

            # 4. Create AttoGiudiziario nodes
            atto_count = await self.create_atto_giudiziario_nodes(urn, article_num, brocardi_info)
            self.stats.atto_giudiziario_created += atto_count

            logger.debug(
                f"Art. {article_num}: enriched "
                f"(cita={cita_count}, dottrina={dottrina_count}, atti={atto_count})"
            )
            return True

        except Exception as e:
            logger.error(f"Error enriching article {article_num}: {e}")
            self.stats.add_error(article_num, str(e))
            return False

    async def run(
        self,
        start_article: int = None,
        end_article: int = None
    ) -> EnrichmentStats:
        """
        Esegue l'enrichment batch.

        Args:
            start_article: Primo articolo (default: 1173)
            end_article: Ultimo articolo (default: 2059)

        Returns:
            EnrichmentStats con i risultati
        """
        start = start_article or self.LIBRO_IV_START
        end = end_article or self.LIBRO_IV_END

        logger.info(f"Starting Brocardi enrichment: Art. {start} - Art. {end}")
        logger.info(f"Dry run: {self.dry_run}")

        articles_to_process = list(range(start, end + 1))
        total = len(articles_to_process)

        logger.info(f"Processing {total} articles")

        for i, art_num in enumerate(articles_to_process, 1):
            art_str = str(art_num)
            self.stats.articles_attempted += 1

            # Progress log
            if i % self.PROGRESS_LOG_INTERVAL == 0:
                logger.info(
                    f"Progress: {i}/{total} ({100*i/total:.1f}%) - "
                    f"Enriched: {self.stats.articles_enriched}, "
                    f"Skipped: {self.stats.articles_skipped}, "
                    f"Failed: {self.stats.articles_failed}"
                )

            # Batch pause
            if i > 0 and i % self.BATCH_PAUSE_INTERVAL == 0:
                logger.info(f"Batch pause: {self.BATCH_PAUSE_SECONDS} seconds...")
                await asyncio.sleep(self.BATCH_PAUSE_SECONDS)

            # Enrich
            success = await self.enrich_article(art_str)

            if success:
                self.stats.articles_enriched += 1
            else:
                # Check if it was a skip (no data) or a failure (error)
                if self.stats.errors and self.stats.errors[-1].get("article") == art_str:
                    self.stats.articles_failed += 1
                else:
                    self.stats.articles_skipped += 1

            # Rate limiting
            await asyncio.sleep(self.BROCARDI_DELAY)

        # Finalize
        self.stats.end_time = datetime.now().isoformat()

        # Log summary
        logger.info("=" * 60)
        logger.info("ENRICHMENT COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Articles attempted: {self.stats.articles_attempted}")
        logger.info(f"Articles enriched: {self.stats.articles_enriched}")
        logger.info(f"Articles skipped: {self.stats.articles_skipped}")
        logger.info(f"Articles failed: {self.stats.articles_failed}")
        logger.info("-" * 40)
        logger.info(f"Relazioni Libro Obbligazioni: {self.stats.relazioni_libro}")
        logger.info(f"Relazioni Codice Civile: {self.stats.relazioni_codice}")
        logger.info(f"Ratio Legis: {self.stats.ratio_legis}")
        logger.info("-" * 40)
        logger.info(f"Dottrina nodes created: {self.stats.dottrina_created}")
        logger.info(f"AttoGiudiziario nodes created: {self.stats.atto_giudiziario_created}")
        logger.info("-" * 40)
        logger.info(f":cita relations: {self.stats.cita_relations}")
        logger.info(f":commenta relations: {self.stats.commenta_relations}")
        logger.info(f":interpreta relations: {self.stats.interpreta_relations}")
        logger.info("-" * 40)
        logger.info(f"Errors: {len(self.stats.errors)}")

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description="Batch Brocardi enrichment EXP-002")
    parser.add_argument("--start", type=int, default=1173, help="Start article")
    parser.add_argument("--end", type=int, default=2059, help="End article")
    parser.add_argument("--dry-run", action="store_true", help="No database writes")
    parser.add_argument("--output", type=str, default="logs/enrich_stats.json", help="Stats output file")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("EXP-002: Brocardi Enrichment")
    logger.info("=" * 60)

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
        # Run enrichment
        runner = BrocardiEnrichmentRunner(
            falkordb_client=falkordb,
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
        logger.info("Connection closed")


if __name__ == "__main__":
    asyncio.run(main())
