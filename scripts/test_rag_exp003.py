#!/usr/bin/env python3
"""
EXP-003: RAG Pipeline Test con Dataset Completo (12K vectors)

Testa retrieval su Norma + Massime con graph enrichment.
"""

import asyncio
import json
import sys
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from qdrant_client import QdrantClient
from falkordb import FalkorDB

from merlt.orchestration.services.embedding_service import EmbeddingService


@dataclass
class SearchResult:
    """Result from semantic search."""
    point_id: str
    score: float
    node_type: str
    # For Norma
    urn: Optional[str] = None
    # For Massime
    node_id: Optional[str] = None
    estremi: Optional[str] = None
    text_preview: str = ""


@dataclass
class EnrichedResult:
    """Result enriched with graph context."""
    identifier: str  # URN for Norma, node_id for Massime
    node_type: str
    score: float
    text_preview: str
    # Enrichment
    metadata: dict = field(default_factory=dict)
    dottrina: list = field(default_factory=list)
    related_norme: list = field(default_factory=list)
    related_massime: list = field(default_factory=list)


@dataclass
class QueryResult:
    """Full query result with metrics."""
    query: str
    latency_ms: float
    results: list
    type_breakdown: dict
    enrichment_rate: float


class RAGTesterEXP003:
    """RAG Pipeline tester for EXP-003."""

    def __init__(self):
        self.pg_dsn = "postgresql://dev:devpassword@localhost:5433/rlcf_dev"
        self.collection_name = "merl_t_chunks"
        self.top_k = 10

        self.pg_pool = None
        self.qdrant = None
        self.falkordb = None
        self.embedding_service = None

    async def setup(self):
        """Initialize connections."""
        print("\n" + "=" * 60)
        print("EXP-003: RAG Pipeline Test - Setup")
        print("=" * 60)

        # Embedding
        print("\n[1/4] Loading embedding model...")
        os.environ["EMBEDDING_DEVICE"] = "mps"
        self.embedding_service = EmbeddingService.get_instance(device="mps")
        print(f"  ✓ Model loaded (dim: {self.embedding_service.embedding_dimension})")

        # Qdrant
        print("\n[2/4] Connecting to Qdrant...")
        self.qdrant = QdrantClient(host="localhost", port=6333)
        info = self.qdrant.get_collection(self.collection_name)
        print(f"  ✓ Connected - {info.points_count} vectors")

        # PostgreSQL
        print("\n[3/4] Connecting to PostgreSQL...")
        self.pg_pool = await asyncpg.create_pool(self.pg_dsn)
        async with self.pg_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM bridge_table")
        print(f"  ✓ Connected - {count} bridge mappings")

        # FalkorDB
        print("\n[4/4] Connecting to FalkorDB...")
        self.falkordb = FalkorDB(host="localhost", port=6380)
        graph = self.falkordb.select_graph("merl_t_legal")
        result = graph.query("MATCH (n) RETURN labels(n)[0] as label, count(n) as cnt")
        for row in result.result_set:
            print(f"  - {row[0]}: {row[1]}")

        print("\n" + "=" * 60)
        return info.points_count

    async def search(self, query: str) -> list[SearchResult]:
        """Semantic search on Qdrant."""
        query_vector = self.embedding_service.encode_query(query)

        results = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=self.top_k,
            with_payload=True
        )

        search_results = []
        for r in results.points:
            node_type = r.payload.get("node_type", "unknown")

            search_results.append(SearchResult(
                point_id=str(r.id),
                score=r.score,
                node_type=node_type,
                urn=r.payload.get("urn"),
                node_id=r.payload.get("node_id"),
                estremi=r.payload.get("estremi"),
                text_preview=r.payload.get("text_preview", "")[:300]
            ))

        return search_results

    def enrich_norma(self, urn: str) -> dict:
        """Enrich Norma result with graph context."""
        graph = self.falkordb.select_graph("merl_t_legal")
        enrichment = {
            'titolo': None,
            'rubrica': None,
            'dottrina': [],
            'massime_correlate': []
        }

        # Node properties
        result = graph.query(
            "MATCH (n:Norma {URN: $urn}) RETURN n.titolo, n.rubrica",
            {'urn': urn}
        )
        if result.result_set:
            enrichment['titolo'] = result.result_set[0][0]
            enrichment['rubrica'] = result.result_set[0][1]

        # Dottrina
        result = graph.query("""
            MATCH (n:Norma {URN: $urn})<-[:commenta]-(d:Dottrina)
            RETURN d.tipo_dottrina, substring(d.descrizione, 0, 100)
            LIMIT 2
        """, {'urn': urn})
        for row in result.result_set:
            enrichment['dottrina'].append({'tipo': row[0], 'preview': row[1]})

        # Massime correlate (top 2)
        result = graph.query("""
            MATCH (n:Norma {URN: $urn})<-[:interpreta]-(a:AttoGiudiziario)
            RETURN a.estremi, substring(a.massima, 0, 100)
            LIMIT 2
        """, {'urn': urn})
        for row in result.result_set:
            enrichment['massime_correlate'].append({'estremi': row[0], 'preview': row[1]})

        return enrichment

    def enrich_massima(self, node_id: str) -> dict:
        """Enrich Massima result with graph context."""
        graph = self.falkordb.select_graph("merl_t_legal")
        enrichment = {
            'organo': None,
            'anno': None,
            'norme_interpretate': []
        }

        # Node properties
        result = graph.query(
            "MATCH (a:AttoGiudiziario {node_id: $nid}) RETURN a.organo_emittente, a.anno",
            {'nid': node_id}
        )
        if result.result_set:
            enrichment['organo'] = result.result_set[0][0]
            enrichment['anno'] = result.result_set[0][1]

        # Norme interpretate
        result = graph.query("""
            MATCH (a:AttoGiudiziario {node_id: $nid})-[:interpreta]->(n:Norma)
            RETURN n.URN, n.rubrica
            LIMIT 3
        """, {'nid': node_id})
        for row in result.result_set:
            # Extract article from URN
            urn = row[0] or ""
            article = urn.split('~')[-1] if '~' in urn else urn
            enrichment['norme_interpretate'].append({
                'articolo': article,
                'rubrica': row[1]
            })

        return enrichment

    async def query(self, user_query: str) -> QueryResult:
        """Execute full RAG pipeline with metrics."""
        start_time = time.time()

        # Semantic search
        search_results = await self.search(user_query)

        # Type breakdown
        type_counts = {}
        for r in search_results:
            type_counts[r.node_type] = type_counts.get(r.node_type, 0) + 1

        # Enrich results
        enriched = []
        enriched_count = 0

        for sr in search_results:
            if sr.node_type == "Norma" and sr.urn:
                enrichment = self.enrich_norma(sr.urn)
                identifier = sr.urn.split('~')[-1] if '~' in sr.urn else sr.urn
                has_enrichment = bool(enrichment['dottrina'] or enrichment['massime_correlate'])

            elif sr.node_type == "AttoGiudiziario" and sr.node_id:
                enrichment = self.enrich_massima(sr.node_id)
                identifier = sr.estremi or sr.node_id
                has_enrichment = bool(enrichment['norme_interpretate'])

            else:
                enrichment = {}
                identifier = sr.urn or sr.node_id or "unknown"
                has_enrichment = False

            if has_enrichment:
                enriched_count += 1

            enriched.append(EnrichedResult(
                identifier=identifier,
                node_type=sr.node_type,
                score=sr.score,
                text_preview=sr.text_preview,
                metadata=enrichment
            ))

        latency = (time.time() - start_time) * 1000

        return QueryResult(
            query=user_query,
            latency_ms=latency,
            results=enriched,
            type_breakdown=type_counts,
            enrichment_rate=enriched_count / len(enriched) if enriched else 0
        )

    def display_result(self, qr: QueryResult):
        """Display query results."""
        print(f"\n{'═' * 60}")
        print(f"Query: \"{qr.query}\"")
        print(f"{'═' * 60}")
        print(f"Latency: {qr.latency_ms:.1f}ms | Types: {qr.type_breakdown}")
        print(f"Enrichment rate: {qr.enrichment_rate:.0%}")

        for i, r in enumerate(qr.results[:5], 1):  # Show top 5
            print(f"\n{'─' * 50}")
            icon = "📜" if r.node_type == "Norma" else "⚖️"
            print(f"#{i} {icon} [{r.node_type}] {r.identifier} | Score: {r.score:.4f}")

            if r.text_preview:
                preview = r.text_preview[:150].replace('\n', ' ')
                print(f"   \"{preview}...\"")

            if r.metadata:
                if r.node_type == "Norma":
                    if r.metadata.get('rubrica'):
                        print(f"   Rubrica: {r.metadata['rubrica']}")
                    if r.metadata.get('dottrina'):
                        print(f"   📚 Dottrina: {len(r.metadata['dottrina'])} fonti")
                    if r.metadata.get('massime_correlate'):
                        print(f"   ⚖️ Massime: {len(r.metadata['massime_correlate'])} correlate")
                else:
                    if r.metadata.get('organo'):
                        print(f"   Organo: {r.metadata['organo']} ({r.metadata.get('anno', 'N/A')})")
                    if r.metadata.get('norme_interpretate'):
                        norme = [n['articolo'] for n in r.metadata['norme_interpretate']]
                        print(f"   📜 Interpreta: {', '.join(norme)}")

    async def run_experiment(self, queries: list[str], output_dir: str = None):
        """Run full experiment with all queries."""
        print("\n" + "🔬" * 20)
        print("EXP-003: Starting experiment")
        print("🔬" * 20)

        all_results = []
        total_latency = 0
        total_enrichment = 0
        type_totals = {}

        for i, query in enumerate(queries, 1):
            print(f"\n[Query {i}/{len(queries)}]")
            result = await self.query(query)
            self.display_result(result)

            all_results.append({
                'query': result.query,
                'latency_ms': result.latency_ms,
                'type_breakdown': result.type_breakdown,
                'enrichment_rate': result.enrichment_rate,
                'top_results': [
                    {
                        'identifier': r.identifier,
                        'node_type': r.node_type,
                        'score': r.score
                    }
                    for r in result.results[:5]
                ]
            })

            total_latency += result.latency_ms
            total_enrichment += result.enrichment_rate
            for t, c in result.type_breakdown.items():
                type_totals[t] = type_totals.get(t, 0) + c

        # Summary
        print("\n" + "=" * 60)
        print("EXPERIMENT SUMMARY")
        print("=" * 60)
        print(f"Queries executed: {len(queries)}")
        print(f"Average latency: {total_latency / len(queries):.1f}ms")
        print(f"Average enrichment rate: {total_enrichment / len(queries):.0%}")
        print(f"Type distribution: {type_totals}")

        # Save results
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"exp003_results_{datetime.now().strftime('%H%M%S')}.json")
            with open(output_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'queries': len(queries),
                    'avg_latency_ms': total_latency / len(queries),
                    'avg_enrichment_rate': total_enrichment / len(queries),
                    'type_distribution': type_totals,
                    'results': all_results
                }, f, indent=2)
            print(f"\nResults saved to: {output_file}")

        return all_results

    async def cleanup(self):
        if self.pg_pool:
            await self.pg_pool.close()


async def main():
    # Query set from DESIGN.md
    queries = [
        "Cos'è la risoluzione del contratto per inadempimento?",
        "Sentenze sulla clausola risolutiva espressa",
        "Responsabilità del medico per danni al paziente",
        "Obblighi del venditore nella compravendita",
        "Giurisprudenza sulla diffida ad adempiere",
        "Cosa dice la Cassazione sul risarcimento del danno?",
        "Eccezione di inadempimento nel contratto",
        "Risoluzione di diritto del contratto",
        "Sentenze recenti sulla caparra confirmatoria",
        "Impossibilità sopravvenuta della prestazione"
    ]

    tester = RAGTesterEXP003()

    try:
        await tester.setup()
        await tester.run_experiment(
            queries,
            output_dir="docs/experiments/EXP-003_rag_full_dataset"
        )
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
