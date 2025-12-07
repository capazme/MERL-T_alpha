#!/usr/bin/env python3
"""
EXP-007: Esperimento End-to-End Completo
=========================================

Ingestion COMPLETA con tutti i componenti attivi:
- Normattiva scraping
- Brocardi enrichment (massime, ratio, spiegazione)
- Multivigenza (storico modifiche, atti modificanti)
- Graph creation (nodi + relazioni gerarchiche)
- Vector embeddings (Qdrant)
- Bridge Table (PostgreSQL)

Scope: Art. 1453-1469 CC (Risoluzione del contratto) - 17 articoli
- Sezione ricca di giurisprudenza
- Articoli con storico modifiche
- Brocardi completo

Usage:
    python scripts/exp007_full_ingestion.py

    # Skip reset (resume)
    python scripts/exp007_full_ingestion.py --skip-reset

    # Dry run
    python scripts/exp007_full_ingestion.py --dry-run
"""

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt import LegalKnowledgeGraph, MerltConfig


# Configurazione Esperimento
EXPERIMENT_NAME = "EXP-007"
GRAPH_NAME = "merl_t_exp007"
TIPO_ATTO = "codice civile"

# Articoli target: 1453-1469 (Risoluzione del contratto)
TARGET_ARTICLES = list(range(1453, 1470))  # 17 articoli


@dataclass
class EXP007Metrics:
    """Metriche dettagliate per EXP-007."""
    experiment: str = EXPERIMENT_NAME
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    # Articoli
    total_articles: int = 0
    articles_processed: int = 0
    articles_failed: int = 0

    # Enrichment
    brocardi_enriched: int = 0
    multivigenza_enriched: int = 0

    # Grafo
    nodes_created: int = 0
    nodes_norma: int = 0
    nodes_dottrina: int = 0
    nodes_atto_giudiziario: int = 0
    relations_created: int = 0

    # Storage
    chunks_created: int = 0
    embeddings_created: int = 0
    bridge_mappings: int = 0

    # Errori
    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment": self.experiment,
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
                "multivigenza_enriched": self.multivigenza_enriched,
            },
            "graph": {
                "nodes_created": self.nodes_created,
                "nodes_norma": self.nodes_norma,
                "nodes_dottrina": self.nodes_dottrina,
                "nodes_atto_giudiziario": self.nodes_atto_giudiziario,
                "relations_created": self.relations_created,
            },
            "storage": {
                "chunks_created": self.chunks_created,
                "embeddings_created": self.embeddings_created,
                "bridge_mappings": self.bridge_mappings,
            },
            "errors": self.errors[:20],
        }


async def reset_databases(kg: LegalKnowledgeGraph):
    """Reset completo dei database per esperimento pulito."""
    print("\n" + "=" * 60)
    print("FASE 1: RESET DATABASE")
    print("=" * 60)

    # 1. Reset FalkorDB Graph
    print("\n1. Resetting FalkorDB graph...")
    if kg.falkordb:
        try:
            result = await kg.falkordb.query("MATCH (n) RETURN count(n) as c")
            count = result[0]['c'] if result else 0
            if count > 0:
                await kg.falkordb.query("MATCH (n) DETACH DELETE n")
                print(f"   Deleted {count} nodes from graph '{GRAPH_NAME}'")
            else:
                print(f"   Graph '{GRAPH_NAME}' already empty")
        except Exception as e:
            print(f"   Warning: Could not reset graph: {e}")

    # 2. Reset Qdrant Collection
    print("\n2. Resetting Qdrant collection...")
    if kg.qdrant:
        try:
            from qdrant_client.http.exceptions import UnexpectedResponse
            try:
                await kg.qdrant.delete_collection(GRAPH_NAME)
                print(f"   Deleted Qdrant collection '{GRAPH_NAME}'")
            except UnexpectedResponse:
                print(f"   Qdrant collection '{GRAPH_NAME}' not found (OK)")

            # Recreate collection
            from qdrant_client.models import Distance, VectorParams
            await kg.qdrant.create_collection(
                collection_name=GRAPH_NAME,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            print(f"   Created new Qdrant collection '{GRAPH_NAME}'")
        except Exception as e:
            print(f"   Warning: Could not reset Qdrant: {e}")

    # 3. Reset Bridge Table (per questo esperimento)
    print("\n3. Resetting Bridge Table entries...")
    if kg.bridge_table:
        try:
            # Delete mappings che iniziano con il pattern dell'esperimento
            async with kg.bridge_table.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM chunk_node_mapping WHERE graph_node_urn LIKE %s",
                        (f"%{GRAPH_NAME}%",)
                    )
                    deleted = cur.rowcount
                    await conn.commit()
                    print(f"   Deleted {deleted} bridge mappings")
        except Exception as e:
            print(f"   Warning: Could not reset Bridge Table: {e}")

    print("\n   Reset completed!")


async def create_codice_structure(kg: LegalKnowledgeGraph, timestamp: str) -> tuple:
    """Crea struttura base: Codice Civile -> Libro IV."""
    print("\n" + "=" * 60)
    print("FASE 2: CREAZIONE STRUTTURA BASE")
    print("=" * 60)

    # Codice Civile
    cc_urn = "urn:nir:stato:regio.decreto:1942-03-16;262:2"
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
        {"urn": cc_urn, "timestamp": timestamp}
    )
    print("   Created: Codice Civile")

    # Libro IV
    libro_urn = f"{cc_urn}~libroIV"
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
        {"urn": libro_urn, "timestamp": timestamp}
    )

    # Link
    await kg.falkordb.query(
        """
        MATCH (cc:Norma {URN: $cc_urn})
        MATCH (libro:Norma {URN: $libro_urn})
        MERGE (cc)-[r:contiene]->(libro)
        ON CREATE SET r.certezza = 1.0
        """,
        {"cc_urn": cc_urn, "libro_urn": libro_urn}
    )
    print("   Created: Libro IV - Delle obbligazioni")
    print("   Created: Codice Civile -[:contiene]-> Libro IV")

    return cc_urn, libro_urn


async def ingest_articles(
    kg: LegalKnowledgeGraph,
    articles: List[str],
    libro_urn: str,
    metrics: EXP007Metrics
):
    """Ingestion degli articoli con TUTTI i flag attivi."""
    print("\n" + "=" * 60)
    print(f"FASE 3: INGESTION {len(articles)} ARTICOLI")
    print("=" * 60)
    print("   Flags: brocardi=True, multivigenza=True, embeddings=True, bridge=True")
    print("   Rate limiting: 1s tra articoli, 3s ogni 5 articoli")
    print()

    start_time = time.time()

    for i, articolo in enumerate(articles):
        # Progress
        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        eta = (len(articles) - i - 1) / rate if rate > 0 else 0

        print(f"   [{i+1:2d}/{len(articles)}] Art. {articolo}...", end=" ", flush=True)

        try:
            # INGESTION CON TUTTI I FLAG ATTIVI
            result = await kg.ingest_norm(
                tipo_atto=TIPO_ATTO,
                articolo=articolo,
                include_brocardi=True,
                include_embeddings=True,
                include_bridge=True,
                include_multivigenza=True,
            )

            # Check for fatal errors
            if result.errors and any("Fatal" in e or "Error" in e for e in result.errors):
                metrics.articles_failed += 1
                metrics.errors.append({
                    "article": articolo,
                    "error": result.errors[0][:200] if result.errors else "Unknown error"
                })
                print(f"FAILED: {result.errors[0][:50]}...")
            else:
                metrics.articles_processed += 1
                metrics.nodes_created += len(result.nodes_created)
                metrics.chunks_created += result.chunks_created

                if result.brocardi_enriched:
                    metrics.brocardi_enriched += 1

                # Count multivigenza
                if hasattr(result, 'multivigenza_result') and result.multivigenza_result:
                    if result.multivigenza_result.atti_modificanti_creati:
                        metrics.multivigenza_enriched += 1

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

                status = "OK"
                if result.brocardi_enriched:
                    status += " +Brocardi"
                if result.warnings:
                    status += f" ({len(result.warnings)} warnings)"
                print(status)

        except Exception as e:
            metrics.articles_failed += 1
            metrics.errors.append({
                "article": articolo,
                "error": str(e)[:200]
            })
            print(f"EXCEPTION: {str(e)[:50]}...")

        # Rate limiting
        await asyncio.sleep(1.0)

        # Batch delay every 5 articles
        if (i + 1) % 5 == 0 and i < len(articles) - 1:
            print(f"         [Batch delay 3s - {rate:.2f} art/s, ETA: {eta:.0f}s]")
            await asyncio.sleep(3.0)


async def validate_results(kg: LegalKnowledgeGraph, metrics: EXP007Metrics) -> Dict[str, Any]:
    """Validazione rigorosa dei risultati."""
    print("\n" + "=" * 60)
    print("FASE 4: VALIDAZIONE RISULTATI")
    print("=" * 60)

    validation = {}

    # 1. Conteggio nodi per tipo
    print("\n1. Node counts by type...")
    result = await kg.falkordb.query("""
        MATCH (n)
        RETURN labels(n)[0] as label,
               n.tipo_documento as tipo,
               count(n) as cnt
        ORDER BY cnt DESC
    """)

    node_counts = {}
    for row in result:
        key = f"{row['label']}:{row['tipo']}" if row['tipo'] else row['label']
        node_counts[key] = row['cnt']
        print(f"      {key}: {row['cnt']}")

    validation["node_counts"] = node_counts
    metrics.nodes_norma = sum(v for k, v in node_counts.items() if 'Norma' in k)
    metrics.nodes_dottrina = node_counts.get('Dottrina:None', 0) + node_counts.get('Dottrina:ratio', 0) + node_counts.get('Dottrina:spiegazione', 0)
    metrics.nodes_atto_giudiziario = node_counts.get('AttoGiudiziario:None', 0) + node_counts.get('AttoGiudiziario:massima', 0)

    # 2. Conteggio relazioni per tipo
    print("\n2. Relation counts by type...")
    result = await kg.falkordb.query("""
        MATCH ()-[r]->()
        RETURN type(r) as rel, count(r) as cnt
        ORDER BY cnt DESC
    """)

    rel_counts = {}
    for row in result:
        rel_counts[row['rel']] = row['cnt']
        print(f"      {row['rel']}: {row['cnt']}")

    validation["relation_counts"] = rel_counts
    metrics.relations_created = sum(rel_counts.values())

    # 3. Articoli con Brocardi enrichment
    print("\n3. Articles with Brocardi enrichment...")
    result = await kg.falkordb.query("""
        MATCH (art:Norma {tipo_documento: 'articolo'})-[:commenta]-(d:Dottrina)
        RETURN art.numero_articolo as art, count(d) as dottrine
        ORDER BY art
    """)

    brocardi_arts = {row['art']: row['dottrine'] for row in result}
    print(f"      {len(brocardi_arts)}/{metrics.total_articles} articles with dottrina")
    validation["brocardi_enriched_articles"] = brocardi_arts

    # 4. Articoli con multivigenza
    print("\n4. Articles with multivigenza...")
    result = await kg.falkordb.query("""
        MATCH (art:Norma {tipo_documento: 'articolo'})<-[:modifica|abroga|sostituisce|inserisce]-(atto)
        RETURN art.numero_articolo as art, count(atto) as modifiche
        ORDER BY art
    """)

    multivigenza_arts = {row['art']: row['modifiche'] for row in result}
    print(f"      {len(multivigenza_arts)}/{metrics.total_articles} articles with modifiche")
    validation["multivigenza_articles"] = multivigenza_arts

    # 5. Verifica gerarchia
    print("\n5. Hierarchy verification (sample Art. 1453)...")
    result = await kg.falkordb.query("""
        MATCH path = (cc:Norma {tipo_documento: 'codice'})-[:contiene*]->(art:Norma {tipo_documento: 'articolo'})
        WHERE art.numero_articolo = '1453'
        RETURN [n in nodes(path) | n.titolo] as hierarchy
    """)

    if result:
        hierarchy = result[0]['hierarchy']
        print(f"      Hierarchy: {' -> '.join(str(h) for h in hierarchy if h)}")
        validation["sample_hierarchy"] = hierarchy
    else:
        print("      WARNING: No hierarchy found for Art. 1453!")
        validation["sample_hierarchy"] = None

    # 6. Qdrant verification
    print("\n6. Qdrant vectors...")
    if kg.qdrant:
        try:
            collection_info = await kg.qdrant.get_collection(GRAPH_NAME)
            vector_count = collection_info.vectors_count
            print(f"      Vectors in collection: {vector_count}")
            validation["qdrant_vectors"] = vector_count
            metrics.embeddings_created = vector_count
        except Exception as e:
            print(f"      ERROR: {e}")
            validation["qdrant_vectors"] = 0

    # 7. Bridge Table verification
    print("\n7. Bridge Table mappings...")
    if kg.bridge_table:
        try:
            async with kg.bridge_table.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM chunk_node_mapping")
                    total = (await cur.fetchone())[0]
                    print(f"      Total mappings: {total}")
                    validation["bridge_mappings"] = total
                    metrics.bridge_mappings = total
        except Exception as e:
            print(f"      ERROR: {e}")
            validation["bridge_mappings"] = 0

    return validation


async def main():
    parser = argparse.ArgumentParser(description="EXP-007: Full End-to-End Ingestion")
    parser.add_argument("--skip-reset", action="store_true", help="Skip database reset")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("=" * 70)
    print(f"EXP-007: ESPERIMENTO END-TO-END COMPLETO")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Graph: {GRAPH_NAME}")
    print(f"Articles: {TARGET_ARTICLES[0]}-{TARGET_ARTICLES[-1]} ({len(TARGET_ARTICLES)} articles)")
    print(f"Options: skip_reset={args.skip_reset}")

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***")
        print(f"\nWould process {len(TARGET_ARTICLES)} articles:")
        for art in TARGET_ARTICLES:
            print(f"  - Art. {art}")
        return

    # Initialize metrics
    metrics = EXP007Metrics()
    metrics.start_time = datetime.now().isoformat()
    metrics.total_articles = len(TARGET_ARTICLES)

    # Initialize LegalKnowledgeGraph
    print("\nConnecting to storage backends...")
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
    print(f"Connected to: FalkorDB ({GRAPH_NAME}), Qdrant, PostgreSQL")

    start_time = time.time()

    try:
        # Fase 1: Reset (opzionale)
        if not args.skip_reset:
            await reset_databases(kg)

        # Fase 2: Struttura base
        timestamp = datetime.now().isoformat()
        cc_urn, libro_urn = await create_codice_structure(kg, timestamp)

        # Fase 3: Ingestion articoli
        articles = [str(n) for n in TARGET_ARTICLES]
        await ingest_articles(kg, articles, libro_urn, metrics)

        # Fase 4: Validazione
        validation = await validate_results(kg, metrics)

    finally:
        # Cleanup
        await kg.close()

    # Finalize metrics
    metrics.end_time = datetime.now().isoformat()
    metrics.duration_seconds = time.time() - start_time

    # Save results
    print("\n" + "=" * 60)
    print("FASE 5: SALVATAGGIO RISULTATI")
    print("=" * 60)

    results_path = Path("docs/experiments/exp007_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)

    results = {
        "experiment": EXPERIMENT_NAME,
        "description": "End-to-End ingestion with all components active",
        "config": {
            "graph": GRAPH_NAME,
            "articles": f"{TARGET_ARTICLES[0]}-{TARGET_ARTICLES[-1]}",
            "flags": {
                "brocardi": True,
                "multivigenza": True,
                "embeddings": True,
                "bridge": True,
            }
        },
        "metrics": metrics.to_dict(),
        "validation": validation,
    }

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   Saved to: {results_path}")

    # Final Summary
    print("\n" + "=" * 70)
    print("EXP-007 COMPLETED")
    print("=" * 70)
    print(f"\nDuration: {metrics.duration_seconds:.1f}s ({metrics.duration_seconds/60:.1f} min)")
    print(f"\nArticles: {metrics.articles_processed}/{metrics.total_articles} "
          f"({metrics.articles_failed} failed)")
    print(f"Brocardi enriched: {metrics.brocardi_enriched}")
    print(f"Multivigenza enriched: {metrics.multivigenza_enriched}")
    print(f"\nGraph:")
    print(f"  - Nodes Norma: {metrics.nodes_norma}")
    print(f"  - Nodes Dottrina: {metrics.nodes_dottrina}")
    print(f"  - Nodes AttoGiudiziario: {metrics.nodes_atto_giudiziario}")
    print(f"  - Relations: {metrics.relations_created}")
    print(f"\nStorage:")
    print(f"  - Chunks: {metrics.chunks_created}")
    print(f"  - Embeddings (Qdrant): {metrics.embeddings_created}")
    print(f"  - Bridge mappings: {metrics.bridge_mappings}")

    if metrics.errors:
        print(f"\nErrors ({len(metrics.errors)}):")
        for err in metrics.errors[:5]:
            print(f"  - Art. {err['article']}: {err['error'][:60]}...")

    # Success criteria check
    print("\n" + "-" * 60)
    print("SUCCESS CRITERIA CHECK")
    print("-" * 60)
    criteria = [
        ("100% articles processed", metrics.articles_processed == metrics.total_articles),
        (">=80% Brocardi enriched", metrics.brocardi_enriched >= metrics.total_articles * 0.8),
        ("Graph has nodes", metrics.nodes_norma > 0),
        ("Embeddings created", metrics.embeddings_created > 0),
        ("Bridge mappings exist", metrics.bridge_mappings > 0),
    ]

    all_passed = True
    for name, passed in criteria:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("EXPERIMENT SUCCESS!")
    else:
        print("EXPERIMENT COMPLETED WITH ISSUES - Review results")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
