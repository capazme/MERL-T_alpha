#!/usr/bin/env python3
"""
EXP-015: RAG Validation & Bridge Benchmark
==========================================

Esegue benchmark sistematico del sistema RAG ibrido su Libro IV Codice Civile.

Uso:
    # Benchmark completo
    python scripts/exp015_rag_benchmark.py --full

    # Solo source comparison
    python scripts/exp015_rag_benchmark.py --source-only

    # Solo latency benchmark
    python scripts/exp015_rag_benchmark.py --latency-only

    # Genera gold standard
    python scripts/exp015_rag_benchmark.py --generate-gold-standard
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

log = structlog.get_logger()
console = Console()

# Experiment paths
EXP_DIR = Path(__file__).parent.parent / "docs/experiments/EXP-015_rag_validation_benchmark"
GOLD_STANDARD_PATH = EXP_DIR / "gold_standard.json"
RESULTS_PATH = EXP_DIR / "results.json"


async def generate_gold_standard():
    """Genera e salva il gold standard."""
    from merlt.benchmark import create_libro_iv_gold_standard

    console.print("\n[bold blue]Generazione Gold Standard[/bold blue]")
    console.print("-" * 50)

    gs = create_libro_iv_gold_standard()

    # Aggiungi timestamp ai metadati
    gs.metadata["created_at"] = datetime.now().isoformat()

    # Mostra statistiche
    stats = gs.get_statistics()

    table = Table(title="Gold Standard Statistics")
    table.add_column("Metrica", style="cyan")
    table.add_column("Valore", style="green")

    table.add_row("Query totali", str(stats["total_queries"]))
    table.add_row("URN unici", str(stats["unique_relevant_urns"]))
    table.add_row("Media rilevanti/query", f"{stats['avg_relevant_per_query']:.2f}")
    table.add_row("", "")
    table.add_row("[bold]Per Categoria[/bold]", "")
    for cat, count in stats["by_category"].items():
        table.add_row(f"  {cat}", str(count))
    table.add_row("", "")
    table.add_row("[bold]Per Difficoltà[/bold]", "")
    for diff, count in stats["by_difficulty"].items():
        table.add_row(f"  {diff}", str(count))

    console.print(table)

    # Valida
    errors = gs.validate()
    if errors:
        console.print(f"\n[red]Errori di validazione: {errors}[/red]")
        return False

    # Salva
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    gs.to_file(str(GOLD_STANDARD_PATH))
    console.print(f"\n[green]Gold standard salvato: {GOLD_STANDARD_PATH}[/green]")

    return True


async def run_source_comparison(kg, gs, config):
    """Esegue confronto tra source types."""
    from merlt.benchmark import RAGBenchmark

    console.print("\n[bold blue]Fase 1: Source Comparison[/bold blue]")
    console.print("-" * 50)

    benchmark = RAGBenchmark(kg, gs, config)
    results = await benchmark.run_source_comparison()

    # Mostra tabella risultati
    table = Table(title="Source Type Comparison")
    table.add_column("Source", style="cyan")
    table.add_column("Recall@1", style="green")
    table.add_column("Recall@5", style="green")
    table.add_column("MRR", style="yellow")
    table.add_column("Hit Rate@5", style="magenta")

    for source_type, result in results.items():
        m = result.metrics
        table.add_row(
            source_type,
            f"{m.recall_at_1:.3f}",
            f"{m.recall_at_5:.3f}",
            f"{m.mrr:.3f}",
            f"{m.hit_rate_at_5:.3f}",
        )

    console.print(table)

    return results


async def run_latency_benchmark(kg, gs, config):
    """Esegue benchmark di latenza."""
    from merlt.benchmark import RAGBenchmark

    console.print("\n[bold blue]Fase 2: Latency Benchmark[/bold blue]")
    console.print("-" * 50)

    benchmark = RAGBenchmark(kg, gs, config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running latency benchmark...", total=None)
        results = await benchmark.run_latency_benchmark()
        progress.update(task, completed=True)

    # Mostra tabella risultati
    table = Table(title="Latency Metrics (ms)")
    table.add_column("Operation", style="cyan")
    table.add_column("p50", style="green")
    table.add_column("p90", style="yellow")
    table.add_column("p99", style="red")
    table.add_column("Mean", style="blue")

    for op, metrics in results.items():
        table.add_row(
            op,
            f"{metrics.median_ms:.1f}",
            f"{metrics.p90_ms:.1f}",
            f"{metrics.p99_ms:.1f}",
            f"{metrics.mean_ms:.1f}",
        )

    console.print(table)

    return results


async def run_full_benchmark():
    """Esegue benchmark completo."""
    from merlt import LegalKnowledgeGraph
    from merlt.core.legal_knowledge_graph import MerltConfig
    from merlt.benchmark import RAGBenchmark, BenchmarkConfig, GoldStandard

    console.print("\n[bold green]EXP-015: RAG Validation & Bridge Benchmark[/bold green]")
    console.print("=" * 60)

    # Verifica gold standard
    if not GOLD_STANDARD_PATH.exists():
        console.print("[yellow]Gold standard non trovato. Genero...[/yellow]")
        await generate_gold_standard()

    # Carica gold standard
    gs = GoldStandard.from_file(str(GOLD_STANDARD_PATH))
    console.print(f"Loaded gold standard: {len(gs)} queries")

    # Connetti al knowledge graph con config per DEV
    console.print("\nConnecting to knowledge graph...")
    config = MerltConfig(
        graph_name="merl_t_dev",
        qdrant_collection="merl_t_dev_chunks",  # Usa la collection con i dati EXP-014
    )
    kg = LegalKnowledgeGraph(config=config)
    await kg.connect()
    console.print("[green]Connected![/green]")

    # Config
    config = BenchmarkConfig(
        top_k=10,
        source_types=["norma", "spiegazione", "ratio", "massima", "all"],
        latency_iterations=100,
        latency_warmup=10,
    )

    # Esegui benchmark
    benchmark = RAGBenchmark(kg, gs, config)
    results = await benchmark.run_full_benchmark("EXP-015")

    # Mostra risultati principali
    console.print("\n" + "=" * 60)
    console.print("[bold green]RISULTATI PRINCIPALI[/bold green]")
    console.print("=" * 60)

    table = Table(title="Overall Metrics")
    table.add_column("Metrica", style="cyan")
    table.add_column("Valore", style="green")

    m = results.overall_metrics
    table.add_row("Recall@1", f"{m.recall_at_1:.3f}")
    table.add_row("Recall@5", f"{m.recall_at_5:.3f}")
    table.add_row("Recall@10", f"{m.recall_at_10:.3f}")
    table.add_row("MRR", f"{m.mrr:.3f}")
    table.add_row("Hit Rate@5", f"{m.hit_rate_at_5:.3f}")
    table.add_row("Query valutate", str(m.num_queries))

    console.print(table)

    # Risultati per categoria
    if results.by_category:
        table = Table(title="Metrics by Category")
        table.add_column("Categoria", style="cyan")
        table.add_column("Recall@5", style="green")
        table.add_column("MRR", style="yellow")
        table.add_column("Queries", style="blue")

        for cat, metrics in results.by_category.items():
            table.add_row(
                cat,
                f"{metrics.recall_at_5:.3f}",
                f"{metrics.mrr:.3f}",
                str(metrics.num_queries),
            )

        console.print(table)

    # Risultati per source
    if results.by_source:
        table = Table(title="Metrics by Source Type")
        table.add_column("Source", style="cyan")
        table.add_column("Recall@5", style="green")
        table.add_column("MRR", style="yellow")

        for source, result in results.by_source.items():
            table.add_row(
                source,
                f"{result.metrics.recall_at_5:.3f}",
                f"{result.metrics.mrr:.3f}",
            )

        console.print(table)

    # Latenza
    if results.latency_metrics:
        table = Table(title="Latency Summary (ms)")
        table.add_column("Operation", style="cyan")
        table.add_column("p50", style="green")
        table.add_column("p99", style="red")

        for op, metrics in results.latency_metrics.items():
            table.add_row(
                op,
                f"{metrics.median_ms:.1f}",
                f"{metrics.p99_ms:.1f}",
            )

        console.print(table)

    # Salva risultati
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    results.to_file(str(RESULTS_PATH))
    console.print(f"\n[green]Risultati salvati: {RESULTS_PATH}[/green]")

    return results


async def main():
    parser = argparse.ArgumentParser(
        description="EXP-015: RAG Validation & Bridge Benchmark"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Esegui benchmark completo"
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Esegui solo source comparison"
    )
    parser.add_argument(
        "--latency-only",
        action="store_true",
        help="Esegui solo latency benchmark"
    )
    parser.add_argument(
        "--generate-gold-standard",
        action="store_true",
        help="Genera gold standard"
    )

    args = parser.parse_args()

    try:
        if args.generate_gold_standard:
            await generate_gold_standard()
        elif args.full or (not args.source_only and not args.latency_only):
            await run_full_benchmark()
        else:
            from merlt import LegalKnowledgeGraph
            from merlt.benchmark import BenchmarkConfig, GoldStandard

            # Carica componenti comuni
            gs = GoldStandard.from_file(str(GOLD_STANDARD_PATH))
            kg = LegalKnowledgeGraph()
            await kg.connect()
            config = BenchmarkConfig()

            if args.source_only:
                await run_source_comparison(kg, gs, config)
            if args.latency_only:
                await run_latency_benchmark(kg, gs, config)

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrotto dall'utente[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Errore: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
