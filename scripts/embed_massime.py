#!/usr/bin/env python3
"""
Embed Massime (Giurisprudenza) for MERL-T
==========================================

Genera embeddings per le massime giurisprudenziali (AttoGiudiziario)
e le aggiunge alla collection Qdrant esistente.

Questo permette ricerca semantica diretta su giurisprudenza:
- Query: "responsabilità medico per danni"
- → Trova Cass. civ. n. 12274/2011 (massima)
- → Collega ad Art. 1218 c.c. (norma interpretata)

Usage:
    python scripts/embed_massime.py [--batch-size 32] [--collection merl_t_chunks]
"""

import asyncio
import argparse
import logging
import sys
import os
from uuid import uuid4
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from falkordb import FalkorDB

from merlt.orchestration.services.embedding_service import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MassimaData:
    """Data for a single massima."""
    node_id: str
    estremi: str
    numero_sentenza: str
    anno: str
    massima_text: str
    organo: str
    materia: str
    related_norma_urns: List[str]  # Articoli interpretati


class MassimeEmbedder:
    """Generate embeddings for massime (AttoGiudiziario)."""

    def __init__(
        self,
        falkordb_host: str = "localhost",
        falkordb_port: int = 6380,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "merl_t_chunks",
        batch_size: int = 32,
        device: str = "mps"
    ):
        self.falkordb_host = falkordb_host
        self.falkordb_port = falkordb_port
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.device = device

        self.falkordb: Optional[FalkorDB] = None
        self.qdrant: Optional[QdrantClient] = None
        self.embedding_service: Optional[EmbeddingService] = None

    def setup(self):
        """Initialize connections."""
        print("\n" + "=" * 60)
        print("MERL-T Massime Embedder")
        print("=" * 60)

        # FalkorDB
        print("\n[1/3] Connecting to FalkorDB...")
        self.falkordb = FalkorDB(host=self.falkordb_host, port=self.falkordb_port)
        graph = self.falkordb.select_graph("merl_t_legal")
        result = graph.query("MATCH (a:AttoGiudiziario) RETURN count(a) as count")
        count = result.result_set[0][0] if result.result_set else 0
        print(f"  ✓ Connected - {count} AttoGiudiziario nodes")

        # Qdrant
        print("\n[2/3] Connecting to Qdrant...")
        self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        info = self.qdrant.get_collection(self.collection_name)
        print(f"  ✓ Connected - {info.points_count} existing points in '{self.collection_name}'")

        # Embedding Service
        print("\n[3/3] Loading embedding model...")
        os.environ["EMBEDDING_DEVICE"] = self.device
        self.embedding_service = EmbeddingService.get_instance(device=self.device)
        dim = self.embedding_service.embedding_dimension
        print(f"  ✓ Model loaded on {self.device}, dimension: {dim}")

        return count

    def get_massime_from_graph(self) -> List[MassimaData]:
        """Fetch all massime with their related articles."""
        graph = self.falkordb.select_graph("merl_t_legal")

        # Get massime with related Norma URNs
        result = graph.query("""
            MATCH (a:AttoGiudiziario)-[:interpreta]->(n:Norma)
            WHERE a.massima IS NOT NULL AND a.massima <> ''
            RETURN
                a.node_id as node_id,
                a.estremi as estremi,
                a.numero_sentenza as numero,
                a.anno as anno,
                a.massima as massima,
                a.organo_emittente as organo,
                a.materia as materia,
                collect(n.URN) as norma_urns
        """)

        massime = []
        for row in result.result_set:
            massime.append(MassimaData(
                node_id=row[0] or f"unknown_{len(massime)}",
                estremi=row[1] or "",
                numero_sentenza=row[2] or "",
                anno=row[3] or "",
                massima_text=row[4] or "",
                organo=row[5] or "",
                materia=row[6] or "",
                related_norma_urns=row[7] or []
            ))

        return massime

    def get_existing_massima_ids(self) -> set:
        """Get IDs of massime already in Qdrant."""
        existing = set()
        try:
            offset = None
            while True:
                result = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                points, offset = result
                for point in points:
                    # Check if it's a massima (has node_type = 'AttoGiudiziario')
                    if point.payload.get('node_type') == 'AttoGiudiziario':
                        existing.add(point.payload.get('node_id'))
                if offset is None:
                    break
        except Exception as e:
            logger.warning(f"Error checking existing: {e}")

        return existing

    def generate_and_store(self):
        """Generate embeddings for massime and store in Qdrant."""
        # Get all massime
        print("\n[4/6] Loading massime from FalkorDB...")
        massime = self.get_massime_from_graph()
        print(f"  Found {len(massime)} massime with text")

        if not massime:
            print("  No massime to process!")
            return

        # Check existing
        print("\n[5/6] Checking existing massime embeddings...")
        existing_ids = self.get_existing_massima_ids()
        print(f"  Found {len(existing_ids)} existing massime embeddings")

        # Filter
        to_process = [m for m in massime if m.node_id not in existing_ids]
        print(f"  {len(to_process)} massime need embedding")

        if not to_process:
            print("  All massime already have embeddings!")
            return

        # Process in batches
        print(f"\n[6/6] Generating embeddings (batch size: {self.batch_size})...")
        total_processed = 0
        total_errors = 0

        for i in range(0, len(to_process), self.batch_size):
            batch = to_process[i:i + self.batch_size]

            # Prepare texts - include context for better retrieval
            texts = []
            valid_massime = []

            for m in batch:
                if m.massima_text and len(m.massima_text.strip()) > 20:
                    # Create enriched text with metadata
                    text = f"{m.estremi}. {m.massima_text}"
                    texts.append(text)
                    valid_massime.append(m)
                else:
                    total_errors += 1

            if not texts:
                continue

            try:
                # Generate embeddings
                embeddings = self.embedding_service.encode_batch(
                    texts,
                    is_query=False,
                    show_progress_bar=False
                )

                # Create points
                points = []
                for massima, embedding, text in zip(valid_massime, embeddings, texts):
                    point_id = str(uuid4())  # Generate unique ID
                    points.append(PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "node_id": massima.node_id,
                            "node_type": "AttoGiudiziario",
                            "estremi": massima.estremi,
                            "numero_sentenza": massima.numero_sentenza,
                            "anno": massima.anno,
                            "organo": massima.organo,
                            "materia": massima.materia,
                            "related_norma_urns": massima.related_norma_urns,
                            "text_preview": text[:500]
                        }
                    ))

                # Upsert
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points
                )

                total_processed += len(points)
                progress = (i + len(batch)) / len(to_process) * 100
                print(f"  Progress: {progress:.1f}% ({total_processed} embedded, {total_errors} errors)")

            except Exception as e:
                logger.error(f"Batch failed: {e}")
                total_errors += len(batch)

        # Final stats
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"  Massime processed: {total_processed}")
        print(f"  Errors: {total_errors}")

        info = self.qdrant.get_collection(self.collection_name)
        print(f"  Total Qdrant points: {info.points_count}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Embed massime for MERL-T")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--collection", type=str, default="merl_t_chunks", help="Qdrant collection")
    parser.add_argument("--device", type=str, default="mps", help="Device: cpu, cuda, mps")
    args = parser.parse_args()

    embedder = MassimeEmbedder(
        collection_name=args.collection,
        batch_size=args.batch_size,
        device=args.device
    )

    try:
        embedder.setup()
        embedder.generate_and_store()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
