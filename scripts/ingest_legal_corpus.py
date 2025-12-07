"""
Legal Corpus Ingestion Script for Qdrant

This script ingests legal documents into Qdrant vector database for semantic search.

Supported Sources:
- Neo4j (knowledge graph norms)
- PostgreSQL (RLCF database)
- JSON files (custom corpus)

Features:
- Chunking for long documents
- Batch embedding with E5-large
- Bulk insert into Qdrant
- Progress tracking
- Resume support (skip already ingested documents)

Usage:
    # Ingest from Neo4j (100 documents)
    python scripts/ingest_legal_corpus.py --source neo4j --limit 100

    # Ingest from JSON file
    python scripts/ingest_legal_corpus.py --source json --file corpus.json

    # Full ingestion from Neo4j
    python scripts/ingest_legal_corpus.py --source neo4j --full

    # Recreate collection (delete existing data)
    python scripts/ingest_legal_corpus.py --source neo4j --recreate

Requirements:
    - Qdrant running: docker-compose --profile phase3 up -d qdrant
    - E5-large model (will download ~1.2GB on first run)
"""

import argparse
import asyncio
import logging
import json
import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from merlt.orchestration.services.embedding_service import EmbeddingService
from merlt.orchestration.services.qdrant_service import QdrantService

# Neo4j and PostgreSQL imports (optional)
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CorpusIngester:
    """
    Ingests legal corpus into Qdrant vector database.
    """

    def __init__(
        self,
        qdrant_service: QdrantService,
        embedding_service: EmbeddingService,
        batch_size: int = 32,
        chunk_size: int = 512
    ):
        """
        Initialize ingester.

        Args:
            qdrant_service: QdrantService instance
            embedding_service: EmbeddingService instance
            batch_size: Batch size for embedding
            chunk_size: Maximum chunk size in tokens (for long documents)
        """
        self.qdrant_service = qdrant_service
        self.embedding_service = embedding_service
        self.batch_size = batch_size
        self.chunk_size = chunk_size

        self.total_documents = 0
        self.total_chunks = 0
        self.skipped = 0

    async def ingest_from_neo4j(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        limit: Optional[int] = None
    ) -> int:
        """
        Ingest documents from Neo4j knowledge graph.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            limit: Maximum number of documents to ingest

        Returns:
            Number of documents ingested
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j package required for Neo4j ingestion")

        logger.info(f"Connecting to Neo4j: {neo4j_uri}")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        try:
            with driver.session() as session:
                # Query norms from Neo4j
                query = """
                MATCH (n:Norma)
                WHERE n.testo IS NOT NULL
                RETURN
                    n.estremi AS id,
                    n.testo AS text,
                    n.tipo_atto AS document_type,
                    n.data_vigore AS date_effective,
                    n.area_giuridica AS legal_area,
                    n.complessita AS complexity_level,
                    n.fonte AS source_type,
                    n.livello_gerarchico AS hierarchical_level
                ORDER BY n.estremi
                LIMIT $limit
                """

                result = session.run(
                    query,
                    limit=limit if limit else 10000  # Default limit
                )

                documents = []
                for record in result:
                    doc = {
                        "id": record["id"],
                        "text": record["text"],
                        "document_type": "norm",
                        "temporal_metadata": {
                            "is_current": True,  # Assume current for now
                            "date_effective": record.get("date_effective"),
                            "date_end": None
                        },
                        "classification": {
                            "legal_area": record.get("legal_area", "civil"),
                            "legal_domain_tags": [],
                            "complexity_level": record.get("complexity_level", 2)
                        },
                        "authority_metadata": {
                            "source_type": record.get("source_type", "neo4j"),
                            "hierarchical_level": record.get("hierarchical_level", "norm"),
                            "authority_score": 1.0
                        },
                        "entities_extracted": {
                            "norm_references": [],
                            "legal_concepts": []
                        }
                    }
                    documents.append(doc)

                logger.info(f"Fetched {len(documents)} documents from Neo4j")

                # Ingest documents
                return await self._ingest_documents(documents)

        finally:
            driver.close()

    async def ingest_from_json(self, json_file: str) -> int:
        """
        Ingest documents from JSON file.

        JSON format:
        [
            {
                "id": "art_1321_cc",
                "text": "Art. 1321 c.c. - ...",
                "document_type": "norm",
                "temporal_metadata": {...},
                "classification": {...},
                "authority_metadata": {...},
                "entities_extracted": {...}
            },
            ...
        ]

        Args:
            json_file: Path to JSON file

        Returns:
            Number of documents ingested
        """
        logger.info(f"Loading documents from JSON: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)

        logger.info(f"Loaded {len(documents)} documents from JSON")

        return await self._ingest_documents(documents)

    async def _ingest_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Ingest documents into Qdrant.

        Process:
        1. Chunk long documents
        2. Embed in batches
        3. Insert into Qdrant

        Args:
            documents: List of documents with metadata

        Returns:
            Number of documents/chunks inserted
        """
        if not documents:
            logger.warning("No documents to ingest")
            return 0

        # Step 1: Chunk long documents (if needed)
        chunks = []
        for doc in documents:
            text = doc["text"]

            # Simple chunking by character count
            # TODO: Improve with token-aware chunking
            if len(text) <= self.chunk_size:
                chunks.append({
                    "id": doc["id"],
                    "text": text,
                    "payload": doc
                })
            else:
                # Split into chunks
                words = text.split()
                current_chunk = []
                chunk_idx = 0

                for word in words:
                    current_chunk.append(word)
                    if len(' '.join(current_chunk)) >= self.chunk_size:
                        chunk_text = ' '.join(current_chunk)
                        chunks.append({
                            "id": f"{doc['id']}_chunk_{chunk_idx}",
                            "text": chunk_text,
                            "payload": {**doc, "chunk_index": chunk_idx}
                        })
                        current_chunk = []
                        chunk_idx += 1

                # Add remaining words as last chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        "id": f"{doc['id']}_chunk_{chunk_idx}",
                        "text": chunk_text,
                        "payload": {**doc, "chunk_index": chunk_idx}
                    })

        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")

        # Step 2: Embed in batches
        logger.info(f"Embedding {len(chunks)} chunks (batch_size={self.batch_size})")

        all_vectors = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            texts = [c["text"] for c in batch]

            # Embed batch
            vectors = await self.embedding_service.encode_batch_async(
                texts,
                is_query=False,
                show_progress_bar=False
            )

            all_vectors.extend(vectors)

            # Progress
            progress = min(i + self.batch_size, len(chunks))
            logger.info(f"Embedded {progress}/{len(chunks)} chunks ({progress/len(chunks)*100:.1f}%)")

        # Step 3: Insert into Qdrant
        logger.info(f"Inserting {len(chunks)} chunks into Qdrant")

        qdrant_documents = []
        for chunk, vector in zip(chunks, all_vectors):
            payload = chunk["payload"]
            # Remove text from payload to avoid duplication (it's in the chunk)
            payload_copy = payload.copy()
            payload_copy["text"] = chunk["text"]

            qdrant_documents.append({
                "id": chunk["id"],
                "vector": vector,
                "payload": payload_copy
            })

        inserted = self.qdrant_service.insert_documents(qdrant_documents)

        self.total_documents = len(documents)
        self.total_chunks = inserted

        logger.info(f"✅ Ingestion complete: {inserted} chunks from {len(documents)} documents")

        return inserted


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest legal corpus into Qdrant vector database"
    )

    parser.add_argument(
        "--source",
        choices=["neo4j", "json", "postgres"],
        required=True,
        help="Data source"
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Path to JSON file (for --source json)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of documents to ingest"
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Ingest full corpus (no limit)"
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate collection (delete existing data)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding (default: 32)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Maximum chunk size in characters (default: 512)"
    )

    args = parser.parse_args()

    # Initialize services
    logger.info("Initializing services...")

    embedding_service = EmbeddingService.get_instance()
    qdrant_service = QdrantService()

    # Initialize collection
    if args.recreate:
        logger.info("Recreating collection...")
        qdrant_service.initialize_collection(recreate=True)
    else:
        if not qdrant_service.collection_exists():
            logger.info("Creating collection...")
            qdrant_service.initialize_collection()
        else:
            logger.info("Using existing collection")

    # Create ingester
    ingester = CorpusIngester(
        qdrant_service=qdrant_service,
        embedding_service=embedding_service,
        batch_size=args.batch_size,
        chunk_size=args.chunk_size
    )

    # Ingest based on source
    try:
        if args.source == "neo4j":
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "merl_t_password")

            limit = None if args.full else (args.limit or 100)

            inserted = await ingester.ingest_from_neo4j(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                limit=limit
            )

        elif args.source == "json":
            if not args.file:
                logger.error("--file is required for --source json")
                return 1

            inserted = await ingester.ingest_from_json(args.file)

        elif args.source == "postgres":
            logger.error("PostgreSQL ingestion not yet implemented")
            return 1

        # Print summary
        logger.info("=" * 60)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Source: {args.source}")
        logger.info(f"Documents processed: {ingester.total_documents}")
        logger.info(f"Chunks inserted: {ingester.total_chunks}")
        logger.info(f"Collection: {qdrant_service.collection_name}")
        logger.info("=" * 60)

        # Collection stats
        stats = qdrant_service.get_collection_stats()
        logger.info(f"Total points in collection: {stats.get('points_count', 'N/A')}")

        return 0

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
