#!/usr/bin/env python3
"""
Test RAG Pipeline - End-to-End Query Testing

This script tests the complete RAG flow:
1. User query → Embedding (E5-large with "query: " prefix)
2. Embedding → Qdrant semantic search
3. Chunk IDs → Bridge Table → Graph Node URNs
4. URNs → FalkorDB graph enrichment (dottrina, giurisprudenza)

Usage:
    python scripts/test_rag_pipeline.py "Cos'è la risoluzione del contratto?"
    python scripts/test_rag_pipeline.py --interactive
"""

import asyncio
import argparse
import sys
import os
from typing import Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from qdrant_client import QdrantClient
from falkordb import FalkorDB

from merlt.orchestration.services.embedding_service import EmbeddingService


@dataclass
class SearchResult:
    """Result from semantic search."""
    chunk_id: str
    score: float
    urn: str
    node_type: str
    text_preview: str


@dataclass
class EnrichedResult:
    """Result enriched with graph context."""
    urn: str
    score: float
    text_preview: str
    # Graph enrichment
    titolo: Optional[str] = None
    rubrica: Optional[str] = None
    dottrina: list = None
    giurisprudenza: list = None

    def __post_init__(self):
        if self.dottrina is None:
            self.dottrina = []
        if self.giurisprudenza is None:
            self.giurisprudenza = []


class RAGPipelineTester:
    """Test the complete RAG pipeline."""

    def __init__(
        self,
        pg_dsn: str = "postgresql://dev:devpassword@localhost:5433/rlcf_dev",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        falkordb_host: str = "localhost",
        falkordb_port: int = 6380,
        collection_name: str = "merl_t_chunks",
        top_k: int = 5
    ):
        self.pg_dsn = pg_dsn
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.falkordb_host = falkordb_host
        self.falkordb_port = falkordb_port
        self.collection_name = collection_name
        self.top_k = top_k

        # Clients
        self.pg_pool = None
        self.qdrant = None
        self.falkordb = None
        self.embedding_service = None

    async def setup(self):
        """Initialize all connections."""
        print("\n" + "=" * 60)
        print("RAG Pipeline Tester - Setup")
        print("=" * 60)

        # 1. Embedding Service
        print("\n[1/4] Loading embedding model...")
        os.environ["EMBEDDING_DEVICE"] = "mps"
        self.embedding_service = EmbeddingService.get_instance(device="mps")
        dim = self.embedding_service.embedding_dimension
        print(f"  ✓ Model loaded (dim: {dim})")

        # 2. Qdrant
        print("\n[2/4] Connecting to Qdrant...")
        self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        info = self.qdrant.get_collection(self.collection_name)
        print(f"  ✓ Connected - {info.points_count} vectors")

        # 3. PostgreSQL
        print("\n[3/4] Connecting to PostgreSQL...")
        self.pg_pool = await asyncpg.create_pool(self.pg_dsn)
        async with self.pg_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM bridge_table")
        print(f"  ✓ Connected - {count} bridge mappings")

        # 4. FalkorDB
        print("\n[4/4] Connecting to FalkorDB...")
        self.falkordb = FalkorDB(host=self.falkordb_host, port=self.falkordb_port)
        graph = self.falkordb.select_graph("merl_t_legal")
        result = graph.query("MATCH (n:Norma) RETURN count(n) as count")
        norma_count = result.result_set[0][0] if result.result_set else 0
        print(f"  ✓ Connected - {norma_count} Norma nodes")

        print("\n" + "=" * 60)
        print("Setup complete! Ready for queries.")
        print("=" * 60)

    async def search(self, query: str) -> list[SearchResult]:
        """
        Step 1-2: Encode query and search Qdrant.
        """
        # Encode with "query: " prefix (E5 requirement)
        query_vector = self.embedding_service.encode_query(query)

        # Search Qdrant (using query_points API)
        results = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=self.top_k,
            with_payload=True
        )

        return [
            SearchResult(
                chunk_id=str(r.id),
                score=r.score,
                urn=r.payload.get("urn", ""),
                node_type=r.payload.get("node_type", ""),
                text_preview=r.payload.get("text_preview", "")[:200]
            )
            for r in results.points
        ]

    async def get_bridge_mappings(self, chunk_ids: list[str]) -> dict:
        """
        Step 3: Get graph node URNs from Bridge Table.
        """
        async with self.pg_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT chunk_id, graph_node_urn, node_type, relation_type
                FROM bridge_table
                WHERE chunk_id = ANY($1::uuid[])
            """, chunk_ids)

            mappings = {}
            for row in rows:
                chunk_id = str(row['chunk_id'])
                if chunk_id not in mappings:
                    mappings[chunk_id] = []
                mappings[chunk_id].append({
                    'urn': row['graph_node_urn'],
                    'node_type': row['node_type'],
                    'relation_type': row['relation_type']
                })
            return mappings

    def enrich_with_graph(self, urn: str) -> dict:
        """
        Step 4: Get graph context for a URN.
        """
        graph = self.falkordb.select_graph("merl_t_legal")
        enrichment = {
            'titolo': None,
            'rubrica': None,
            'dottrina': [],
            'giurisprudenza': []
        }

        # Get node properties
        result = graph.query(
            "MATCH (n:Norma {URN: $urn}) RETURN n.titolo, n.rubrica",
            {'urn': urn}
        )
        if result.result_set:
            enrichment['titolo'] = result.result_set[0][0]
            enrichment['rubrica'] = result.result_set[0][1]

        # Get dottrina (max 3) - field is 'descrizione'
        result = graph.query("""
            MATCH (n:Norma {URN: $urn})<-[:commenta]-(d:Dottrina)
            RETURN d.tipo_dottrina, substring(d.descrizione, 0, 150) as preview
            LIMIT 3
        """, {'urn': urn})
        for row in result.result_set:
            enrichment['dottrina'].append({
                'tipo': row[0],
                'preview': row[1]
            })

        # Get giurisprudenza (max 3) - fields: organo_emittente, numero_sentenza, anno, massima
        result = graph.query("""
            MATCH (n:Norma {URN: $urn})<-[:interpreta]-(a:AttoGiudiziario)
            RETURN a.organo_emittente, a.numero_sentenza, a.anno, substring(a.massima, 0, 150) as preview
            LIMIT 3
        """, {'urn': urn})
        for row in result.result_set:
            enrichment['giurisprudenza'].append({
                'autorita': row[0],
                'numero': row[1],
                'anno': row[2],
                'preview': row[3]
            })

        return enrichment

    async def query(self, user_query: str) -> list[EnrichedResult]:
        """
        Execute full RAG pipeline.
        """
        print(f"\n{'─' * 60}")
        print(f"Query: \"{user_query}\"")
        print(f"{'─' * 60}")

        # Step 1-2: Semantic search
        print("\n[Step 1] Semantic Search (Qdrant)...")
        search_results = await self.search(user_query)
        print(f"  Found {len(search_results)} results")

        # Step 3: Bridge Table lookup
        print("\n[Step 2] Bridge Table Lookup...")
        chunk_ids = [r.chunk_id for r in search_results]
        bridge_mappings = await self.get_bridge_mappings(chunk_ids)
        print(f"  Found mappings for {len(bridge_mappings)} chunks")

        # Step 4: Graph enrichment
        print("\n[Step 3] Graph Enrichment (FalkorDB)...")
        enriched_results = []

        for result in search_results:
            enrichment = self.enrich_with_graph(result.urn)

            enriched = EnrichedResult(
                urn=result.urn,
                score=result.score,
                text_preview=result.text_preview,
                titolo=enrichment['titolo'],
                rubrica=enrichment['rubrica'],
                dottrina=enrichment['dottrina'],
                giurisprudenza=enrichment['giurisprudenza']
            )
            enriched_results.append(enriched)

        print(f"  Enriched {len(enriched_results)} results")

        return enriched_results

    def display_results(self, results: list[EnrichedResult]):
        """Display results in a readable format."""
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        for i, r in enumerate(results, 1):
            print(f"\n{'─' * 60}")
            print(f"#{i} | Score: {r.score:.4f}")
            print(f"{'─' * 60}")

            # Extract article number from URN
            article = r.urn.split('~')[-1] if '~' in r.urn else r.urn
            print(f"📜 {article}")

            if r.rubrica:
                print(f"   Rubrica: {r.rubrica}")

            print(f"\n   Testo (preview):")
            print(f"   {r.text_preview}...")

            if r.dottrina:
                print(f"\n   📚 Dottrina ({len(r.dottrina)} fonti):")
                for d in r.dottrina:
                    tipo = d.get('tipo') or 'N/A'
                    preview = d.get('preview') or ''
                    print(f"      • [{tipo}] {preview[:80]}..." if preview else f"      • [{tipo}]")

            if r.giurisprudenza:
                print(f"\n   ⚖️  Giurisprudenza ({len(r.giurisprudenza)} sentenze):")
                for g in r.giurisprudenza:
                    autorita = g.get('autorita') or 'N/A'
                    numero = g.get('numero')
                    anno = g.get('anno')
                    ref = f"{autorita} {numero}/{anno}" if numero else autorita
                    print(f"      • {ref}")
                    preview = g.get('preview')
                    if preview:
                        print(f"        \"{preview[:80]}...\"")

        print("\n" + "=" * 60)

    async def cleanup(self):
        """Close connections."""
        if self.pg_pool:
            await self.pg_pool.close()


async def main():
    parser = argparse.ArgumentParser(description="Test RAG Pipeline")
    parser.add_argument("query", nargs="?", help="Query to test")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    tester = RAGPipelineTester(top_k=args.top_k)

    try:
        await tester.setup()

        if args.interactive:
            print("\n💡 Interactive mode. Type 'exit' to quit.\n")
            while True:
                try:
                    query = input("\n🔍 Query: ").strip()
                    if query.lower() in ('exit', 'quit', 'q'):
                        break
                    if not query:
                        continue

                    results = await tester.query(query)
                    tester.display_results(results)

                except KeyboardInterrupt:
                    break

        elif args.query:
            results = await tester.query(args.query)
            tester.display_results(results)

        else:
            # Default test queries
            test_queries = [
                "Cos'è la risoluzione del contratto per inadempimento?",
                "Quando si può richiedere il risarcimento del danno?",
                "Cosa prevede la clausola risolutiva espressa?",
            ]

            print("\n📋 Running default test queries...\n")

            for query in test_queries:
                results = await tester.query(query)
                tester.display_results(results)
                print("\n" + "🔹" * 30 + "\n")

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
