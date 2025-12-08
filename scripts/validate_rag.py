#!/usr/bin/env python3
"""
RAG Validation Script
=====================

Valida la qualità del retrieval semantico con metriche quantitative.

Usage:
    python scripts/validate_rag.py
    python scripts/validate_rag.py --collection exp_libro_iv_cc --top-k 10
"""

import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from merlt.storage.vectors.embeddings import EmbeddingService


# Test queries con expected results
# Format: (query, expected_article_numbers, category)
TEST_QUERIES_COSTITUZIONE = [
    # Ricerche concettuali (senza numero articolo)
    ("diritti fondamentali dei cittadini", ["2", "3", "13", "14", "15"], "conceptual"),
    ("libertà di pensiero e parola", ["21"], "conceptual"),
    ("lavoro e diritti dei lavoratori", ["1", "4", "35", "36", "37", "38"], "conceptual"),
    ("organizzazione del governo", ["92", "93", "94", "95"], "conceptual"),
    ("potere legislativo", ["70", "71", "72", "73"], "conceptual"),
    ("magistratura e giudici", ["101", "102", "103", "104"], "conceptual"),

    # Ricerche per principio
    ("uguaglianza davanti alla legge", ["3"], "principle"),
    ("sovranità popolare", ["1"], "principle"),
    ("inviolabilità della libertà personale", ["13"], "principle"),

    # Ricerche per istituzione
    ("presidente della repubblica", ["83", "84", "85", "86", "87"], "institution"),
    ("corte costituzionale", ["134", "135", "136", "137"], "institution"),
    ("parlamento italiano", ["55", "56", "57", "58"], "institution"),
]

TEST_QUERIES_CODICE_CIVILE = [
    # Obbligazioni
    ("inadempimento del debitore", ["1218", "1219", "1220"], "conceptual"),
    ("responsabilità contrattuale", ["1218", "1223", "1225"], "conceptual"),
    ("mora del debitore", ["1219", "1220", "1221"], "conceptual"),

    # Contratti
    ("rescissione del contratto", ["1447", "1448", "1449"], "conceptual"),
    ("risoluzione per inadempimento", ["1453", "1454", "1455"], "conceptual"),
]


@dataclass
class ValidationResult:
    """Result of a single query validation."""
    query: str
    expected: List[str]
    retrieved: List[str]
    scores: List[float]
    category: str
    hit_at_1: bool
    hit_at_5: bool
    hit_at_10: bool
    reciprocal_rank: float


def calculate_metrics(results: List[ValidationResult]) -> Dict:
    """Calculate aggregate metrics from validation results."""
    total = len(results)
    if total == 0:
        return {}

    hits_at_1 = sum(1 for r in results if r.hit_at_1)
    hits_at_5 = sum(1 for r in results if r.hit_at_5)
    hits_at_10 = sum(1 for r in results if r.hit_at_10)
    mrr = sum(r.reciprocal_rank for r in results) / total

    # Per category
    by_category = {}
    for r in results:
        if r.category not in by_category:
            by_category[r.category] = []
        by_category[r.category].append(r)

    category_metrics = {}
    for cat, cat_results in by_category.items():
        cat_total = len(cat_results)
        category_metrics[cat] = {
            "total": cat_total,
            "recall_at_1": sum(1 for r in cat_results if r.hit_at_1) / cat_total,
            "recall_at_5": sum(1 for r in cat_results if r.hit_at_5) / cat_total,
            "mrr": sum(r.reciprocal_rank for r in cat_results) / cat_total,
        }

    return {
        "total_queries": total,
        "recall_at_1": hits_at_1 / total,
        "recall_at_5": hits_at_5 / total,
        "recall_at_10": hits_at_10 / total,
        "mrr": mrr,
        "by_category": category_metrics,
    }


async def validate_rag(
    collection: str,
    test_queries: List[tuple],
    top_k: int = 10,
) -> List[ValidationResult]:
    """Run RAG validation on a collection."""

    # Initialize
    qdrant = QdrantClient(host="localhost", port=6333)
    embedding_service = EmbeddingService()

    results = []

    for query, expected, category in test_queries:
        # Embed query
        query_vector = await embedding_service.encode_query_async(query)

        # Search using query_points API
        search_results = qdrant.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
        )

        # Extract retrieved article numbers
        retrieved = []
        scores = []
        for hit in search_results.points:
            art_num = hit.payload.get("numero_articolo", hit.payload.get("article_number", ""))
            if art_num:
                retrieved.append(str(art_num))
                scores.append(hit.score)

        # Calculate metrics for this query
        hit_at_1 = any(exp in retrieved[:1] for exp in expected)
        hit_at_5 = any(exp in retrieved[:5] for exp in expected)
        hit_at_10 = any(exp in retrieved[:10] for exp in expected)

        # Reciprocal rank: 1/position of first relevant result
        rr = 0.0
        for i, ret in enumerate(retrieved):
            if ret in expected:
                rr = 1.0 / (i + 1)
                break

        results.append(ValidationResult(
            query=query,
            expected=expected,
            retrieved=retrieved[:5],
            scores=scores[:5],
            category=category,
            hit_at_1=hit_at_1,
            hit_at_5=hit_at_5,
            hit_at_10=hit_at_10,
            reciprocal_rank=rr,
        ))

    return results


async def main():
    parser = argparse.ArgumentParser(description="RAG Validation")
    parser.add_argument("--collection", default="merl_t_dev_chunks", help="Qdrant collection")
    parser.add_argument("--top-k", type=int, default=10, help="Top K results to retrieve")
    parser.add_argument("--corpus", default="costituzione", choices=["costituzione", "codice_civile"], help="Test corpus")
    args = parser.parse_args()

    print("=" * 70)
    print("RAG VALIDATION")
    print("=" * 70)
    print(f"Collection: {args.collection}")
    print(f"Top K: {args.top_k}")
    print(f"Corpus: {args.corpus}")

    # Select test queries
    if args.corpus == "costituzione":
        test_queries = TEST_QUERIES_COSTITUZIONE
    else:
        test_queries = TEST_QUERIES_CODICE_CIVILE

    print(f"Test queries: {len(test_queries)}")

    # Run validation
    print("\nRunning validation...")
    results = await validate_rag(args.collection, test_queries, args.top_k)

    # Calculate metrics
    metrics = calculate_metrics(results)

    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"\nOverall Metrics:")
    print(f"  Recall@1:  {metrics['recall_at_1']:.2%}")
    print(f"  Recall@5:  {metrics['recall_at_5']:.2%}")
    print(f"  Recall@10: {metrics['recall_at_10']:.2%}")
    print(f"  MRR:       {metrics['mrr']:.3f}")

    print(f"\nBy Category:")
    for cat, cat_metrics in metrics.get("by_category", {}).items():
        print(f"  {cat}:")
        print(f"    Recall@5: {cat_metrics['recall_at_5']:.2%}, MRR: {cat_metrics['mrr']:.3f}")

    # Detailed results
    print(f"\nDetailed Results:")
    for r in results:
        status = "✓" if r.hit_at_5 else "✗"
        print(f"  {status} [{r.category}] {r.query[:50]}...")
        print(f"      Expected: {r.expected[:3]}..., Got: {r.retrieved[:3]}")

    # Save results
    output_path = Path(f"docs/experiments/rag_validation_{args.corpus}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "collection": args.collection,
            "top_k": args.top_k,
            "corpus": args.corpus,
        },
        "metrics": metrics,
        "results": [
            {
                "query": r.query,
                "expected": r.expected,
                "retrieved": r.retrieved,
                "scores": r.scores,
                "category": r.category,
                "hit_at_5": r.hit_at_5,
                "reciprocal_rank": r.reciprocal_rank,
            }
            for r in results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
