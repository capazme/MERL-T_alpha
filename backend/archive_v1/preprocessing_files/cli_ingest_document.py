#!/usr/bin/env python3
"""
Document Ingestion CLI
======================

Command-line tool for ingesting legal documents into the Knowledge Graph.

Usage:
    python cli_ingest_document.py --file "manual.pdf" --dry-run
    python cli_ingest_document.py --file "manual.pdf" --max-segments 5
    python cli_ingest_document.py --directory "docs/" --pattern "*.pdf"
"""

import asyncio
import argparse
import sys
import yaml
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from backend.preprocessing.document_ingestion import IngestionPipeline


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest legal documents into MERL-T Knowledge Graph"
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Path to document file to ingest"
    )

    parser.add_argument(
        "--directory",
        type=str,
        help="Directory containing documents to ingest"
    )

    parser.add_argument(
        "--pattern",
        type=str,
        default="*.pdf",
        help="Glob pattern for files in directory (default: *.pdf)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract entities but don't write to Neo4j"
    )

    parser.add_argument(
        "--max-segments",
        type=int,
        default=None,
        help="Limit number of segments to process (for testing)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override LLM model (e.g., 'openai/gpt-4-turbo')"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="backend/preprocessing/kg_config.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Validation
    if not args.file and not args.directory:
        parser.error("Either --file or --directory must be specified")

    # Load environment variables
    load_dotenv()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Override model if specified
    if args.model:
        config["document_ingestion"]["llm"]["model"] = args.model

    # Get API keys from environment
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        print("Set it in .env file or export it:")
        print("  export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    neo4j_uri = os.getenv("NEO4J_URI", config["neo4j"]["uri"])
    neo4j_user = os.getenv("NEO4J_USER", config["neo4j"]["user"])
    neo4j_password = os.getenv("NEO4J_PASSWORD", config["neo4j"]["password"])
    neo4j_database = os.getenv("NEO4J_DATABASE", config["neo4j"]["database"])

    # Create Neo4j driver
    print(f"Connecting to Neo4j at {neo4j_uri}...")
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )

    try:
        # Verify connection
        async with driver.session(database=neo4j_database) as session:
            result = await session.run("RETURN 1 as test")
            await result.single()
        print("✓ Neo4j connection successful")

        # Create pipeline
        pipeline = IngestionPipeline(
            neo4j_driver=driver,
            openrouter_api_key=openrouter_api_key,
            config=config.get("document_ingestion", {})
        )

        # Run ingestion
        if args.file:
            # Single file
            print(f"\nIngesting file: {args.file}")
            print(f"Dry run: {args.dry_run}")
            if args.max_segments:
                print(f"Max segments: {args.max_segments}")

            result = await pipeline.ingest_document(
                file_path=Path(args.file),
                dry_run=args.dry_run,
                max_segments=args.max_segments,
            )

            # Print results
            print("\n")
            result.print_summary()

        else:
            # Directory batch
            print(f"\nIngesting directory: {args.directory}")
            print(f"Pattern: {args.pattern}")
            print(f"Dry run: {args.dry_run}")

            results = await pipeline.ingest_directory(
                directory=Path(args.directory),
                pattern=args.pattern,
                dry_run=args.dry_run,
                max_segments=args.max_segments,
            )

            print(f"\nProcessed {len(results)} files")

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
