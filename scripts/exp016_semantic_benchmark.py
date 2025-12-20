#!/usr/bin/env python3
"""
EXP-016: Semantic RAG Benchmark
===============================

Benchmark con metodologia corretta per testare le capacità
REALI del sistema di similarity search:

- Solo query semantiche (no numeri articolo)
- Valutazione graduata (0-3) invece di binaria
- Articoli solo nel range Libro IV (1173-2059)

Uso:
    python scripts/exp016_semantic_benchmark.py --full
    python scripts/exp016_semantic_benchmark.py --source-only
    python scripts/exp016_semantic_benchmark.py --latency-only
"""

import asyncio
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import structlog

from merlt import LegalKnowledgeGraph, MerltConfig
from merlt.benchmark import (
    create_semantic_gold_standard,
    GradedRelevanceMetrics,
    compute_graded_relevance_metrics,
    compute_latency_metrics,
    recall_at_k,
    mrr,
    hit_rate,
)

log = structlog.get_logger()

# Output directory
OUTPUT_DIR = Path("docs/experiments/EXP-016_semantic_benchmark")


async def run_semantic_benchmark(kg: LegalKnowledgeGraph, top_k: int = 10) -> Dict[str, Any]:
    """
    Esegue il benchmark semantico con valutazione graduata.

    Args:
        kg: Knowledge graph connesso
        top_k: Numero di risultati per query

    Returns:
        Dizionario con risultati completi
    """
    gs = create_semantic_gold_standard()
    log.info(f"Gold standard caricato", num_queries=len(gs))

    # Risultati per ogni query
    all_retrieved: List[List[str]] = []
    all_relevance_scores: List[Dict[str, int]] = []
    all_relevant: List[List[str]] = []
    categories: List[str] = []

    # Esegui query - usa direttamente Qdrant per avere article_urn
    for query in gs.queries:
        log.info(f"Eseguendo query {query.id}", text=query.text[:50])

        # Encode query
        query_embedding = await kg._embedding_service.encode_query_async(query.text)

        # Search in Qdrant
        response = kg._qdrant.query_points(
            collection_name=kg.config.qdrant_collection,
            query=query_embedding,
            limit=top_k,
        )

        # Estrai URN dai risultati
        retrieved_urns = [p.payload.get("article_urn", "") for p in response.points]

        all_retrieved.append(retrieved_urns)
        all_relevance_scores.append(query.relevance_scores)
        all_relevant.append(query.relevant_urns)
        categories.append(query.category.value)

    # Calcola metriche graduata
    graded_metrics = compute_graded_relevance_metrics(
        all_retrieved, all_relevance_scores, categories
    )

    # Calcola anche metriche tradizionali per confronto
    recall_1 = sum(recall_at_k(ret, rel, k=1) for ret, rel in zip(all_retrieved, all_relevant)) / len(gs)
    recall_5 = sum(recall_at_k(ret, rel, k=5) for ret, rel in zip(all_retrieved, all_relevant)) / len(gs)
    recall_10 = sum(recall_at_k(ret, rel, k=10) for ret, rel in zip(all_retrieved, all_relevant)) / len(gs)
    mrr_score = mrr(all_retrieved, all_relevant)
    hit_rate_5 = hit_rate(all_retrieved, all_relevant, k=5)

    return {
        "graded_metrics": graded_metrics.to_dict(),
        "traditional_metrics": {
            "recall_at_1": round(recall_1, 4),
            "recall_at_5": round(recall_5, 4),
            "recall_at_10": round(recall_10, 4),
            "mrr": round(mrr_score, 4),
            "hit_rate_at_5": round(hit_rate_5, 4),
        },
        "num_queries": len(gs),
    }


async def run_source_comparison(kg: LegalKnowledgeGraph, top_k: int = 10) -> Dict[str, Any]:
    """
    Confronta performance per source type (norma vs spiegazione vs ratio).
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    gs = create_semantic_gold_standard()
    source_types = ["norma", "spiegazione", "ratio", "massima"]

    results = {}

    for source_type in source_types:
        log.info(f"Testing source type: {source_type}")

        all_retrieved = []
        all_relevance_scores = []
        all_relevant = []

        for query in gs.queries:
            # Search con filtro per source_type
            query_embedding = await kg._embedding_service.encode_query_async(query.text)

            search_filter = Filter(
                must=[FieldCondition(key="source_type", match=MatchValue(value=source_type))]
            )

            response = kg._qdrant.query_points(
                collection_name=kg.config.qdrant_collection,
                query=query_embedding,
                query_filter=search_filter,
                limit=top_k,
            )

            retrieved_urns = [p.payload.get("article_urn", "") for p in response.points]
            all_retrieved.append(retrieved_urns)
            all_relevance_scores.append(query.relevance_scores)
            all_relevant.append(query.relevant_urns)

        # Metriche per questo source
        graded = compute_graded_relevance_metrics(all_retrieved, all_relevance_scores)

        recall_5 = sum(recall_at_k(ret, rel, k=5) for ret, rel in zip(all_retrieved, all_relevant)) / len(gs)
        mrr_score = mrr(all_retrieved, all_relevant)

        results[source_type] = {
            "mean_relevance_at_5": round(graded.mean_relevance_at_5, 4),
            "ndcg_at_5": round(graded.ndcg_at_5, 4),
            "queries_with_score_3": round(graded.queries_with_score_3, 4),
            "recall_at_5": round(recall_5, 4),
            "mrr": round(mrr_score, 4),
        }

    return results


async def run_latency_benchmark(kg: LegalKnowledgeGraph, iterations: int = 50) -> Dict[str, Any]:
    """
    Benchmark di latenza per le operazioni principali.
    """
    gs = create_semantic_gold_standard()
    sample_queries = [q.text for q in gs.queries[:10]]

    # Warmup
    for q in sample_queries[:3]:
        await kg.search(q, top_k=5)

    # Embedding latencies
    embedding_latencies = []
    for _ in range(iterations):
        for q in sample_queries:
            start = time.perf_counter()
            await kg._embedding_service.encode_query_async(q)
            elapsed = (time.perf_counter() - start) * 1000
            embedding_latencies.append(elapsed)

    # Full pipeline latencies
    pipeline_latencies = []
    for _ in range(iterations // 10):
        for q in sample_queries:
            start = time.perf_counter()
            await kg.search(q, top_k=10)
            elapsed = (time.perf_counter() - start) * 1000
            pipeline_latencies.append(elapsed)

    return {
        "query_embedding": compute_latency_metrics(embedding_latencies, "query_embedding").to_dict(),
        "full_pipeline": compute_latency_metrics(pipeline_latencies, "full_pipeline").to_dict(),
    }


def print_graded_results(results: Dict[str, Any]) -> None:
    """Stampa risultati con formato leggibile."""
    print("\n" + "=" * 70)
    print("EXP-016: SEMANTIC BENCHMARK RESULTS")
    print("=" * 70)

    print("\n### GRADED RELEVANCE METRICS ###")
    graded = results["graded_metrics"]
    print(f"Mean Relevance@5:    {graded['mean_relevance_at_5']:.3f} / 3.0")
    print(f"Mean Relevance@10:   {graded['mean_relevance_at_10']:.3f} / 3.0")
    print(f"NDCG@5:              {graded['ndcg_at_5']:.3f}")
    print(f"NDCG@10:             {graded['ndcg_at_10']:.3f}")
    print(f"Queries with score=3: {graded['queries_with_score_3']*100:.1f}%")
    print(f"Queries with score>=2: {graded['queries_with_score_2_plus']*100:.1f}%")

    print("\n### TRADITIONAL METRICS (for comparison) ###")
    trad = results["traditional_metrics"]
    print(f"Recall@1:     {trad['recall_at_1']:.3f}")
    print(f"Recall@5:     {trad['recall_at_5']:.3f}")
    print(f"Recall@10:    {trad['recall_at_10']:.3f}")
    print(f"MRR:          {trad['mrr']:.3f}")
    print(f"Hit Rate@5:   {trad['hit_rate_at_5']:.3f}")

    # Per categoria
    if graded.get("by_category"):
        print("\n### BY CATEGORY ###")
        print(f"{'Category':<15} {'MeanRel@5':>10} {'NDCG@5':>10} {'Score>=2':>10}")
        print("-" * 50)
        for cat, metrics in graded["by_category"].items():
            print(f"{cat:<15} {metrics['mean_relevance_at_5']:>10.3f} {metrics['ndcg_at_5']:>10.3f} {metrics['queries_with_score_2_plus']*100:>9.1f}%")


def print_source_comparison(results: Dict[str, Any]) -> None:
    """Stampa confronto tra source types."""
    print("\n### SOURCE TYPE COMPARISON ###")
    print(f"{'Source':<15} {'MeanRel@5':>10} {'NDCG@5':>10} {'Recall@5':>10} {'MRR':>10}")
    print("-" * 60)
    for source, metrics in results.items():
        print(f"{source:<15} {metrics['mean_relevance_at_5']:>10.3f} {metrics['ndcg_at_5']:>10.3f} {metrics['recall_at_5']:>10.3f} {metrics['mrr']:>10.3f}")


async def main():
    parser = argparse.ArgumentParser(description="EXP-016: Semantic RAG Benchmark")
    parser.add_argument("--full", action="store_true", help="Run full benchmark")
    parser.add_argument("--source-only", action="store_true", help="Run source comparison only")
    parser.add_argument("--latency-only", action="store_true", help="Run latency benchmark only")
    parser.add_argument("--generate-gold-standard", action="store_true", help="Generate and save gold standard")
    args = parser.parse_args()

    # Genera gold standard
    if args.generate_gold_standard:
        gs = create_semantic_gold_standard()
        output_path = OUTPUT_DIR / "gold_standard_semantic.json"
        gs.to_file(str(output_path))
        print(f"Gold standard salvato: {output_path}")
        return

    # Connetti al knowledge graph
    config = MerltConfig(
        graph_name="merl_t_dev",
        qdrant_collection="merl_t_dev_chunks"
    )
    kg = LegalKnowledgeGraph(config)
    await kg.connect()

    start_time = time.time()
    all_results = {
        "experiment": "EXP-016",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "graph_name": config.graph_name,
            "qdrant_collection": config.qdrant_collection,
            "top_k": 10,
        }
    }

    try:
        if args.full or (not args.source_only and not args.latency_only):
            # Benchmark semantico principale
            log.info("Running semantic benchmark...")
            semantic_results = await run_semantic_benchmark(kg)
            all_results["semantic_benchmark"] = semantic_results
            print_graded_results(semantic_results)

            # Source comparison
            log.info("Running source comparison...")
            source_results = await run_source_comparison(kg)
            all_results["source_comparison"] = source_results
            print_source_comparison(source_results)

            # Latency
            log.info("Running latency benchmark...")
            latency_results = await run_latency_benchmark(kg)
            all_results["latency"] = latency_results

        elif args.source_only:
            log.info("Running source comparison only...")
            source_results = await run_source_comparison(kg)
            all_results["source_comparison"] = source_results
            print_source_comparison(source_results)

        elif args.latency_only:
            log.info("Running latency benchmark only...")
            latency_results = await run_latency_benchmark(kg)
            all_results["latency"] = latency_results

        # Tempo totale
        elapsed = time.time() - start_time
        all_results["duration_seconds"] = round(elapsed, 1)
        print(f"\nBenchmark completato in {elapsed:.1f} secondi")

        # Salva risultati
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"Risultati salvati: {output_path}")

    finally:
        await kg.close()


if __name__ == "__main__":
    asyncio.run(main())
