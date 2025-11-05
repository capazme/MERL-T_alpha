#!/usr/bin/env python3
"""
Neo4j Connection Test Script
=============================

Tests backend connectivity to Neo4j and verifies schema.

Usage:
    python infrastructure/scripts/test_neo4j_connection.py

Requirements:
    pip install neo4j python-dotenv
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


def test_neo4j_connection():
    """Test Neo4j connection and schema."""

    print("=" * 60)
    print("MERL-T Neo4j Connection Test")
    print("=" * 60)
    print()

    # Load environment variables
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print(f"⚠ No .env file found, using defaults")

    # Get Neo4j credentials
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "merl_t_password")
    database = os.getenv("NEO4J_DATABASE", "merl-t-kg")

    print()
    print("Configuration:")
    print(f"  URI: {uri}")
    print(f"  User: {user}")
    print(f"  Database: {database}")
    print()

    # Test connection
    print("Step 1: Testing connection...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✓ Connection successful")
    except ServiceUnavailable as e:
        print(f"✗ Connection failed: {e}")
        print()
        print("Make sure Neo4j is running:")
        print("  docker-compose --profile phase2 up -d neo4j")
        sys.exit(1)
    except AuthError as e:
        print(f"✗ Authentication failed: {e}")
        print()
        print("Check your credentials in .env file")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)

    print()

    # Test database access
    print("Step 2: Testing database access...")
    try:
        with driver.session(database=database) as session:
            result = session.run("RETURN 1 AS test")
            record = result.single()
            if record and record["test"] == 1:
                print(f"✓ Database '{database}' is accessible")
            else:
                print(f"✗ Unexpected result from test query")
                sys.exit(1)
    except Exception as e:
        print(f"✗ Database access failed: {e}")
        print()
        print(f"Make sure database '{database}' exists")
        sys.exit(1)

    print()

    # Check constraints
    print("Step 3: Checking constraints...")
    try:
        with driver.session(database=database) as session:
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            if constraints:
                print(f"✓ Found {len(constraints)} constraints:")
                for constraint in constraints:
                    print(f"  - {constraint.get('name', 'unnamed')}: {constraint.get('type', 'unknown')}")
            else:
                print("⚠ No constraints found (schema may not be loaded)")
    except Exception as e:
        print(f"✗ Failed to check constraints: {e}")

    print()

    # Check indexes
    print("Step 4: Checking indexes...")
    try:
        with driver.session(database=database) as session:
            result = session.run("SHOW INDEXES")
            indexes = list(result)
            if indexes:
                print(f"✓ Found {len(indexes)} indexes:")
                for index in indexes:
                    print(f"  - {index.get('name', 'unnamed')}: {index.get('type', 'unknown')}")
            else:
                print("⚠ No indexes found (schema may not be loaded)")
    except Exception as e:
        print(f"✗ Failed to check indexes: {e}")

    print()

    # Count nodes
    print("Step 5: Counting nodes by label...")
    try:
        with driver.session(database=database) as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
                ORDER BY count DESC
            """)
            nodes = list(result)
            if nodes:
                print(f"✓ Found nodes:")
                total_count = 0
                for node in nodes:
                    label = node["label"]
                    count = node["count"]
                    print(f"  - {label}: {count}")
                    total_count += count
                print(f"  Total: {total_count} nodes")
            else:
                print("⚠ No nodes found (data may not be loaded)")
    except Exception as e:
        print(f"✗ Failed to count nodes: {e}")

    print()

    # Test sample data
    print("Step 6: Testing sample data (Art. 1321 c.c.)...")
    try:
        with driver.session(database=database) as session:
            result = session.run("""
                MATCH (a:Articolo {id: 'cc_art_1321'})
                RETURN a.numero AS numero, a.titolo AS titolo
            """)
            record = result.single()
            if record:
                print(f"✓ Found sample article:")
                print(f"  Numero: {record['numero']}")
                print(f"  Titolo: {record['titolo']}")
            else:
                print("⚠ Sample article not found (schema may not be loaded)")
                print()
                print("Load schema with:")
                print("  ./infrastructure/scripts/setup_neo4j.sh")
    except Exception as e:
        print(f"✗ Failed to query sample data: {e}")

    print()

    # Test relationships
    print("Step 7: Testing relationships...")
    try:
        with driver.session(database=database) as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS rel_type, count(*) AS count
                ORDER BY count DESC
                LIMIT 10
            """)
            relationships = list(result)
            if relationships:
                print(f"✓ Found relationships:")
                for rel in relationships:
                    print(f"  - {rel['rel_type']}: {rel['count']}")
            else:
                print("⚠ No relationships found")
    except Exception as e:
        print(f"✗ Failed to query relationships: {e}")

    print()

    # Close driver
    driver.close()

    # Success summary
    print("=" * 60)
    print("✓ Neo4j Connection Test Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run data ingestion scripts to load 5,000+ articles")
    print("2. Test KG enrichment service with sample queries")
    print("3. Run full pipeline integration tests")
    print()


if __name__ == "__main__":
    try:
        test_neo4j_connection()
    except KeyboardInterrupt:
        print()
        print("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
