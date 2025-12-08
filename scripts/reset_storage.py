#!/usr/bin/env python3
"""
Reset Storage per Ambiente
===========================

Script per pulire completamente e reinizializzare lo storage MERL-T.

Operazioni eseguite per ogni ambiente:
1. FalkorDB: Cancella tutti i nodi e relazioni dal graph
2. Qdrant: Elimina e ricrea la collection
3. PostgreSQL: Elimina e ricrea la bridge table

Usage:
    # Reset ambiente test (default, sicuro)
    python scripts/reset_storage.py --env test --confirm

    # Reset ambiente prod (ATTENZIONE!)
    python scripts/reset_storage.py --env prod --confirm

    # Reset entrambi gli ambienti
    python scripts/reset_storage.py --all --confirm

    # Dry-run (mostra cosa farebbe senza eseguire)
    python scripts/reset_storage.py --env test --dry-run

    # Solo un componente specifico
    python scripts/reset_storage.py --env test --only falkordb --confirm
    python scripts/reset_storage.py --env test --only qdrant --confirm
    python scripts/reset_storage.py --env test --only postgres --confirm
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.config.environments import (
    Environment, get_environment_config, TEST_ENV, PROD_ENV
)


async def reset_falkordb(env_config, dry_run: bool = False):
    """Reset FalkorDB graph per l'ambiente specificato."""
    from merlt.storage.graph import FalkorDBClient, FalkorDBConfig

    graph_name = env_config.falkordb_graph
    print(f"  [FalkorDB] Graph: {graph_name}")

    if dry_run:
        print(f"  [DRY-RUN] Would delete all nodes from graph '{graph_name}'")
        return {"status": "dry-run", "graph": graph_name}

    config = FalkorDBConfig(
        host=env_config.falkordb_host,
        port=env_config.falkordb_port,
        graph_name=graph_name
    )

    client = FalkorDBClient(config)
    await client.connect()

    try:
        # Conta nodi prima della cancellazione
        count_result = await client.execute_query("MATCH (n) RETURN count(n) as count")
        node_count = count_result[0]["count"] if count_result else 0
        print(f"  [FalkorDB] Nodi esistenti: {node_count}")

        # Cancella tutto
        await client.execute_query("MATCH (n) DETACH DELETE n")
        print(f"  [FalkorDB] ✓ Cancellati {node_count} nodi")

        return {"status": "success", "graph": graph_name, "deleted_nodes": node_count}

    finally:
        await client.close()


async def reset_qdrant(env_config, dry_run: bool = False):
    """Reset Qdrant collection per l'ambiente specificato."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    collection_name = env_config.qdrant_collection
    print(f"  [Qdrant] Collection: {collection_name}")

    if dry_run:
        print(f"  [DRY-RUN] Would delete and recreate collection '{collection_name}'")
        return {"status": "dry-run", "collection": collection_name}

    client = QdrantClient(
        host=env_config.qdrant_host,
        port=env_config.qdrant_port
    )

    try:
        # Verifica se collection esiste e conta punti
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name in collection_names:
            info = client.get_collection(collection_name)
            point_count = info.points_count
            print(f"  [Qdrant] Punti esistenti: {point_count}")

            # Elimina collection
            client.delete_collection(collection_name)
            print(f"  [Qdrant] ✓ Collection eliminata")
        else:
            point_count = 0
            print(f"  [Qdrant] Collection non esistente, verrà creata")

        # Ricrea collection con configurazione standard
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1024,  # multilingual-e5-large
                distance=Distance.COSINE
            )
        )
        print(f"  [Qdrant] ✓ Collection ricreata (1024d, cosine)")

        # Crea payload indexes
        client.create_payload_index(
            collection_name=collection_name,
            field_name="node_type",
            field_schema="keyword"
        )
        client.create_payload_index(
            collection_name=collection_name,
            field_name="urn",
            field_schema="keyword"
        )
        print(f"  [Qdrant] ✓ Payload indexes creati (node_type, urn)")

        return {"status": "success", "collection": collection_name, "deleted_points": point_count}

    finally:
        client.close()


async def reset_postgres(env_config, dry_run: bool = False):
    """Reset PostgreSQL bridge table per l'ambiente specificato."""
    from merlt.storage.bridge import BridgeTable, BridgeTableConfig

    table_name = f"bridge_table{env_config.bridge_table_suffix}"
    print(f"  [PostgreSQL] Table: {table_name}")

    if dry_run:
        print(f"  [DRY-RUN] Would drop and recreate table '{table_name}'")
        return {"status": "dry-run", "table": table_name}

    config = BridgeTableConfig(
        host="localhost",
        port=5433,
        database="rlcf_dev",
        table_name=table_name
    )

    bridge = BridgeTable(config)
    await bridge.connect()

    try:
        # Conta righe prima
        try:
            row_count = await bridge.count()
            print(f"  [PostgreSQL] Righe esistenti: {row_count}")
        except Exception:
            row_count = 0
            print(f"  [PostgreSQL] Tabella non esistente, verrà creata")

        # Drop e ricrea
        await bridge.drop_table()
        await bridge.ensure_table_exists()
        print(f"  [PostgreSQL] ✓ Tabella ricreata con indexes")

        return {"status": "success", "table": table_name, "deleted_rows": row_count}

    finally:
        await bridge.close()


async def reset_environment(env: Environment, dry_run: bool = False, only: str = None):
    """
    Reset completo di un ambiente.

    Args:
        env: Ambiente da resettare (TEST o PROD)
        dry_run: Se True, mostra cosa farebbe senza eseguire
        only: Se specificato, resetta solo quel componente (falkordb, qdrant, postgres)
    """
    env_config = get_environment_config(env)

    print(f"\n{'='*60}")
    print(f"RESET AMBIENTE: {env_config.name.upper()}")
    print(f"{'='*60}")
    print(f"Descrizione: {env_config.description}")

    results = {}

    components = ["falkordb", "qdrant", "postgres"]
    if only:
        components = [only]

    for component in components:
        print(f"\n--- {component.upper()} ---")
        try:
            if component == "falkordb":
                results["falkordb"] = await reset_falkordb(env_config, dry_run)
            elif component == "qdrant":
                results["qdrant"] = await reset_qdrant(env_config, dry_run)
            elif component == "postgres":
                results["postgres"] = await reset_postgres(env_config, dry_run)
        except Exception as e:
            print(f"  [ERROR] {e}")
            results[component] = {"status": "error", "error": str(e)}

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Reset storage MERL-T per ambiente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--env",
        choices=["test", "prod"],
        help="Ambiente da resettare"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset entrambi gli ambienti (test e prod)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Conferma l'operazione (richiesto per eseguire)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cosa farebbe senza eseguire"
    )
    parser.add_argument(
        "--only",
        choices=["falkordb", "qdrant", "postgres"],
        help="Resetta solo un componente specifico"
    )

    args = parser.parse_args()

    # Validazione argomenti
    if not args.env and not args.all:
        parser.error("Specificare --env test|prod oppure --all")

    if not args.confirm and not args.dry_run:
        print("\n⚠️  ATTENZIONE: Questa operazione cancellerà TUTTI i dati!")
        print("Usa --dry-run per vedere cosa farebbe")
        print("Usa --confirm per eseguire effettivamente")
        sys.exit(1)

    # Determina ambienti da processare
    environments = []
    if args.all:
        environments = [TEST_ENV, PROD_ENV]
    elif args.env == "test":
        environments = [TEST_ENV]
    elif args.env == "prod":
        # Doppia conferma per prod
        if not args.dry_run:
            print("\n🚨 STAI PER CANCELLARE DATI DI PRODUZIONE!")
            confirm = input("Digita 'ELIMINA PROD' per confermare: ")
            if confirm != "ELIMINA PROD":
                print("Operazione annullata")
                sys.exit(1)
        environments = [PROD_ENV]

    # Esegui reset
    async def run():
        all_results = {}
        for env in environments:
            results = await reset_environment(
                env,
                dry_run=args.dry_run,
                only=args.only
            )
            all_results[env.value] = results

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        for env_name, results in all_results.items():
            print(f"\n{env_name.upper()}:")
            for component, result in results.items():
                status = result.get("status", "unknown")
                if status == "success":
                    print(f"  ✓ {component}: OK")
                elif status == "dry-run":
                    print(f"  ○ {component}: dry-run")
                else:
                    print(f"  ✗ {component}: {result.get('error', 'unknown error')}")

    asyncio.run(run())
    print("\n✓ Completato")


if __name__ == "__main__":
    main()
