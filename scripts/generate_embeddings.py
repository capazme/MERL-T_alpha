#!/usr/bin/env python3
"""
Generate Embeddings for MERL-T Knowledge Base

This script:
1. Reads chunk mappings from the Bridge Table (PostgreSQL)
2. Fetches article texts from FalkorDB using URNs
3. Generates embeddings using multilingual-e5-large (local, MPS accelerated)
4. Stores embeddings in Qdrant vector database
5. Updates Bridge Table with chunk_text for caching

Usage:
    python scripts/generate_embeddings.py [--batch-size 32] [--collection merl_t_chunks]

Requirements:
    - FalkorDB running with populated Norma nodes
    - PostgreSQL running with bridge_table populated
    - Qdrant running on localhost:6333
    - sentence-transformers installed with torch MPS support
"""

import asyncio
import argparse
import logging
import sys
import os
from uuid import UUID
from typing import Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    CollectionStatus, OptimizersConfigDiff
)
from falkordb import FalkorDB

from merlt.orchestration.services.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ChunkMapping:
    """Bridge table chunk mapping."""
    id: int
    chunk_id: UUID
    graph_node_urn: str
    node_type: str
    chunk_text: Optional[str] = None


class EmbeddingGenerator:
    """Generate and store embeddings for MERL-T knowledge base."""

    def __init__(
        self,
        pg_dsn: str,
        falkordb_host: str = "localhost",
        falkordb_port: int = 6380,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "merl_t_chunks",
        batch_size: int = 32,
        device: str = "mps"
    ):
        self.pg_dsn = pg_dsn
        self.falkordb_host = falkordb_host
        self.falkordb_port = falkordb_port
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.device = device

        # Clients (initialized in setup)
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.falkordb: Optional[FalkorDB] = None
        self.qdrant: Optional[QdrantClient] = None
        self.embedding_service: Optional[EmbeddingService] = None

    async def setup(self):
        """Initialize all connections."""
        print("\n" + "=" * 60)
        print("MERL-T Embedding Generator")
        print("=" * 60)

        # 1. PostgreSQL
        print("\n[1/4] Connecting to PostgreSQL...")
        self.pg_pool = await asyncpg.create_pool(self.pg_dsn)
        async with self.pg_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM bridge_table")
            print(f"  ✓ Connected - {count} chunks in bridge_table")

        # 2. FalkorDB
        print("\n[2/4] Connecting to FalkorDB...")
        self.falkordb = FalkorDB(host=self.falkordb_host, port=self.falkordb_port)
        graph = self.falkordb.select_graph("merl_t_legal")
        result = graph.query("MATCH (n:Norma) RETURN count(n) as count")
        norma_count = result.result_set[0][0] if result.result_set else 0
        print(f"  ✓ Connected - {norma_count} Norma nodes")

        # 3. Qdrant
        print("\n[3/4] Connecting to Qdrant...")
        self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        collections = self.qdrant.get_collections()
        print(f"  ✓ Connected - {len(collections.collections)} existing collections")

        # 4. Embedding Service (with MPS)
        print("\n[4/4] Loading embedding model...")
        os.environ["EMBEDDING_DEVICE"] = self.device
        self.embedding_service = EmbeddingService.get_instance(device=self.device)

        # Force model loading to get dimension
        dim = self.embedding_service.embedding_dimension
        print(f"  ✓ Model loaded on {self.device}")
        print(f"  ✓ Embedding dimension: {dim}")

        return dim

    async def create_collection(self, dimension: int):
        """Create Qdrant collection if not exists."""
        collections = self.qdrant.get_collections()
        existing = [c.name for c in collections.collections]

        if self.collection_name in existing:
            print(f"\n  Collection '{self.collection_name}' already exists")
            # Get collection info
            info = self.qdrant.get_collection(self.collection_name)
            print(f"  Points count: {info.points_count}")

            # Ask to recreate or continue
            if info.points_count > 0:
                return False  # Skip, already has data
        else:
            print(f"\n  Creating collection '{self.collection_name}'...")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000  # Index after 10k points
                )
            )
            print(f"  ✓ Collection created with dimension {dimension}")

        return True

    async def get_chunks_without_embedding(self) -> list[ChunkMapping]:
        """Get all chunks from bridge table that need embedding."""
        async with self.pg_pool.acquire() as conn:
            # Get all unique chunk_id + URN pairs
            rows = await conn.fetch("""
                SELECT DISTINCT ON (chunk_id)
                    id, chunk_id, graph_node_urn, node_type, chunk_text
                FROM bridge_table
                WHERE node_type = 'Norma'
                ORDER BY chunk_id, id
            """)

            return [
                ChunkMapping(
                    id=row['id'],
                    chunk_id=row['chunk_id'],
                    graph_node_urn=row['graph_node_urn'],
                    node_type=row['node_type'],
                    chunk_text=row['chunk_text']
                )
                for row in rows
            ]

    def get_text_from_falkordb(self, urn: str) -> Optional[str]:
        """Fetch article text from FalkorDB by URN."""
        graph = self.falkordb.select_graph("merl_t_legal")

        result = graph.query(
            "MATCH (n:Norma {URN: $urn}) RETURN n.testo_vigente as testo",
            {'urn': urn}
        )

        if result.result_set and result.result_set[0][0]:
            return result.result_set[0][0]
        return None

    async def update_chunk_text(self, chunk_id: UUID, text: str):
        """Update chunk_text in bridge table for caching."""
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "UPDATE bridge_table SET chunk_text = $1 WHERE chunk_id = $2",
                text, chunk_id
            )

    async def generate_and_store(self):
        """Main pipeline: generate embeddings and store in Qdrant."""
        # Get chunks to process
        print("\n[5/7] Loading chunks from Bridge Table...")
        chunks = await self.get_chunks_without_embedding()
        print(f"  Found {len(chunks)} chunks to process")

        if not chunks:
            print("  No chunks to process!")
            return

        # Check which chunks already have embeddings in Qdrant
        print("\n[6/7] Checking existing embeddings in Qdrant...")
        existing_ids = set()
        try:
            # Scroll through all points to get IDs
            offset = None
            while True:
                result = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )
                points, offset = result
                for point in points:
                    existing_ids.add(str(point.id))
                if offset is None:
                    break
        except Exception:
            pass  # Collection might be empty

        print(f"  Found {len(existing_ids)} existing embeddings")

        # Filter out already processed chunks
        chunks_to_process = [c for c in chunks if str(c.chunk_id) not in existing_ids]
        print(f"  {len(chunks_to_process)} chunks need embedding")

        if not chunks_to_process:
            print("  All chunks already have embeddings!")
            return

        # Process in batches
        print(f"\n[7/7] Generating embeddings (batch size: {self.batch_size})...")
        total_processed = 0
        total_errors = 0

        for i in range(0, len(chunks_to_process), self.batch_size):
            batch = chunks_to_process[i:i + self.batch_size]

            # Fetch texts for this batch
            texts = []
            valid_chunks = []

            for chunk in batch:
                # Use cached text or fetch from FalkorDB
                if chunk.chunk_text:
                    text = chunk.chunk_text
                else:
                    text = self.get_text_from_falkordb(chunk.graph_node_urn)
                    if text:
                        # Cache for future use
                        await self.update_chunk_text(chunk.chunk_id, text)

                if text and len(text.strip()) > 10:  # Skip very short texts
                    texts.append(text)
                    valid_chunks.append(chunk)
                else:
                    total_errors += 1
                    logger.warning(f"No text for URN: {chunk.graph_node_urn}")

            if not texts:
                continue

            # Generate embeddings for batch
            try:
                embeddings = self.embedding_service.encode_batch(
                    texts,
                    is_query=False,  # These are documents, not queries
                    show_progress_bar=False
                )

                # Create Qdrant points
                points = [
                    PointStruct(
                        id=str(chunk.chunk_id),
                        vector=embedding,
                        payload={
                            "urn": chunk.graph_node_urn,
                            "node_type": chunk.node_type,
                            "text_preview": text[:500] if text else None
                        }
                    )
                    for chunk, embedding, text in zip(valid_chunks, embeddings, texts)
                ]

                # Upsert to Qdrant
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points
                )

                total_processed += len(points)

                # Progress
                progress = (i + len(batch)) / len(chunks_to_process) * 100
                print(f"  Progress: {progress:.1f}% ({total_processed} embedded, {total_errors} errors)")

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                total_errors += len(batch)

        # Final stats
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"  Total chunks processed: {total_processed}")
        print(f"  Errors: {total_errors}")

        # Verify Qdrant
        info = self.qdrant.get_collection(self.collection_name)
        print(f"  Qdrant collection points: {info.points_count}")
        print("=" * 60)

    async def cleanup(self):
        """Close connections."""
        if self.pg_pool:
            await self.pg_pool.close()


async def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for MERL-T")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding")
    parser.add_argument("--collection", type=str, default="merl_t_chunks", help="Qdrant collection name")
    parser.add_argument("--device", type=str, default="mps", help="Device: cpu, cuda, mps")
    args = parser.parse_args()

    # PostgreSQL connection string
    pg_dsn = "postgresql://dev:devpassword@localhost:5433/rlcf_dev"

    generator = EmbeddingGenerator(
        pg_dsn=pg_dsn,
        batch_size=args.batch_size,
        collection_name=args.collection,
        device=args.device
    )

    try:
        # Setup
        dimension = await generator.setup()

        # Create collection
        should_process = await generator.create_collection(dimension)

        if should_process:
            # Generate and store embeddings
            await generator.generate_and_store()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await generator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
