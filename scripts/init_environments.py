#!/usr/bin/env python3
"""
Initialize Test/Prod Environments
=================================

This script:
1. Deletes the existing merl_t_legal graph (legacy)
2. Creates merl_t_test graph (for experiments)
3. Creates merl_t_prod graph (for validated data)
4. Creates corresponding Qdrant collections
5. Optionally clears bridge table

Usage:
    # Initialize both environments (default)
    python scripts/init_environments.py

    # Initialize only test
    python scripts/init_environments.py --test-only

    # Skip legacy cleanup
    python scripts/init_environments.py --skip-legacy

    # Dry run (show what would be done)
    python scripts/init_environments.py --dry-run
"""

import argparse
import asyncio
from datetime import datetime

import asyncpg
from falkordb import FalkorDB
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Configuration
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

POSTGRES_DSN = "postgresql://dev:devpassword@localhost:5433/rlcf_dev"

# Legacy graph to delete
LEGACY_GRAPH = "merl_t_legal"

# New environments
ENVIRONMENTS = {
    "test": {
        "graph": "merl_t_test",
        "collection": "merl_t_test_chunks",
        "bridge_table": "bridge_table_test",
        "description": "Test environment for experiments",
    },
    "prod": {
        "graph": "merl_t_prod",
        "collection": "merl_t_prod_chunks",
        "bridge_table": "bridge_table_prod",
        "description": "Production environment with validated data",
    },
}

# Qdrant collection settings
EMBEDDING_DIM = 1024  # multilingual-e5-large
DISTANCE_METRIC = Distance.COSINE


def delete_graph(fb: FalkorDB, graph_name: str, dry_run: bool = False) -> bool:
    """Delete a FalkorDB graph if it exists."""
    try:
        # Check if graph exists by trying to select it
        graph = fb.select_graph(graph_name)

        # Try to count nodes - if graph exists, this will work
        try:
            result = graph.query("MATCH (n) RETURN count(n) as c")
            node_count = result.result_set[0][0] if result.result_set else 0
        except Exception:
            # Graph might be empty or doesn't exist
            node_count = 0

        if dry_run:
            print(f"   [DRY RUN] Would delete graph '{graph_name}' ({node_count} nodes)")
            return True

        # Delete all nodes and relationships
        if node_count > 0:
            graph.query("MATCH (n) DETACH DELETE n")

        # Delete the graph itself
        graph.delete()
        print(f"   Deleted graph '{graph_name}' ({node_count} nodes)")
        return True

    except Exception as e:
        if "does not exist" in str(e).lower() or "empty" in str(e).lower():
            print(f"   Graph '{graph_name}' does not exist (OK)")
            return True
        print(f"   Warning: Could not delete '{graph_name}': {e}")
        return False


def create_graph(fb: FalkorDB, graph_name: str, dry_run: bool = False) -> bool:
    """Create a new FalkorDB graph with initial schema."""
    try:
        if dry_run:
            print(f"   [DRY RUN] Would create graph '{graph_name}'")
            return True

        graph = fb.select_graph(graph_name)

        # Create initial constraints/indexes
        # FalkorDB uses different syntax than Neo4j
        # Syntax: CREATE INDEX ON :Label(property)
        try:
            graph.query("CREATE INDEX ON :Norma(URN)")
        except Exception:
            pass  # Index may already exist

        try:
            graph.query("CREATE INDEX ON :Norma(numero_articolo)")
        except Exception:
            pass

        try:
            graph.query("CREATE INDEX ON :Dottrina(article_urn)")
        except Exception:
            pass

        try:
            graph.query("CREATE INDEX ON :AttoGiudiziario(numero)")
        except Exception:
            pass

        print(f"   Created graph '{graph_name}' with indexes")
        return True

    except Exception as e:
        print(f"   Error creating graph '{graph_name}': {e}")
        return False


def create_qdrant_collection(
    client: QdrantClient, collection_name: str, dry_run: bool = False
) -> bool:
    """Create a Qdrant collection if it doesn't exist."""
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if exists:
            # Get collection info
            info = client.get_collection(collection_name)
            point_count = info.points_count
            print(f"   Collection '{collection_name}' exists ({point_count} points)")

            if dry_run:
                print(f"   [DRY RUN] Would recreate collection '{collection_name}'")
                return True

            # Delete and recreate
            client.delete_collection(collection_name)
            print(f"   Deleted collection '{collection_name}'")

        if dry_run:
            print(f"   [DRY RUN] Would create collection '{collection_name}'")
            return True

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=DISTANCE_METRIC,
            ),
        )

        # Create payload indexes for efficient filtering
        client.create_payload_index(
            collection_name=collection_name,
            field_name="node_type",
            field_schema="keyword",
        )

        client.create_payload_index(
            collection_name=collection_name,
            field_name="urn",
            field_schema="keyword",
        )

        client.create_payload_index(
            collection_name=collection_name,
            field_name="fonte",
            field_schema="keyword",
        )

        print(f"   Created collection '{collection_name}' ({EMBEDDING_DIM}d, cosine)")
        return True

    except Exception as e:
        print(f"   Error with collection '{collection_name}': {e}")
        return False


async def create_bridge_table(dsn: str, table_name: str, dry_run: bool = False) -> bool:
    """Create a bridge table for the environment."""
    try:
        if dry_run:
            print(f"   [DRY RUN] Would create bridge table '{table_name}'")
            return True

        conn = await asyncpg.connect(dsn)

        # Check if table exists and get count
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
            table_name
        )

        if exists:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"   Bridge table '{table_name}' exists ({count} rows)")
            # Drop and recreate
            await conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            print(f"   Dropped table '{table_name}'")
        else:
            print(f"   Bridge table '{table_name}' does not exist, will create")

        # Create table with full schema
        create_sql = f"""
        CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            chunk_id UUID NOT NULL,
            chunk_text TEXT,
            graph_node_urn VARCHAR(500) NOT NULL,
            node_type VARCHAR(50) NOT NULL,
            relation_type VARCHAR(50),
            confidence FLOAT,
            source VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            metadata JSONB,
            CONSTRAINT {table_name}_chunk_id_graph_node_urn_key UNIQUE (chunk_id, graph_node_urn),
            CONSTRAINT {table_name}_confidence_check CHECK (confidence >= 0 AND confidence <= 1)
        )
        """
        await conn.execute(create_sql)

        # Create indexes
        await conn.execute(f"CREATE INDEX {table_name}_chunk_id_idx ON {table_name}(chunk_id)")
        await conn.execute(f"CREATE INDEX {table_name}_graph_node_urn_idx ON {table_name}(graph_node_urn)")
        await conn.execute(f"CREATE INDEX {table_name}_node_type_idx ON {table_name}(node_type)")

        await conn.close()

        print(f"   Created bridge table '{table_name}' with indexes")
        return True

    except Exception as e:
        print(f"   Error creating bridge table '{table_name}': {e}")
        return False


async def clear_bridge_table(dsn: str, dry_run: bool = False) -> bool:
    """Clear the legacy bridge table (backward compatibility)."""
    try:
        if dry_run:
            print("   [DRY RUN] Would clear legacy bridge table")
            return True

        conn = await asyncpg.connect(dsn)

        # Check if table exists
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bridge_table')"
        )

        if exists:
            count = await conn.fetchval("SELECT COUNT(*) FROM bridge_table")
            await conn.execute("DELETE FROM bridge_table")
            print(f"   Cleared legacy bridge table ({count} rows deleted)")
        else:
            print("   Legacy bridge table does not exist (OK)")

        await conn.close()
        return True

    except Exception as e:
        print(f"   Error clearing legacy bridge table: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Initialize MERL-T test/prod environments")
    parser.add_argument("--test-only", action="store_true", help="Only initialize test environment")
    parser.add_argument("--prod-only", action="store_true", help="Only initialize prod environment")
    parser.add_argument("--skip-legacy", action="store_true", help="Skip deletion of legacy merl_t_legal")
    parser.add_argument("--skip-bridge", action="store_true", help="Skip bridge table cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")

    args = parser.parse_args()

    print("=" * 70)
    print("MERL-T ENVIRONMENT INITIALIZATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Connect to services
    print("\n1. Connecting to services...")

    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    print(f"   FalkorDB: {FALKORDB_HOST}:{FALKORDB_PORT}")

    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"   Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")

    # Step 2: Delete legacy graph
    if not args.skip_legacy:
        print(f"\n2. Deleting legacy graph '{LEGACY_GRAPH}'...")
        delete_graph(fb, LEGACY_GRAPH, dry_run=args.dry_run)

        # Also delete legacy Qdrant collection
        legacy_collection = "merl_t_chunks"
        try:
            collections = qdrant.get_collections().collections
            if any(c.name == legacy_collection for c in collections):
                if args.dry_run:
                    print(f"   [DRY RUN] Would delete collection '{legacy_collection}'")
                else:
                    qdrant.delete_collection(legacy_collection)
                    print(f"   Deleted legacy collection '{legacy_collection}'")
            else:
                print(f"   Legacy collection '{legacy_collection}' not found (OK)")
        except Exception as e:
            print(f"   Warning: Could not check/delete legacy collection: {e}")
    else:
        print("\n2. Skipping legacy cleanup (--skip-legacy)")

    # Step 3: Create new environments
    print("\n3. Creating new environments...")

    envs_to_create = []
    if args.test_only:
        envs_to_create = ["test"]
    elif args.prod_only:
        envs_to_create = ["prod"]
    else:
        envs_to_create = ["test", "prod"]

    for env_name in envs_to_create:
        env = ENVIRONMENTS[env_name]
        print(f"\n   --- {env_name.upper()} Environment ---")
        print(f"   {env['description']}")

        # Create graph
        create_graph(fb, env["graph"], dry_run=args.dry_run)

        # Create Qdrant collection
        create_qdrant_collection(qdrant, env["collection"], dry_run=args.dry_run)

        # Create bridge table for this environment
        await create_bridge_table(POSTGRES_DSN, env["bridge_table"], dry_run=args.dry_run)

    # Step 4: Clear legacy bridge table (if exists)
    if not args.skip_bridge:
        print("\n4. Cleaning up legacy bridge table...")
        await clear_bridge_table(POSTGRES_DSN, dry_run=args.dry_run)
    else:
        print("\n4. Skipping legacy bridge table cleanup (--skip-bridge)")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if args.dry_run:
        print("\n*** DRY RUN - No changes were made ***")
        print("\nRun without --dry-run to execute changes.")
    else:
        print("\nEnvironments ready:")
        for env_name in envs_to_create:
            env = ENVIRONMENTS[env_name]
            print(f"\n  {env_name.upper()}:")
            print(f"    Graph: {env['graph']}")
            print(f"    Collection: {env['collection']}")
            print(f"    Bridge Table: {env['bridge_table']}")

        print("\nUsage:")
        print("  from merlt.config import get_environment_config, TEST_ENV")
        print("  config = get_environment_config(TEST_ENV)")
        print("  print(config.falkordb_graph)  # 'merl_t_test'")
        print("")
        print("  # Per bridge table con ambiente:")
        print("  from merlt.storage.bridge import BridgeTable, BridgeTableConfig")
        print("  config = BridgeTableConfig.from_environment(get_environment_config(TEST_ENV))")
        print("  # oppure: config = BridgeTableConfig.for_test()")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
