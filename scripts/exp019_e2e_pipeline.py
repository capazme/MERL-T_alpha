#!/usr/bin/env python3
"""
EXP-019: End-to-End Pipeline Test

Valida il flusso completo kg.interpret() con:
- LegalKnowledgeGraph connesso ai database
- Multi-Expert System
- AI Service (OpenRouter)

Usage:
    source .venv/bin/activate
    docker-compose -f docker-compose.dev.yml up -d
    python scripts/exp019_e2e_pipeline.py

Output:
    docs/experiments/EXP-019_e2e_pipeline/results/responses.json
    docs/experiments/EXP-019_e2e_pipeline/results/latency.json
    docs/experiments/EXP-019_e2e_pipeline/results/quality_scores.md
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / ".env")

from merlt import LegalKnowledgeGraph, MerltConfig, InterpretationResult


# Config paths
QUERIES_PATH = project_root / "docs/experiments/EXP-019_e2e_pipeline/test_queries.yaml"
RESULTS_DIR = project_root / "docs/experiments/EXP-019_e2e_pipeline/results"


async def run_experiment():
    """Esegue l'esperimento E2E completo."""
    print("=" * 60)
    print("EXP-019: End-to-End Pipeline Test")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("WARNING: OPENROUTER_API_KEY not set. AI features will be limited.")

    # Load queries
    with open(QUERIES_PATH) as f:
        query_dataset = yaml.safe_load(f)

    # Initialize LegalKnowledgeGraph
    config = MerltConfig(
        graph_name="merl_t_dev",
        falkordb_host="localhost",
        falkordb_port=6380,
        qdrant_host="localhost",
        qdrant_port=6333,
        postgres_host="localhost",
        postgres_port=5433,
    )

    kg = LegalKnowledgeGraph(config)

    print("\nConnecting to databases...")
    try:
        await kg.connect()
        print(f"Connected: FalkorDB={kg.falkordb is not None}, "
              f"Qdrant={kg.qdrant is not None}, "
              f"Bridge={kg.bridge_table is not None}")
    except Exception as e:
        print(f"ERROR connecting: {e}")
        print("Make sure databases are running: docker-compose -f docker-compose.dev.yml up -d")
        return

    # Results storage
    all_responses = []
    latency_data = []

    total_queries = sum(len(cat["queries"]) for cat in query_dataset.values())
    processed = 0

    print(f"\nProcessing {total_queries} queries across 5 categories...")
    print("-" * 60)

    for category, data in query_dataset.items():
        expected_scenario = data["expected_scenario"]
        queries = data["queries"]

        print(f"\n[{category.upper()}] Scenario: {expected_scenario}")

        for query in queries:
            processed += 1
            print(f"  [{processed}/{total_queries}] {query[:50]}...")

            start_time = time.time()

            try:
                # Run full interpret() pipeline
                result = await kg.interpret(
                    query=query,
                    include_search=True,
                    max_experts=4,
                    aggregation_method="weighted_average",
                    timeout_seconds=30.0,
                )

                execution_time = (time.time() - start_time) * 1000

                # Store results
                response_data = {
                    "query": query,
                    "category": category,
                    "expected_scenario": expected_scenario,
                    "result": result.to_dict(),
                    "execution_time_ms": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }

                all_responses.append(response_data)

                latency_data.append({
                    "query": query[:50],
                    "category": category,
                    "execution_time_ms": execution_time,
                    "experts_used": len(result.expert_contributions),
                    "confidence": result.confidence,
                })

                # Verify scenario expectations
                top_experts = sorted(
                    result.routing_decision.get("expert_weights", {}).items(),
                    key=lambda x: x[1],
                    reverse=True
                ) if result.routing_decision else []

                scenario_met = False
                if expected_scenario == "single_expert_dominance":
                    scenario_met = top_experts and top_experts[0][1] > 0.4
                elif expected_scenario == "multi_expert_balance":
                    high_weight_experts = sum(1 for _, w in top_experts if w > 0.2)
                    scenario_met = high_weight_experts >= 2

                status = "OK" if scenario_met else "UNEXPECTED"
                print(f"      [{status}] Conf: {result.confidence:.2f}, "
                      f"Experts: {list(result.expert_contributions.keys())}, "
                      f"Time: {execution_time:.0f}ms")

            except Exception as e:
                print(f"    ERROR: {e}")
                all_responses.append({
                    "query": query,
                    "category": category,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

    # Calculate metrics
    metrics = calculate_metrics(all_responses, latency_data)

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_DIR / "responses.json", "w") as f:
        json.dump(all_responses, f, indent=2, ensure_ascii=False)

    with open(RESULTS_DIR / "latency.json", "w") as f:
        json.dump(latency_data, f, indent=2, ensure_ascii=False)

    # Generate quality scores markdown
    quality_md = generate_quality_report(metrics)
    with open(RESULTS_DIR / "quality_scores.md", "w") as f:
        f.write(quality_md)

    # Cleanup
    await kg.close()

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total queries: {metrics['total_queries']}")
    print(f"Successful: {metrics['successful_queries']}")
    print(f"Errors: {metrics['error_count']}")
    print(f"\nPipeline Success Rate: {metrics['pipeline_success_rate']:.1%}")
    print(f"Average Latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"Average Confidence: {metrics['avg_confidence']:.3f}")
    print(f"\nExpert Utilization: {metrics['expert_utilization']}")
    print(f"\nResults saved to: {RESULTS_DIR}")


def calculate_metrics(responses: List[Dict], latency_data: List[Dict]) -> Dict[str, Any]:
    """Calcola metriche aggregate."""
    successful = [r for r in responses if "error" not in r]
    errors = [r for r in responses if "error" in r]

    # Pipeline success rate
    success_rate = len(successful) / len(responses) if responses else 0

    # Latency
    latencies = [r["execution_time_ms"] for r in latency_data]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    # Confidence
    confidences = [r.get("result", {}).get("confidence", 0) for r in successful]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Expert utilization
    all_experts = set()
    for r in successful:
        experts = r.get("result", {}).get("expert_contributions", {})
        all_experts.update(experts.keys())

    # Source coverage
    with_sources = sum(
        1 for r in successful
        if len(r.get("result", {}).get("combined_legal_basis", [])) > 0
    )
    source_coverage = with_sources / len(successful) if successful else 0

    return {
        "experiment": "EXP-019",
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(responses),
        "successful_queries": len(successful),
        "error_count": len(errors),
        "pipeline_success_rate": success_rate,
        "avg_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "min_latency_ms": min_latency,
        "avg_confidence": avg_confidence,
        "expert_utilization": list(all_experts),
        "source_coverage": source_coverage,
    }


def generate_quality_report(metrics: Dict[str, Any]) -> str:
    """Genera report markdown."""
    return f"""# EXP-019: Quality Report

Generated: {metrics['timestamp']}

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Pipeline Success Rate | {metrics['pipeline_success_rate']:.1%} | > 95% | {'OK' if metrics['pipeline_success_rate'] > 0.95 else 'BELOW'} |
| Average Latency | {metrics['avg_latency_ms']:.0f}ms | < 5000ms | {'OK' if metrics['avg_latency_ms'] < 5000 else 'SLOW'} |
| Average Confidence | {metrics['avg_confidence']:.3f} | > 0.5 | {'OK' if metrics['avg_confidence'] > 0.5 else 'LOW'} |
| Source Coverage | {metrics['source_coverage']:.1%} | > 80% | {'OK' if metrics['source_coverage'] > 0.8 else 'LOW'} |

## Latency Distribution

- Min: {metrics['min_latency_ms']:.0f}ms
- Avg: {metrics['avg_latency_ms']:.0f}ms
- Max: {metrics['max_latency_ms']:.0f}ms

## Expert Utilization

Experts used: {', '.join(metrics['expert_utilization']) or 'None'}

## Errors

Total errors: {metrics['error_count']}
"""


if __name__ == "__main__":
    asyncio.run(run_experiment())
