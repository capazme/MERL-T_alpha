#!/usr/bin/env python3
"""
Test infrastructure imports for Week 5 Day 3 components.
"""

import sys

def test_imports():
    """Test that all new infrastructure components can be imported."""

    print("Testing infrastructure imports...")
    errors = []

    # Test Neo4j connection manager
    try:
        from backend.preprocessing.neo4j_connection import Neo4jConnectionManager, get_neo4j_driver
        print("✓ Neo4j connection manager imported successfully")
    except Exception as e:
        errors.append(f"✗ Neo4j connection import failed: {str(e)}")
        print(errors[-1])

    # Test Redis connection manager
    try:
        from backend.preprocessing.redis_connection import RedisConnectionManager, get_redis_client
        print("✓ Redis connection manager imported successfully")
    except Exception as e:
        errors.append(f"✗ Redis connection import failed: {str(e)}")
        print(errors[-1])

    # Test KG config loader
    try:
        from backend.preprocessing.config.kg_config import (
            KGConfig,
            Neo4jConfig,
            RedisConfig,
            load_kg_config,
            get_kg_config
        )
        print("✓ KG config loader imported successfully")
    except Exception as e:
        errors.append(f"✗ KG config import failed: {str(e)}")
        print(errors[-1])

    # Test intent mapping
    try:
        from backend.preprocessing.intent_mapping import (
            convert_query_intent_to_intent_type,
            convert_intent_type_to_query_intent,
            prepare_query_understanding_for_kg_enrichment
        )
        print("✓ Intent mapping imported successfully")
    except Exception as e:
        errors.append(f"✗ Intent mapping import failed: {str(e)}")
        print(errors[-1])

    # Test updated pipeline integration
    try:
        from backend.rlcf_framework.pipeline_integration import (
            initialize_pipeline_components,
            shutdown_pipeline_components,
            create_pipeline_router
        )
        print("✓ Pipeline integration imported successfully")
    except Exception as e:
        errors.append(f"✗ Pipeline integration import failed: {str(e)}")
        print(errors[-1])

    # Summary
    print("\n" + "="*60)
    if errors:
        print(f"❌ {len(errors)} import errors found:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("✅ All infrastructure imports successful!")
        return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
