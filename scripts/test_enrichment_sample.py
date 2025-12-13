#!/usr/bin/env python3
"""
Test Enrichment Pipeline - Manuale Torrente
============================================

Script per testare l'enrichment incrementale con il manuale Torrente (Libro IV CC).

Approccio: Processa il PDF per CHUNKS (non filtra per articoli).
Il manuale cita articoli in ordine sparso, quindi l'EntityLinker
deduplica automaticamente e il GraphWriter mergia con il grafo esistente.

Usage:
    # Test 1: 10 chunk (sample rapido, ~$1-2)
    python scripts/test_enrichment_sample.py --test 1 --dry-run  # Preview
    python scripts/test_enrichment_sample.py --test 1           # Esegui

    # Test 2: 30 chunk (capitolo, ~$4-6)
    python scripts/test_enrichment_sample.py --test 2

    # Test 3: PDF completo (~$30-50, ~1-2 ore)
    python scripts/test_enrichment_sample.py --test 3

    # Custom
    python scripts/test_enrichment_sample.py --max-chunks 5 --dry-run

Author: Claude + gpuzio
Date: 13 Dicembre 2025
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from merlt import LegalKnowledgeGraph, MerltConfig
from merlt.pipeline.enrichment import EnrichmentConfig
from merlt.pipeline.enrichment.models import EntityType, EnrichmentContent
from merlt.pipeline.enrichment.sources.manual import ManualEnrichmentSource


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAZIONI TEST
# ═══════════════════════════════════════════════════════════════════════════════

TEST_CONFIGS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Sample (10 chunk)",
        "description": "Test rapido per validare parsing PDF e estrazione base",
        "max_chunks": 10,
        "entity_types": [
            EntityType.CONCETTO,
            EntityType.PRINCIPIO,
            EntityType.DEFINIZIONE,
        ],
        "expected_entities": (10, 30),  # min, max attesi
        "estimated_cost": "$1-2",
        "estimated_time": "3-5 min",
    },
    2: {
        "name": "Capitolo (30 chunk)",
        "description": "Test incrementale per validare deduplicazione",
        "max_chunks": 30,
        "entity_types": [
            EntityType.CONCETTO,
            EntityType.PRINCIPIO,
            EntityType.DEFINIZIONE,
            EntityType.SOGGETTO,
            EntityType.RUOLO,
            EntityType.MODALITA,
        ],
        "expected_entities": (30, 80),
        "estimated_cost": "$4-6",
        "estimated_time": "10-15 min",
    },
    3: {
        "name": "PDF Completo",
        "description": "Ingestion completa del manuale Torrente - Libro IV",
        "max_chunks": None,  # Tutto il PDF
        "entity_types": [
            EntityType.CONCETTO,
            EntityType.PRINCIPIO,
            EntityType.DEFINIZIONE,
            EntityType.SOGGETTO,
            EntityType.RUOLO,
            EntityType.MODALITA,
            EntityType.FATTO,
            EntityType.ATTO,
            EntityType.PROCEDURA,
            EntityType.TERMINE,
            EntityType.EFFETTO,
            EntityType.RESPONSABILITA,
            EntityType.RIMEDIO,
            EntityType.SANZIONE,
            EntityType.CASO,
            EntityType.ECCEZIONE,
            EntityType.CLAUSOLA,
        ],
        "expected_entities": (200, 600),
        "estimated_cost": "$30-50",
        "estimated_time": "1-2 ore",
    },
}

# Path al PDF
PDF_PATH = Path("data")
MANUAL_NAME = "Torrente-libroiv"


# ═══════════════════════════════════════════════════════════════════════════════
# WRAPPER PER LIMITARE CHUNKS
# ═══════════════════════════════════════════════════════════════════════════════

class LimitedManualSource(ManualEnrichmentSource):
    """
    ManualEnrichmentSource con limite sul numero di chunk.

    Permette di testare l'enrichment con un sottoinsieme del PDF
    senza modificare la pipeline core.
    """

    def __init__(
        self,
        path: str,
        manual_name: str = "unknown",
        max_chunks: Optional[int] = None,
        **kwargs
    ):
        """
        Args:
            path: Directory contenente i PDF
            manual_name: Nome del manuale
            max_chunks: Limite chunk da processare (None = tutti)
        """
        super().__init__(path, manual_name, **kwargs)
        self.max_chunks = max_chunks

    async def fetch(
        self,
        scope=None
    ) -> AsyncIterator[EnrichmentContent]:
        """
        Override fetch per limitare il numero di chunk.

        Non filtra per articoli - processa tutti i chunk fino al limite.
        """
        count = 0
        async for content in super().fetch(scope):
            if self.max_chunks is not None and count >= self.max_chunks:
                break
            yield content
            count += 1

        print(f"  ✓ Processati {count} chunk (limite: {self.max_chunks or 'nessuno'})")


# ═══════════════════════════════════════════════════════════════════════════════
# FUNZIONI PRINCIPALI
# ═══════════════════════════════════════════════════════════════════════════════

async def run_test(
    test_num: int,
    dry_run: bool = False,
    reset_checkpoint: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Esegue un test predefinito.

    Args:
        test_num: Numero test (1, 2, o 3)
        dry_run: Se True, mostra solo preview senza eseguire
        reset_checkpoint: Se True, ignora checkpoint precedenti
        verbose: Log dettagliato

    Returns:
        Dizionario con risultati del test
    """
    if test_num not in TEST_CONFIGS:
        raise ValueError(f"Test {test_num} non definito. Usa 1, 2, o 3.")

    config = TEST_CONFIGS[test_num]

    print(f"\n{'═' * 70}")
    print(f"TEST {test_num}: {config['name']}")
    print(f"{'═' * 70}")
    print(f"Descrizione: {config['description']}")
    print(f"Max chunks: {config['max_chunks'] or 'tutti'}")
    print(f"Entity types: {len(config['entity_types'])} tipi")
    print(f"Costo stimato: {config['estimated_cost']}")
    print(f"Tempo stimato: {config['estimated_time']}")
    print(f"{'─' * 70}")

    if dry_run:
        return await preview_test(test_num)

    return await run_enrichment(
        max_chunks=config["max_chunks"],
        entity_types=config["entity_types"],
        test_name=f"test_{test_num}",
        reset_checkpoint=reset_checkpoint,
        verbose=verbose,
    )


async def preview_test(test_num: int) -> Dict[str, Any]:
    """
    Preview del test senza eseguire (mostra chunk che verrebbero processati).
    """
    config = TEST_CONFIGS[test_num]
    max_chunks = config["max_chunks"] or 100  # Preview max 100

    print("\n[DRY-RUN] Preview dei chunk che verrebbero processati:\n")

    # Verifica PDF esiste
    pdf_file = PDF_PATH / f"{MANUAL_NAME}.pdf"
    if not pdf_file.exists():
        print(f"  ❌ PDF non trovato: {pdf_file}")
        return {"error": f"PDF not found: {pdf_file}"}

    print(f"  ✓ PDF trovato: {pdf_file} ({pdf_file.stat().st_size / 1024 / 1024:.1f} MB)")

    # Crea source e inizializza
    source = LimitedManualSource(
        path=str(PDF_PATH),
        manual_name=MANUAL_NAME,
        max_chunks=min(max_chunks, 5),  # Preview solo primi 5
    )
    await source.initialize()

    # Mostra primi chunk
    chunks_info = []
    async for content in source.fetch():
        chunks_info.append({
            "id": content.id,
            "text_preview": content.text[:200] + "..." if len(content.text) > 200 else content.text,
            "article_refs": content.article_refs[:5],
            "page": content.metadata.get("page_num", "?"),
        })
        print(f"\n  Chunk {len(chunks_info)}: pagina {content.metadata.get('page_num', '?')}")
        print(f"    Articoli citati: {content.article_refs[:5]}")
        print(f"    Testo: {content.text[:150]}...")

    print(f"\n{'─' * 70}")
    print(f"Con Test {test_num} verrebbero processati {config['max_chunks'] or 'tutti'} chunk")
    print(f"Entity types: {[t.value for t in config['entity_types']]}")
    print(f"\nEsegui senza --dry-run per processare.")

    return {
        "mode": "dry_run",
        "test_num": test_num,
        "chunks_previewed": len(chunks_info),
        "config": config,
    }


async def run_enrichment(
    max_chunks: Optional[int],
    entity_types: List[EntityType],
    test_name: str = "custom",
    reset_checkpoint: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Esegue enrichment con la configurazione specificata.

    Args:
        max_chunks: Limite chunk (None = tutti)
        entity_types: Tipi entità da estrarre
        test_name: Nome test per checkpoint/log
        reset_checkpoint: Ignora checkpoint precedenti
        verbose: Log dettagliato

    Returns:
        Dizionario con risultati
    """
    start_time = datetime.now()

    # Verifica PDF
    pdf_file = PDF_PATH / f"{MANUAL_NAME}.pdf"
    if not pdf_file.exists():
        print(f"❌ PDF non trovato: {pdf_file}")
        return {"error": f"PDF not found: {pdf_file}"}

    print(f"\n📄 PDF: {pdf_file.name} ({pdf_file.stat().st_size / 1024 / 1024:.1f} MB)")

    # Inizializza Knowledge Graph
    print("\n🔌 Connessione ai database...")
    config = MerltConfig(
        graph_name="merl_t_dev",
        qdrant_collection="merl_t_dev_chunks",
    )
    kg = LegalKnowledgeGraph(config)
    await kg.connect()
    print("  ✓ FalkorDB connesso")
    print("  ✓ Qdrant connesso")

    # Crea source con limite chunk
    source = LimitedManualSource(
        path=str(PDF_PATH),
        manual_name=MANUAL_NAME,
        max_chunks=max_chunks,
    )

    # Configura enrichment
    enrichment_config = EnrichmentConfig(
        sources=[source],
        entity_types=entity_types,
        scope=None,  # IMPORTANTE: NO filtro articoli!
        checkpoint_dir=Path(f"data/checkpoints/enrichment_{test_name}/"),
        audit_log_path=Path(f"logs/enrichment_{test_name}_audit.jsonl"),
        verbose=verbose,
        dry_run=False,
    )

    print(f"\n🚀 Avvio enrichment...")
    print(f"   Entity types: {[t.value for t in entity_types]}")
    print(f"   Max chunks: {max_chunks or 'tutti'}")
    print(f"   Checkpoint: {enrichment_config.checkpoint_dir}")

    # Esegui enrichment
    try:
        result = await kg.enrich(enrichment_config)
    except Exception as e:
        print(f"\n❌ Errore durante enrichment: {e}")
        await kg.close()
        return {"error": str(e)}

    # Chiudi connessioni
    await kg.close()

    # Calcola durata
    duration = (datetime.now() - start_time).total_seconds()

    # Stampa risultato
    print(result.summary())

    # Salva metrics
    metrics = {
        "test_name": test_name,
        "timestamp": start_time.isoformat(),
        "duration_seconds": duration,
        "max_chunks": max_chunks,
        "entity_types": [t.value for t in entity_types],
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

    # Salva metrics JSON
    metrics_path = Path(f"docs/experiments/enrichment_{test_name}.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\n📊 Metrics salvate in: {metrics_path}")

    return metrics


async def validate_results() -> Dict[str, Any]:
    """
    Valida i risultati dell'enrichment con query FalkorDB.
    """
    print("\n📋 Validazione risultati in FalkorDB...")

    config = MerltConfig(graph_name="merl_t_dev")
    kg = LegalKnowledgeGraph(config)
    await kg.connect()

    queries = [
        # Conteggio entità per tipo
        (
            "Entità per tipo (schema 2.1)",
            """
            MATCH (e)
            WHERE e.schema_version = '2.1'
            RETURN labels(e)[0] as tipo, count(e) as count
            ORDER BY count DESC
            """
        ),
        # Concetti con fonti
        (
            "Concetti estratti",
            """
            MATCH (c:ConcettoGiuridico)
            WHERE c.schema_version = '2.1'
            RETURN c.nome, c.fonti, c.descrizione
            LIMIT 10
            """
        ),
        # Relazioni create
        (
            "Relazioni Norma → Entità",
            """
            MATCH (n:Norma)-[r:DISCIPLINA]->(e)
            WHERE e.schema_version = '2.1'
            RETURN n.numero_articolo, type(r), e.nome
            ORDER BY n.numero_articolo
            LIMIT 20
            """
        ),
    ]

    results = {}
    for name, query in queries:
        print(f"\n  Query: {name}")
        try:
            result = await kg.graph.query(query)
            results[name] = result.result_set if hasattr(result, 'result_set') else result
            for row in results[name][:5]:
                print(f"    {row}")
            if len(results[name]) > 5:
                print(f"    ... e altri {len(results[name]) - 5}")
        except Exception as e:
            print(f"    ❌ Errore: {e}")
            results[name] = {"error": str(e)}

    await kg.close()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Test enrichment pipeline con manuale Torrente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Preview test 1
  python scripts/test_enrichment_sample.py --test 1 --dry-run

  # Esegui test 1 (10 chunk, ~$1-2)
  python scripts/test_enrichment_sample.py --test 1

  # Test custom con 5 chunk
  python scripts/test_enrichment_sample.py --max-chunks 5

  # Valida risultati
  python scripts/test_enrichment_sample.py --validate
        """
    )

    parser.add_argument(
        "--test", "-t",
        type=int,
        choices=[1, 2, 3],
        help="Test predefinito (1=10 chunk, 2=30 chunk, 3=completo)"
    )
    parser.add_argument(
        "--max-chunks", "-m",
        type=int,
        help="Numero massimo di chunk da processare (override test)"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview senza eseguire"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignora checkpoint precedenti"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Valida risultati in FalkorDB"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log dettagliato"
    )

    args = parser.parse_args()

    # Validation mode
    if args.validate:
        asyncio.run(validate_results())
        return

    # Test mode
    if args.test:
        result = asyncio.run(run_test(
            test_num=args.test,
            dry_run=args.dry_run,
            reset_checkpoint=args.reset,
            verbose=args.verbose,
        ))
    elif args.max_chunks:
        # Custom mode
        result = asyncio.run(run_enrichment(
            max_chunks=args.max_chunks,
            entity_types=[
                EntityType.CONCETTO,
                EntityType.PRINCIPIO,
                EntityType.DEFINIZIONE,
            ],
            test_name=f"custom_{args.max_chunks}",
            reset_checkpoint=args.reset,
            verbose=args.verbose,
        ))
    else:
        parser.print_help()
        print("\n⚠️  Specifica --test N o --max-chunks N")
        return

    # Stampa risultato finale
    if "error" in result:
        print(f"\n❌ Test fallito: {result['error']}")
        sys.exit(1)
    else:
        print(f"\n✅ Test completato!")


if __name__ == "__main__":
    main()
