#!/usr/bin/env python3
"""
EXP-006: Test RAG Pipeline per Codice Penale

Questo script:
1. Genera embeddings per gli articoli del Codice Penale (merl_t_test)
2. Li inserisce in Qdrant (collection: merl_t_test_cp)
3. Esegue 10+ query di test
4. Calcola metriche precision/recall

Usage:
    python scripts/test_codice_penale.py
    python scripts/test_codice_penale.py --skip-embed  # Solo test (embeddings già generati)
"""

import asyncio
import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field

from falkordb import FalkorDB
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


# Config
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380
FALKORDB_GRAPH = "merl_t_test"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "merl_t_test_cp"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024
BATCH_SIZE = 32
TOP_K = 5

# Output
RESULTS_PATH = Path("docs/experiments/EXP-006_libro_primo_cp/rag_results.json")


# Test queries con ground truth (articoli rilevanti attesi)
TEST_QUERIES = [
    {
        "query": "Cos'è il principio di legalità nel diritto penale?",
        "expected_articles": ["1", "2"],
        "topic": "Principio di legalità"
    },
    {
        "query": "Quando un reato può essere punito con l'ergastolo?",
        "expected_articles": ["17", "22"],
        "topic": "Ergastolo"
    },
    {
        "query": "Quali sono le circostanze attenuanti comuni?",
        "expected_articles": ["62", "62-bis"],
        "topic": "Attenuanti"
    },
    {
        "query": "Quali sono le circostanze aggravanti comuni?",
        "expected_articles": ["61"],
        "topic": "Aggravanti"
    },
    {
        "query": "Cosa si intende per concorso di reati?",
        "expected_articles": ["81", "71", "72"],
        "topic": "Concorso reati"
    },
    {
        "query": "Quando si applica la legittima difesa?",
        "expected_articles": ["52", "55"],
        "topic": "Legittima difesa"
    },
    {
        "query": "Cosa prevede lo stato di necessità?",
        "expected_articles": ["54"],
        "topic": "Stato di necessità"
    },
    {
        "query": "Come funziona la sospensione condizionale della pena?",
        "expected_articles": ["163", "164", "165"],
        "topic": "Sospensione condizionale"
    },
    {
        "query": "Quando si applica la confisca?",
        "expected_articles": ["240"],
        "topic": "Confisca"
    },
    {
        "query": "Quali sono le cause di estinzione del reato?",
        "expected_articles": ["150", "151", "152", "157"],
        "topic": "Estinzione reato"
    },
    {
        "query": "Cosa prevede il tentativo di reato?",
        "expected_articles": ["56"],
        "topic": "Tentativo"
    },
    {
        "query": "Come si determina la pena per il concorso di persone nel reato?",
        "expected_articles": ["110", "111", "112", "114"],
        "topic": "Concorso persone"
    }
]


@dataclass
class QueryResult:
    """Result for a single query."""
    query: str
    topic: str
    expected_articles: List[str]
    retrieved_articles: List[str]
    scores: List[float]
    precision_at_k: float
    recall: float
    hits: List[str]
    misses: List[str]


@dataclass
class RAGMetrics:
    """Aggregate RAG metrics."""
    total_queries: int = 0
    avg_precision: float = 0.0
    avg_recall: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    query_results: List[QueryResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_queries": self.total_queries,
            "avg_precision_at_5": f"{self.avg_precision:.3f}",
            "avg_recall": f"{self.avg_recall:.3f}",
            "mrr": f"{self.mrr:.3f}",
            "queries": [
                {
                    "query": r.query,
                    "topic": r.topic,
                    "expected": r.expected_articles,
                    "retrieved": r.retrieved_articles[:5],
                    "precision_at_5": f"{r.precision_at_k:.3f}",
                    "recall": f"{r.recall:.3f}",
                    "hits": r.hits,
                    "misses": r.misses
                }
                for r in self.query_results
            ]
        }


async def generate_embeddings(qdrant: QdrantClient, model: SentenceTransformer):
    """Generate embeddings for Codice Penale articles."""
    print("\n" + "=" * 60)
    print("GENERATING EMBEDDINGS")
    print("=" * 60)

    # Connect to FalkorDB
    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = fb.select_graph(FALKORDB_GRAPH)

    # Read articles
    print("\n1. Reading articles from FalkorDB...")
    result = graph.query("""
        MATCH (n:Norma {tipo_documento: 'articolo'})
        RETURN n.URN, n.numero_articolo, n.testo_vigente, n.position
        ORDER BY n.numero_articolo
    """)

    articles = []
    for row in result.result_set:
        urn, numero, testo, position = row[0], row[1], row[2] or "", row[3] or ""
        if testo:
            articles.append((urn, numero, testo, position))

    print(f"   Found {len(articles)} articles")

    # Create/recreate collection
    print("\n2. Creating Qdrant collection...")
    try:
        qdrant.delete_collection(QDRANT_COLLECTION)
    except Exception:
        pass

    qdrant.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
    )
    print(f"   Created collection: {QDRANT_COLLECTION}")

    # Generate embeddings
    print("\n3. Generating embeddings...")
    texts = []
    for urn, numero, testo, position in articles:
        # E5 format: "passage: <text>"
        text = f"passage: Art. {numero} Codice Penale. {testo[:2000]}"
        texts.append(text)

    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embeddings)
        print(f"   Batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1}")

    print(f"   Generated {len(all_embeddings)} embeddings")

    # Insert into Qdrant
    print("\n4. Inserting into Qdrant...")
    points = []
    for i, (urn, numero, testo, position) in enumerate(articles):
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=all_embeddings[i].tolist(),
            payload={
                "urn": urn,
                "numero_articolo": numero,
                "position": position,
                "text_preview": testo[:300]
            }
        ))

    for i in range(0, len(points), 100):
        batch = points[i:i+100]
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=batch)

    print(f"   Inserted {len(points)} points")

    return len(articles)


def run_query(
    qdrant: QdrantClient,
    model: SentenceTransformer,
    query: str,
    expected_articles: List[str],
    topic: str,
    top_k: int = TOP_K
) -> QueryResult:
    """Run a single query and compute metrics."""
    # Encode query
    query_vector = model.encode(f"query: {query}", normalize_embeddings=True)

    # Search
    results = qdrant.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector.tolist(),
        limit=top_k,
        with_payload=True
    )

    # Extract retrieved articles
    retrieved = []
    scores = []
    for r in results.points:
        num = r.payload.get("numero_articolo", "")
        retrieved.append(num)
        scores.append(r.score)

    # Normalize expected (handle "62-bis" -> "62 bis" mapping)
    expected_normalized = set()
    for a in expected_articles:
        expected_normalized.add(a.replace("-", " "))

    # Compute metrics
    hits = []
    for r in retrieved:
        r_norm = r.replace("-", " ")
        if r_norm in expected_normalized or r in expected_articles:
            hits.append(r)

    precision_at_k = len(hits) / top_k if top_k > 0 else 0
    recall = len(hits) / len(expected_articles) if expected_articles else 0

    misses = [a for a in expected_articles if a not in hits and a.replace("-", " ") not in [h.replace("-", " ") for h in hits]]

    return QueryResult(
        query=query,
        topic=topic,
        expected_articles=expected_articles,
        retrieved_articles=retrieved,
        scores=scores,
        precision_at_k=precision_at_k,
        recall=recall,
        hits=hits,
        misses=misses
    )


def run_all_queries(qdrant: QdrantClient, model: SentenceTransformer) -> RAGMetrics:
    """Run all test queries and compute aggregate metrics."""
    print("\n" + "=" * 60)
    print("RUNNING RAG TEST QUERIES")
    print("=" * 60)

    metrics = RAGMetrics()
    total_precision = 0
    total_recall = 0
    reciprocal_ranks = []

    for i, test in enumerate(TEST_QUERIES, 1):
        result = run_query(
            qdrant, model,
            test["query"],
            test["expected_articles"],
            test["topic"]
        )

        metrics.query_results.append(result)
        total_precision += result.precision_at_k
        total_recall += result.recall

        # MRR: find position of first relevant result
        rr = 0
        for j, r in enumerate(result.retrieved_articles):
            r_norm = r.replace("-", " ")
            for exp in result.expected_articles:
                if r == exp or r_norm == exp.replace("-", " "):
                    rr = 1 / (j + 1)
                    break
            if rr > 0:
                break
        reciprocal_ranks.append(rr)

        # Print result
        status = "OK" if result.hits else "MISS"
        print(f"\n[{i}/{len(TEST_QUERIES)}] {result.topic}")
        print(f"    Query: {result.query[:60]}...")
        print(f"    Expected: {result.expected_articles}")
        print(f"    Retrieved: {result.retrieved_articles}")
        print(f"    [{status}] Hits: {result.hits}, Misses: {result.misses}")
        print(f"    P@5: {result.precision_at_k:.3f}, Recall: {result.recall:.3f}")

    metrics.total_queries = len(TEST_QUERIES)
    metrics.avg_precision = total_precision / len(TEST_QUERIES) if TEST_QUERIES else 0
    metrics.avg_recall = total_recall / len(TEST_QUERIES) if TEST_QUERIES else 0
    metrics.mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0

    return metrics


async def main():
    parser = argparse.ArgumentParser(description="EXP-006: Test RAG per Codice Penale")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    args = parser.parse_args()

    print("=" * 70)
    print("EXP-006: RAG TEST - CODICE PENALE LIBRO PRIMO")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Initialize
    print("\n1. Initializing services...")
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"   Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")

    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"   Model: {EMBEDDING_MODEL}")

    # Generate embeddings
    if not args.skip_embed:
        n_articles = await generate_embeddings(qdrant, model)
    else:
        info = qdrant.get_collection(QDRANT_COLLECTION)
        n_articles = info.points_count
        print(f"\n   Skipping embedding generation ({n_articles} points exist)")

    # Run queries
    metrics = run_all_queries(qdrant, model)

    # Summary
    print("\n" + "=" * 70)
    print("RAG TEST RESULTS")
    print("=" * 70)
    print(f"\nTotal queries: {metrics.total_queries}")
    print(f"Average Precision@5: {metrics.avg_precision:.3f}")
    print(f"Average Recall: {metrics.avg_recall:.3f}")
    print(f"Mean Reciprocal Rank: {metrics.mrr:.3f}")

    # Classification
    if metrics.avg_precision >= 0.6 and metrics.avg_recall >= 0.5:
        verdict = "GOOD"
    elif metrics.avg_precision >= 0.3 or metrics.avg_recall >= 0.3:
        verdict = "ACCEPTABLE"
    else:
        verdict = "NEEDS IMPROVEMENT"

    print(f"\nVerdict: {verdict}")

    # Save results
    print(f"\nSaving results to: {RESULTS_PATH}")
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    results = {
        "experiment": "EXP-006",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "graph": FALKORDB_GRAPH,
            "collection": QDRANT_COLLECTION,
            "model": EMBEDDING_MODEL,
            "top_k": TOP_K,
            "n_articles": n_articles
        },
        "metrics": metrics.to_dict(),
        "verdict": verdict
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("TEST COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
