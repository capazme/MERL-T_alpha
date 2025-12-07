#!/usr/bin/env python3
"""
EXP-005: Ingest L.241/1990 Capo I con Multivigenza
==================================================

Questo script:
1. Cancella dati esistenti nel grafo test
2. Fetch 9 articoli del Capo I da Normattiva
3. Crea nodi Norma nel grafo
4. Applica MultivigenzaPipeline per tracciare tutte le modifiche
5. Genera report di validazione

Dataset:
- Art. 1, 1-bis, 1-ter
- Art. 2, 2-bis, 2-ter, 2-quater
- Art. 3, 3-bis

Usage:
    python scripts/ingest_241_multivigenza.py

    # Solo fetch senza multivigenza
    python scripts/ingest_241_multivigenza.py --skip-multivigenza

    # Dry run (mostra cosa farebbe)
    python scripts/ingest_241_multivigenza.py --dry-run
"""

import asyncio
import argparse
from datetime import datetime
from typing import List, Tuple

from falkordb import FalkorDB

# Imports locali
import sys
sys.path.insert(0, '.')

from merlt.external_sources.visualex.tools.norma import NormaVisitata, Norma
from merlt.external_sources.visualex.scrapers.normattiva_scraper import NormattivaScraper
from merlt.preprocessing.multivigenza_pipeline import MultivigenzaPipeline
from merlt.storage import FalkorDBClient, FalkorDBConfig


# Configurazione
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380
GRAPH_NAME = "merl_t_test"  # Usa grafo test

# Articoli del Capo I - Principi (5 articoli)
# Verificato da Normattiva: Art. 1-3-bis
ARTICOLI_CAPO_I = [
    "1",
    "2",
    "2-bis",
    "3",
    "3-bis",
]


async def clear_test_graph():
    """Cancella tutti i dati dal grafo test."""
    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = fb.select_graph(GRAPH_NAME)

    # Conta nodi esistenti
    result = graph.query("MATCH (n) RETURN count(n) as c")
    count = result.result_set[0][0] if result.result_set else 0

    if count > 0:
        graph.query("MATCH (n) DETACH DELETE n")
        print(f"   Deleted {count} nodes from {GRAPH_NAME}")
    else:
        print(f"   Graph {GRAPH_NAME} already empty")


async def fetch_article(
    scraper: NormattivaScraper,
    numero_articolo: str,
) -> Tuple[NormaVisitata, str]:
    """
    Fetch un articolo da Normattiva.

    Returns:
        Tuple (NormaVisitata, testo_articolo)
    """
    norma = Norma(tipo_atto='legge', data='1990-08-07', numero_atto='241')
    nv = NormaVisitata(norma=norma, numero_articolo=numero_articolo)

    testo, urn = await scraper.get_document(nv)
    return nv, testo


async def create_article_node(
    client: FalkorDBClient,
    nv: NormaVisitata,
    testo: str,
    timestamp: str,
) -> None:
    """Crea nodo Norma per articolo nel grafo."""
    await client.query(
        """
        MERGE (art:Norma {URN: $urn})
        ON CREATE SET
            art.node_id = $urn,
            art.tipo_documento = 'articolo',
            art.numero_articolo = $numero,
            art.testo_vigente = $testo,
            art.fonte = 'Normattiva',
            art.created_at = $timestamp
        """,
        {
            "urn": nv.urn,
            "numero": nv.numero_articolo,
            "testo": testo,
            "timestamp": timestamp,
        }
    )


async def create_legge_node(
    client: FalkorDBClient,
    timestamp: str,
) -> str:
    """Crea nodo Norma per la legge 241/1990."""
    urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1990-08-07;241"

    await client.query(
        """
        MERGE (legge:Norma {URN: $urn})
        ON CREATE SET
            legge.node_id = $urn,
            legge.tipo_documento = 'legge',
            legge.titolo = 'Nuove norme sul procedimento amministrativo',
            legge.data_pubblicazione = '1990-08-07',
            legge.fonte = 'Normattiva',
            legge.created_at = $timestamp
        """,
        {"urn": urn, "timestamp": timestamp}
    )
    return urn


async def link_article_to_legge(
    client: FalkorDBClient,
    article_urn: str,
    legge_urn: str,
) -> None:
    """Crea relazione :contiene tra legge e articolo."""
    await client.query(
        """
        MATCH (legge:Norma {URN: $legge_urn})
        MATCH (art:Norma {URN: $art_urn})
        MERGE (legge)-[r:contiene]->(art)
        ON CREATE SET r.certezza = 1.0
        """,
        {"legge_urn": legge_urn, "art_urn": article_urn}
    )


async def run_validation_queries(client: FalkorDBClient) -> dict:
    """Esegue query di validazione e ritorna metriche."""
    metrics = {}

    # 1. Conteggio nodi
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

    # 2. Conteggio relazioni per tipo
    for rel_type in ['modifica', 'inserisce', 'abroga', 'sostituisce', 'contiene']:
        result = await client.query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as c")
        metrics[f'rel_{rel_type}'] = result[0]['c'] if result else 0

    # 3. Articoli bis/ter/quater
    result = await client.query("""
        MATCH (art:Norma {tipo_documento: 'articolo'})
        WHERE art.numero_articolo CONTAINS '-'
        RETURN art.numero_articolo as num
    """)
    metrics['bis_ter_articles'] = [r['num'] for r in result] if result else []

    return metrics


async def main():
    parser = argparse.ArgumentParser(description="EXP-005: Ingest L.241/1990 con multivigenza")
    parser.add_argument("--skip-multivigenza", action="store_true", help="Skip multivigenza processing")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--skip-clear", action="store_true", help="Don't clear existing data")

    args = parser.parse_args()

    print("=" * 70)
    print("EXP-005: INGEST L.241/1990 CAPO I CON MULTIVIGENZA")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Graph: {GRAPH_NAME}")
    print(f"Articles: {', '.join(ARTICOLI_CAPO_I)}")

    if args.dry_run:
        print("\n*** DRY RUN - No changes will be made ***")
        print(f"\nWould process {len(ARTICOLI_CAPO_I)} articles")
        print("Would create modifying act nodes and relations")
        return

    timestamp = datetime.now().isoformat()

    # 1. Clear graph
    print("\n1. Preparing test graph...")
    if not args.skip_clear:
        await clear_test_graph()
    else:
        print("   Skipping clear (--skip-clear)")

    # 2. Connect
    print("\n2. Connecting to services...")
    config = FalkorDBConfig(
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        graph_name=GRAPH_NAME,
    )
    client = FalkorDBClient(config)
    await client.connect()
    print(f"   FalkorDB: {GRAPH_NAME}")

    scraper = NormattivaScraper()
    print("   NormattivaScraper ready")

    # 3. Create legge node
    print("\n3. Creating L.241/1990 node...")
    legge_urn = await create_legge_node(client, timestamp)
    print(f"   Created: {legge_urn}")

    # 4. Fetch and create article nodes
    print(f"\n4. Fetching {len(ARTICOLI_CAPO_I)} articles...")
    articles_created = []

    for numero in ARTICOLI_CAPO_I:
        try:
            print(f"   Art. {numero}...", end=" ", flush=True)
            nv, testo = await fetch_article(scraper, numero)

            await create_article_node(client, nv, testo, timestamp)
            await link_article_to_legge(client, nv.urn, legge_urn)

            articles_created.append((nv, len(testo)))
            print(f"OK ({len(testo)} chars)")

        except Exception as e:
            print(f"ERROR: {e}")

    print(f"   Created {len(articles_created)} article nodes")

    # 5. Apply multivigenza
    if not args.skip_multivigenza:
        print("\n5. Applying multivigenza...")
        pipeline = MultivigenzaPipeline(falkordb_client=client, scraper=scraper)

        total_modifiche = 0
        total_atti = 0
        total_relazioni = 0

        for nv, _ in articles_created:
            print(f"   Art. {nv.numero_articolo}...", end=" ", flush=True)
            try:
                result = await pipeline.ingest_with_history(
                    nv,
                    fetch_all_versions=False,
                    create_modifying_acts=True,
                )

                n_mod = len(result.storia.modifiche) if result.storia else 0
                n_atti = len(result.atti_modificanti_creati)
                n_rel = len(result.relazioni_create)

                total_modifiche += n_mod
                total_atti += n_atti
                total_relazioni += n_rel

                print(f"{n_mod} modifiche, {n_atti} atti, {n_rel} relazioni")

            except Exception as e:
                print(f"ERROR: {e}")

        print(f"\n   Totals: {total_modifiche} modifiche, {total_atti} atti, {total_relazioni} relazioni")
    else:
        print("\n5. Skipping multivigenza (--skip-multivigenza)")

    # 6. Validation
    print("\n6. Validation queries...")
    metrics = await run_validation_queries(client)

    print(f"\n   Nodes:")
    print(f"     - Total: {metrics['total_nodes']}")
    print(f"     - Articles: {metrics['article_nodes']}")
    print(f"     - Modifying acts: {metrics['modifying_act_nodes']}")

    print(f"\n   Relations:")
    print(f"     - :contiene: {metrics['rel_contiene']}")
    print(f"     - :modifica: {metrics['rel_modifica']}")
    print(f"     - :inserisce: {metrics['rel_inserisce']}")
    print(f"     - :abroga: {metrics['rel_abroga']}")
    print(f"     - :sostituisce: {metrics['rel_sostituisce']}")

    print(f"\n   Bis/ter articles: {metrics['bis_ter_articles']}")

    # Cleanup
    await client.close()

    # Summary
    print("\n" + "=" * 70)
    print("EXP-005 COMPLETED")
    print("=" * 70)
    print(f"\nResults saved in graph: {GRAPH_NAME}")
    print("\nNext steps:")
    print("1. Verify results with FalkorDB browser")
    print("2. Update docs/experiments/EXP-005_multivigenza_241/RESULTS.md")
    print("3. Run validation queries from DESIGN.md")


if __name__ == "__main__":
    asyncio.run(main())
