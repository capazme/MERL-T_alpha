#!/usr/bin/env python3
"""
Quick test script for VisualeXClient integration.

Usage:
    # Start visualex API first
    cd visualex/src
    python -m visualex_api.main

    # Then run this test
    python backend/preprocessing/sources/test_visualex_client.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from preprocessing.sources.visualex_client import VisualeXClient
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger()


async def test_single_article():
    """Test fetching a single Codice Civile article."""
    log.info("=" * 60)
    log.info("TEST 1: Fetching single article (Art. 2043)")
    log.info("=" * 60)

    async with VisualeXClient(base_url="http://localhost:5000") as client:
        response = await client.fetch_articles(
            tipo_atto="codice civile",
            articoli=["2043"]
        )

        if response.success and response.data:
            article = response.data[0]
            print("\n✓ Article fetched successfully!")
            print(f"  Article: {article.numero_articolo}")
            print(f"  URN: {article.urn}")
            print(f"  Text length: {len(article.article_text) if article.article_text else 0} chars")
            print(f"\n  Text preview:")
            print(f"  {article.article_text[:200]}..." if article.article_text else "  (No text)")

            # Convert to Neo4j format
            neo4j_entity = article.to_neo4j_entity()
            print(f"\n✓ Converted to Neo4j entity:")
            print(f"  Entity type: {neo4j_entity['entity_type']}")
            print(f"  Confidence: {neo4j_entity['confidence']}")
            print(f"  Properties: {list(neo4j_entity['properties'].keys())}")

        else:
            print(f"\n✗ Fetch failed: {response.errors}")


async def test_batch_articles():
    """Test batch fetching multiple articles."""
    log.info("\n" + "=" * 60)
    log.info("TEST 2: Batch fetching articles 1-10")
    log.info("=" * 60)

    async with VisualeXClient(base_url="http://localhost:5000") as client:
        # Progress callback
        def progress_callback(current, total):
            percent = (current / total) * 100
            bar_length = 40
            filled = int(bar_length * current / total)
            bar = '█' * filled + '-' * (bar_length - filled)
            print(f'\r  Progress: [{bar}] {current}/{total} ({percent:.1f}%)', end='')

        response = await client.fetch_codice_civile_batch(
            start_article=1,
            end_article=10,
            batch_size=5,
            progress_callback=progress_callback
        )

        print()  # Newline after progress bar
        print(f"\n✓ Batch fetch complete!")
        print(f"  Total fetched: {response.total_fetched}")
        print(f"  Total errors: {response.total_errors}")

        if response.data:
            print(f"\n  Sample articles:")
            for article in response.data[:3]:
                title_line = article.article_text.split('\n')[1] if article.article_text and len(article.article_text.split('\n')) > 1 else "(No title)"
                print(f"    - Art. {article.numero_articolo}: {title_line[:50]}...")


async def test_error_handling():
    """Test error handling for invalid articles."""
    log.info("\n" + "=" * 60)
    log.info("TEST 3: Error handling (invalid article)")
    log.info("=" * 60)

    async with VisualeXClient(base_url="http://localhost:5000") as client:
        response = await client.fetch_articles(
            tipo_atto="codice civile",
            articoli=["99999"]  # Invalid article number
        )

        if response.errors:
            print(f"\n✓ Errors handled correctly:")
            for error in response.errors:
                print(f"  - {error}")
        else:
            print(f"\n  (No errors - article might exist)")


async def test_connection_failure():
    """Test connection failure handling."""
    log.info("\n" + "=" * 60)
    log.info("TEST 4: Connection failure handling (wrong port)")
    log.info("=" * 60)

    async with VisualeXClient(base_url="http://localhost:9999", max_retries=2) as client:
        try:
            response = await client.fetch_articles(
                tipo_atto="codice civile",
                articoli=["2043"]
            )
            print(f"\n✗ Should have failed but succeeded: {response}")
        except Exception as e:
            print(f"\n✓ Connection failure handled correctly:")
            print(f"  Error: {type(e).__name__}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("VISUALEX CLIENT INTEGRATION TESTS")
    print("=" * 60)
    print("\nMake sure visualex API is running on http://localhost:5000")
    print("(cd visualex/src && python -m visualex_api.main)\n")

    try:
        await test_single_article()
        await test_batch_articles()
        await test_error_handling()
        await test_connection_failure()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 60 + "\n")

    except Exception as e:
        log.error("Test suite failed", error=str(e), exc_info=True)
        print(f"\n✗ TEST SUITE FAILED: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
