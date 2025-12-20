#!/usr/bin/env python3
"""
EXP-018: Expert Comparison Experiment

Esegue 50 query giuridiche per confrontare i 4 Expert interpretativi.

Metriche raccolte:
- Routing accuracy (query_type detection)
- Confidence distribution per expert
- Source type distribution
- Execution time

Usage:
    source .venv/bin/activate
    python scripts/exp018_expert_comparison.py

Output:
    docs/experiments/EXP-018_expert_comparison/results/responses.json
    docs/experiments/EXP-018_expert_comparison/results/metrics.json
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

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from merlt.experts import (
    MultiExpertOrchestrator,
    OrchestratorConfig,
    ExpertRouter,
    ExpertContext,
)


# Config paths
QUERIES_PATH = project_root / "docs/experiments/EXP-018_expert_comparison/queries.yaml"
RESULTS_DIR = project_root / "docs/experiments/EXP-018_expert_comparison/results"


async def run_experiment():
    """Esegue l'esperimento completo."""
    print("=" * 60)
    print("EXP-018: Expert Comparison")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("WARNING: OPENROUTER_API_KEY not set. Running without AI service.")
        ai_service = None
    else:
        from merlt.rlcf.ai_service import OpenRouterService
        ai_service = OpenRouterService()
        print("OpenRouter AI service initialized.")

    # Load queries
    with open(QUERIES_PATH) as f:
        query_dataset = yaml.safe_load(f)

    # Initialize orchestrator
    config = OrchestratorConfig(
        max_experts=4,
        aggregation_method="weighted_average",
        timeout_seconds=30.0,
        selection_threshold=0.1,  # Lower threshold to get more experts
    )

    orchestrator = MultiExpertOrchestrator(
        tools=[],  # No tools for this experiment
        ai_service=ai_service,
        config=config,
    )

    router = ExpertRouter()

    # Results storage
    all_responses = []
    routing_results = []

    total_queries = sum(len(cat["queries"]) for cat in query_dataset.values())
    processed = 0

    print(f"\nProcessing {total_queries} queries across 5 categories...")
    print("-" * 60)

    for category, data in query_dataset.items():
        expected_expert = data["expected_expert"]
        queries = data["queries"]

        print(f"\n[{category.upper()}] Expected expert: {expected_expert}")

        for query in queries:
            processed += 1
            print(f"  [{processed}/{total_queries}] {query[:50]}...")

            start_time = time.time()

            try:
                # Step 1: Test routing
                context = ExpertContext(query_text=query)
                routing_decision = await router.route(context)

                # Step 2: Run full orchestration
                response = await orchestrator.process(query)

                execution_time = (time.time() - start_time) * 1000

                # Store results
                result = {
                    "query": query,
                    "category": category,
                    "expected_expert": expected_expert,
                    "routing": {
                        "query_type": routing_decision.query_type,
                        "expert_weights": routing_decision.expert_weights,
                        "confidence": routing_decision.confidence,
                    },
                    "response": {
                        "synthesis": response.synthesis[:500] if response.synthesis else "",
                        "confidence": response.confidence,
                        "expert_contributions": list(response.expert_contributions.keys()),
                        "aggregation_method": response.aggregation_method,
                        "source_count": len(response.combined_legal_basis),
                        "conflicts": response.conflicts or [],
                    },
                    "execution_time_ms": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }

                all_responses.append(result)

                # Check routing accuracy
                top_expert = max(
                    routing_decision.expert_weights.items(),
                    key=lambda x: x[1]
                )[0]

                routing_results.append({
                    "category": category,
                    "expected": expected_expert,
                    "actual_query_type": routing_decision.query_type,
                    "top_expert": top_expert,
                    "correct": top_expert == expected_expert,
                })

                print(f"      Routing: {routing_decision.query_type}, Top: {top_expert}, Conf: {response.confidence:.2f}")

            except Exception as e:
                print(f"    ERROR: {e}")
                all_responses.append({
                    "query": query,
                    "category": category,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

    # Calculate metrics
    metrics = calculate_metrics(all_responses, routing_results)

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_DIR / "responses.json", "w") as f:
        json.dump(all_responses, f, indent=2, ensure_ascii=False)

    with open(RESULTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # Cleanup
    if ai_service:
        await ai_service.close()

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total queries: {metrics['total_queries']}")
    print(f"Successful: {metrics['successful_queries']}")
    print(f"Errors: {metrics['error_count']}")
    print(f"\nRouting Accuracy: {metrics['routing_accuracy']:.1%}")
    print(f"Average Confidence: {metrics['avg_confidence']:.3f}")
    print(f"Average Execution Time: {metrics['avg_execution_time_ms']:.0f}ms")
    print(f"\nResults saved to: {RESULTS_DIR}")


def calculate_metrics(responses: List[Dict], routing_results: List[Dict]) -> Dict[str, Any]:
    """Calcola metriche aggregate."""
    successful = [r for r in responses if "error" not in r]
    errors = [r for r in responses if "error" in r]

    # Routing accuracy
    correct_routing = sum(1 for r in routing_results if r.get("correct", False))
    total_routing = len(routing_results)
    routing_accuracy = correct_routing / total_routing if total_routing > 0 else 0

    # Confidence distribution
    confidences = [r["response"]["confidence"] for r in successful if "response" in r]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Execution time
    exec_times = [r["execution_time_ms"] for r in successful if "execution_time_ms" in r]
    avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0

    # Expert usage distribution
    expert_usage = {}
    for r in successful:
        for expert in r.get("response", {}).get("expert_contributions", []):
            expert_usage[expert] = expert_usage.get(expert, 0) + 1

    # Per-category metrics
    category_metrics = {}
    for category in ["definitional", "interpretive", "procedural", "constitutional", "jurisprudential"]:
        cat_responses = [r for r in successful if r.get("category") == category]
        cat_routing = [r for r in routing_results if r.get("category") == category]

        cat_correct = sum(1 for r in cat_routing if r.get("correct", False))
        cat_total = len(cat_routing)

        cat_confidences = [r["response"]["confidence"] for r in cat_responses if "response" in r]

        category_metrics[category] = {
            "total": len(cat_responses),
            "routing_accuracy": cat_correct / cat_total if cat_total > 0 else 0,
            "avg_confidence": sum(cat_confidences) / len(cat_confidences) if cat_confidences else 0,
        }

    return {
        "experiment": "EXP-018",
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(responses),
        "successful_queries": len(successful),
        "error_count": len(errors),
        "routing_accuracy": routing_accuracy,
        "avg_confidence": avg_confidence,
        "avg_execution_time_ms": avg_exec_time,
        "expert_usage": expert_usage,
        "category_metrics": category_metrics,
    }


if __name__ == "__main__":
    asyncio.run(run_experiment())
