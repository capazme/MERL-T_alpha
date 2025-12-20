#!/usr/bin/env python3
"""
EXP-014: Full Ingestion Pipeline
=================================

Esegue ingestion completa:
1. Backbone: Libro IV Codice Civile (Normattiva + Brocardi strutturale)
2. Enrichment Fase 1: Brocardi LLM (entità schema-compliant)
3. Enrichment Fase 2: Torrente LLM (arricchimento entità)

Questa pipeline implementa Option C: esecuzione sequenziale per fasi
dove Brocardi crea entità fondative che Torrente poi arricchisce.

Usage:
    # Backbone only
    python scripts/exp014_full_ingestion.py --backbone

    # Enrichment only (richiede backbone esistente)
    python scripts/exp014_full_ingestion.py --enrichment

    # Full pipeline
    python scripts/exp014_full_ingestion.py --full

    # Dry-run per preview
    python scripts/exp014_full_ingestion.py --full --dry-run

    # Test con subset (5 articoli backbone, 10 chunk per fonte)
    python scripts/exp014_full_ingestion.py --full --test

Author: Claude + gpuzio
Date: 14 Dicembre 2025
Experiment: EXP-014
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from merlt import LegalKnowledgeGraph, MerltConfig
from merlt.pipeline.enrichment import EnrichmentConfig
from merlt.pipeline.enrichment.config import EnrichmentScope
from merlt.pipeline.enrichment.models import EntityType
from merlt.pipeline.enrichment.sources.brocardi import BrocardiEnrichmentSource
from merlt.pipeline.enrichment.sources.manual import ManualEnrichmentSource

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path("logs") / f"exp014_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════════════════

# Libro IV: Delle obbligazioni (artt. 1173-2059)
LIBRO_IV_RANGE = (1173, 2059)

# Path manuali
PDF_PATH = Path("data")
MANUAL_NAME = "Torrente-libroiv"

# Entity types da estrarre - TUTTI i 17 tipi dello schema
ENTITY_TYPES = [
    # Core (astratti)
    EntityType.CONCETTO,
    EntityType.PRINCIPIO,
    EntityType.DEFINIZIONE,
    # Soggettivi
    EntityType.SOGGETTO,
    EntityType.RUOLO,
    EntityType.MODALITA,
    # Dinamici
    EntityType.FATTO,
    EntityType.ATTO,
    EntityType.PROCEDURA,
    EntityType.TERMINE,
    EntityType.EFFETTO,
    EntityType.RESPONSABILITA,
    EntityType.RIMEDIO,
    # Normativi
    EntityType.SANZIONE,
    EntityType.CASO,
    EntityType.ECCEZIONE,
    EntityType.CLAUSOLA,
]

# Test mode: subset ridotto
TEST_ARTICLES = (1173, 1177)  # Solo 5 articoli per test rapido
TEST_MAX_CHUNKS = 10  # 10 chunk per fonte


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: BACKBONE
# ═══════════════════════════════════════════════════════════════════════════════

async def run_backbone(
    kg: LegalKnowledgeGraph,
    article_range: tuple,
    dry_run: bool = False,
    batch_size: int = 10,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """
    Esegue backbone ingestion: Normattiva + Brocardi strutturale.

    OTTIMIZZATO: Usa BatchIngestionPipeline per parallelizzare:
    - HTTP fetches (Normattiva + Brocardi)
    - Batch embedding generation
    - Batch database operations

    Performance: 5-10x più veloce del metodo sequenziale.

    Args:
        kg: LegalKnowledgeGraph connesso
        article_range: Tupla (start, end) degli articoli
        dry_run: Se True, solo preview
        batch_size: Articoli per batch (default: 10)
        max_concurrent: Max fetch HTTP paralleli (default: 5)

    Returns:
        Dizionario con risultati
    """
    start_art, end_art = article_range
    total_articles = end_art - start_art + 1

    logger.info(f"=== BACKBONE OTTIMIZZATO: Artt. {start_art}-{end_art} ({total_articles} articoli) ===")
    logger.info(f"    Batch size: {batch_size}, Max concurrent: {max_concurrent}")

    if dry_run:
        logger.info("[DRY-RUN] Backbone skip")
        return {"mode": "dry_run", "articles": total_articles}

    results = {
        "start_article": start_art,
        "end_article": end_art,
        "total_articles": total_articles,
        "ingested": 0,
        "skipped": 0,
        "embeddings": 0,
        "nodes": 0,
        "bridge_mappings": 0,
        "duration_seconds": 0,
        "errors": [],
    }

    # USA BATCH INGESTION OTTIMIZZATO
    try:
        batch_result = await kg.ingest_batch(
            tipo_atto="codice civile",
            article_range=article_range,
            batch_size=batch_size,
            max_concurrent_fetches=max_concurrent,
            include_brocardi=True,
            include_multivigenza=True,
        )

        results["ingested"] = batch_result.successful
        results["skipped"] = batch_result.failed
        results["embeddings"] = batch_result.embeddings_created
        results["nodes"] = batch_result.graph_nodes_created
        results["bridge_mappings"] = batch_result.bridge_mappings_created
        results["duration_seconds"] = batch_result.duration_seconds
        results["errors"] = batch_result.errors[:10]  # Limit errors

        logger.info(batch_result.summary())

    except Exception as e:
        logger.error(f"Backbone batch failed: {e}")
        results["errors"].append(f"Batch failed: {str(e)}")

    logger.info(
        f"Backbone completato: {results['ingested']} ingeriti, "
        f"{results['skipped']} saltati, {len(results['errors'])} errori"
    )

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════════

async def run_enrichment(
    kg: LegalKnowledgeGraph,
    article_range: tuple,
    entity_types: list,
    max_chunks: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Esegue enrichment con Brocardi (fase 1) e Torrente (fase 2).

    Args:
        kg: LegalKnowledgeGraph connesso
        article_range: Tupla (start, end) per scope
        entity_types: Tipi entità da estrarre
        max_chunks: Limite chunk per fonte (None = tutti)
        dry_run: Se True, solo preview

    Returns:
        Dizionario con risultati
    """
    start_art, end_art = article_range

    logger.info(f"=== ENRICHMENT: Fase 1 (Brocardi) + Fase 2 (Torrente) ===")

    # Crea scope
    scope = EnrichmentScope(articoli=(start_art, end_art))

    # Crea fonti con fasi diverse
    # BrocardiEnrichmentSource può usare graph_client dal kg se serve query articoli
    brocardi_source = BrocardiEnrichmentSource(
        graph_client=kg._falkordb,  # Per query articoli esistenti
        act_type="codice civile",
        phase=1,  # Fase primaria
    )

    torrente_source = ManualEnrichmentSource(
        path=str(PDF_PATH),
        manual_name=MANUAL_NAME,
        act_type="codice civile",
        phase=2,  # Fase arricchimento
    )

    # Configura enrichment
    enrichment_config = EnrichmentConfig(
        sources=[brocardi_source, torrente_source],  # Ordinate per fase
        entity_types=entity_types,
        scope=scope,
        checkpoint_dir=Path("data/checkpoints/exp014/"),
        audit_log_path=Path("logs/exp014_audit.jsonl"),
        dry_run=dry_run,
        verbose=True,
    )

    logger.info(f"Entity types: {[t.value for t in entity_types]}")
    logger.info(f"Scope: artt. {start_art}-{end_art}")
    logger.info(f"Fonti: {[s.source_name for s in enrichment_config.sources]}")
    logger.info(f"Fasi: Brocardi (phase=1) → Torrente (phase=2)")

    if dry_run:
        logger.info("[DRY-RUN] Enrichment preview")
        return {"mode": "dry_run", "sources": 2, "entity_types": len(entity_types)}

    # Esegui enrichment
    result = await kg.enrich(enrichment_config)

    # Prepara risultati
    enrichment_results = {
        "contents_processed": result.contents_processed,
        "contents_skipped": result.contents_skipped,
        "stats": {
            "total_created": result.stats.total_entities_created,
            "total_merged": result.stats.total_entities_merged,
            "concepts": result.stats.concepts_created,
            "principles": result.stats.principles_created,
            "definitions": result.stats.definitions_created,
            "relations": result.stats.relations_created,
        },
        "errors": len(result.errors),
        "success": result.success,
    }

    logger.info(result.summary())

    return enrichment_results


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: VALIDAZIONE
# ═══════════════════════════════════════════════════════════════════════════════

async def run_validation(kg: LegalKnowledgeGraph) -> Dict[str, Any]:
    """
    Valida i risultati dell'ingestion completa.

    Checks:
    - Rubrica non in comma (fix parsing)
    - Entità create per tipo
    - Relazioni Norma → Entità
    - Fonti su entità (Brocardi + Torrente)
    """
    logger.info("=== VALIDAZIONE RISULTATI ===")

    validation_results = {}

    queries = {
        "backbone_norme": "MATCH (n:Norma) RETURN count(n) as count",
        "backbone_commi": "MATCH (c:Comma) RETURN count(c) as count",
        "rubrica_bug": """
            MATCH (c:Comma)
            WHERE c.numero_comma = '1'
            AND (c.testo STARTS WITH '(' AND c.testo CONTAINS ')')
            AND size(c.testo) < 100
            RETURN count(c) as count
        """,
        "entities_concetto": "MATCH (e:ConcettoGiuridico) RETURN count(e) as count",
        "entities_principio": "MATCH (e:PrincipioGiuridico) RETURN count(e) as count",
        "entities_definizione": "MATCH (e:DefinizioneLegale) RETURN count(e) as count",
        "relations_disciplina": "MATCH ()-[r:DISCIPLINA]->() RETURN count(r) as count",
        "entities_with_brocardi": """
            MATCH (e)
            WHERE 'brocardi' IN e.fonti
            RETURN count(e) as count
        """,
        "entities_with_torrente": """
            MATCH (e)
            WHERE any(f IN e.fonti WHERE f STARTS WITH 'manuale:')
            RETURN count(e) as count
        """,
        "entities_multi_source": """
            MATCH (e)
            WHERE size(e.fonti) > 1
            RETURN count(e) as count
        """,
    }

    for name, query in queries.items():
        try:
            result = await kg._falkordb.query(query)
            count = result[0]["count"] if result else 0
            validation_results[name] = count
            logger.info(f"  {name}: {count}")
        except Exception as e:
            validation_results[name] = f"ERROR: {e}"
            logger.error(f"  {name}: ERROR - {e}")

    # Calcola metriche derivate
    if isinstance(validation_results.get("rubrica_bug"), int):
        validation_results["rubrica_bug_status"] = (
            "PASS" if validation_results["rubrica_bug"] == 0 else "FAIL"
        )

    if all(isinstance(validation_results.get(k), int) for k in [
        "entities_with_brocardi", "entities_with_torrente"
    ]):
        validation_results["multi_source_dynamics"] = (
            "OK" if validation_results["entities_multi_source"] > 0 else "NO_MERGE"
        )

    return validation_results


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

async def run_full_pipeline(
    mode: str,
    test_mode: bool = False,
    dry_run: bool = False,
    batch_size: int = 10,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """
    Esegue la pipeline completa o parziale.

    Args:
        mode: "backbone", "enrichment", o "full"
        test_mode: Se True, usa subset ridotto
        dry_run: Se True, solo preview
        batch_size: Articoli per batch (ottimizzazione)
        max_concurrent: Max fetch HTTP paralleli

    Returns:
        Dizionario con tutti i risultati
    """
    start_time = datetime.now()

    # Determina range articoli
    if test_mode:
        article_range = TEST_ARTICLES
        max_chunks = TEST_MAX_CHUNKS
        logger.info(f"🧪 TEST MODE: artt. {TEST_ARTICLES}, max {TEST_MAX_CHUNKS} chunks")
    else:
        article_range = LIBRO_IV_RANGE
        max_chunks = None
        logger.info(f"📚 FULL MODE: Libro IV completo")

    results = {
        "experiment": "EXP-014",
        "mode": mode,
        "test_mode": test_mode,
        "dry_run": dry_run,
        "started_at": start_time.isoformat(),
        "article_range": article_range,
    }

    # Connessione
    logger.info("\n🔌 Connessione ai database...")
    config = MerltConfig(
        graph_name=os.environ.get("FALKORDB_GRAPH", "merl_t_dev"),
        qdrant_collection=os.environ.get("QDRANT_COLLECTION", "merl_t_dev_chunks"),
    )
    kg = LegalKnowledgeGraph(config)
    await kg.connect()
    logger.info("  ✓ FalkorDB connesso")
    logger.info("  ✓ Qdrant connesso")

    try:
        # BACKBONE
        if mode in ("backbone", "full"):
            results["backbone"] = await run_backbone(
                kg, article_range,
                dry_run=dry_run,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
            )

        # ENRICHMENT
        if mode in ("enrichment", "full"):
            results["enrichment"] = await run_enrichment(
                kg,
                article_range,
                ENTITY_TYPES,
                max_chunks=max_chunks,
                dry_run=dry_run,
            )

        # VALIDATION (sempre, anche dopo partial)
        if not dry_run:
            results["validation"] = await run_validation(kg)

    finally:
        await kg.close()

    # Finalizza
    results["completed_at"] = datetime.now().isoformat()
    results["duration_seconds"] = (datetime.now() - start_time).total_seconds()

    # Salva risultati
    output_path = Path("docs/experiments/EXP-014_full_ingestion/results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"\n📊 Risultati salvati in: {output_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="EXP-014: Full Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Test rapido (5 articoli, 10 chunks)
  python scripts/exp014_full_ingestion.py --full --test

  # Dry-run full pipeline
  python scripts/exp014_full_ingestion.py --full --dry-run

  # Solo backbone
  python scripts/exp014_full_ingestion.py --backbone

  # Solo enrichment (richiede backbone esistente)
  python scripts/exp014_full_ingestion.py --enrichment

  # Full pipeline Libro IV completo
  python scripts/exp014_full_ingestion.py --full
        """
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--backbone",
        action="store_true",
        help="Esegui solo backbone (Normattiva + Brocardi strutturale)"
    )
    mode_group.add_argument(
        "--enrichment",
        action="store_true",
        help="Esegui solo enrichment (Brocardi LLM + Torrente LLM)"
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Esegui pipeline completa (backbone + enrichment)"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: usa subset ridotto (5 articoli, 10 chunks)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview senza eseguire"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Articoli per batch (default: 10)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Max fetch HTTP paralleli (default: 5)"
    )

    args = parser.parse_args()

    # Determina mode
    if args.backbone:
        mode = "backbone"
    elif args.enrichment:
        mode = "enrichment"
    else:
        mode = "full"

    # Esegui
    print(f"\n{'═' * 70}")
    print(f"EXP-014: FULL INGESTION PIPELINE (OTTIMIZZATO)")
    print(f"{'═' * 70}")
    print(f"Mode: {mode.upper()}")
    print(f"Test: {args.test}")
    print(f"Dry-run: {args.dry_run}")
    print(f"Batch size: {args.batch_size}")
    print(f"Max concurrent: {args.max_concurrent}")
    print(f"{'═' * 70}\n")

    # Crea directory logs se non esiste
    Path("logs").mkdir(exist_ok=True)

    results = asyncio.run(run_full_pipeline(
        mode=mode,
        test_mode=args.test,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent,
    ))

    # Stampa summary
    print(f"\n{'═' * 70}")
    print("RISULTATI FINALI")
    print(f"{'═' * 70}")

    if "backbone" in results:
        bb = results["backbone"]
        if isinstance(bb, dict) and "ingested" in bb:
            print(f"Backbone: {bb['ingested']} articoli ingeriti")
            if "embeddings" in bb:
                print(f"  - Embeddings: {bb['embeddings']}")
            if "nodes" in bb:
                print(f"  - Nodi grafo: {bb['nodes']}")
            if "bridge_mappings" in bb:
                print(f"  - Bridge mappings: {bb['bridge_mappings']}")
            if "duration_seconds" in bb:
                print(f"  - Durata backbone: {bb['duration_seconds']:.1f}s")

    if "enrichment" in results:
        en = results["enrichment"]
        if isinstance(en, dict) and "stats" in en:
            print(f"Enrichment: {en['stats']['total_created']} entità create")

    if "validation" in results:
        val = results["validation"]
        if isinstance(val, dict):
            print(f"Validazione:")
            print(f"  - Norme: {val.get('backbone_norme', '?')}")
            print(f"  - Concetti: {val.get('entities_concetto', '?')}")
            print(f"  - Rubrica bug: {val.get('rubrica_bug_status', '?')}")
            print(f"  - Multi-source: {val.get('entities_multi_source', '?')}")

    print(f"\nDurata: {results.get('duration_seconds', 0):.1f}s")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()
