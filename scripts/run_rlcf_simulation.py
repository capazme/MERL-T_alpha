#!/usr/bin/env python3
"""
RLCF Simulation Runner - Entry Point CLI

Esegue la simulazione RLCF per validare il loop di feedback
senza necessità di una community reale.

Uso:
    python scripts/run_rlcf_simulation.py
    python scripts/run_rlcf_simulation.py --config custom_config.yaml
    python scripts/run_rlcf_simulation.py --iterations 10 --no-llm-judge

Opzioni:
    --config PATH       File di configurazione YAML
    --iterations N      Numero iterazioni training (override config)
    --no-llm-judge      Disabilita LLM-as-Judge (solo metriche oggettive)
    --output-dir PATH   Directory output (override config)
    --verbose           Output dettagliato
    --dry-run           Mostra configurazione senza eseguire

Variabili d'ambiente:
    RLCF_JUDGE_MODEL    Modello LLM per valutazione
    OPENROUTER_API_KEY  API key per OpenRouter

Esempio:
    # Esecuzione standard
    python scripts/run_rlcf_simulation.py

    # Con modello judge personalizzato
    RLCF_JUDGE_MODEL=anthropic/claude-3.5-sonnet python scripts/run_rlcf_simulation.py

    # Solo metriche oggettive (no API calls)
    python scripts/run_rlcf_simulation.py --no-llm-judge
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Aggiungi root al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Carica variabili d'ambiente da .env
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def setup_logging(verbose: bool = False):
    """Configura logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    # Riduci verbosità di alcuni logger
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RLCF Simulation Runner - Valida il loop di feedback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="File di configurazione YAML"
    )

    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=None,
        help="Numero iterazioni training"
    )

    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Disabilita LLM-as-Judge"
    )

    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Directory output"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Output dettagliato"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra configurazione senza eseguire"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed per riproducibilità"
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="Usa componenti reali (LegalKnowledgeGraph, RLCFOrchestrator)"
    )

    parser.add_argument(
        "--check-components",
        action="store_true",
        help="Verifica disponibilità componenti reali e esce"
    )

    parser.add_argument(
        "--graph-name",
        type=str,
        default="merl_t_dev",
        help="Nome del grafo FalkorDB (default: merl_t_dev)"
    )

    parser.add_argument(
        "--falkordb-port",
        type=int,
        default=6380,
        help="Porta FalkorDB (default: 6380)"
    )

    return parser.parse_args()


async def main():
    """Entry point principale."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("rlcf_simulation")
    logger.info("=" * 60)
    logger.info("RLCF Simulation Runner")
    logger.info("=" * 60)

    # Import componenti
    from merlt.rlcf.simulator.config import load_config, SimulationConfig
    from merlt.rlcf.simulator.experiment import RLCFExperiment, ExperimentConfig
    from merlt.rlcf.simulator.statistics import StatisticalAnalyzer
    from merlt.rlcf.simulator.outputs import ThesisOutputGenerator

    # Check componenti se richiesto
    if args.check_components:
        from merlt.rlcf.simulator.integration import check_real_components
        status = check_real_components()
        logger.info("\nStato componenti reali:")
        for component, available in status.items():
            emoji = "✓" if available else "✗"
            logger.info(f"  [{emoji}] {component}")

        all_ready = all(status.values())
        if all_ready:
            logger.info("\n✓ Tutti i componenti sono disponibili per --real")
        else:
            logger.info("\n✗ Alcuni componenti non sono disponibili")
            logger.info("  Assicurati che FalkorDB e Qdrant siano in esecuzione:")
            logger.info("    docker-compose -f docker-compose.dev.yml up -d")
        return 0 if all_ready else 1

    # Carica configurazione
    config = load_config(args.config)

    # Override da CLI
    if args.iterations is not None:
        config.training_iterations = args.iterations

    if args.no_llm_judge:
        config.use_llm_judge = False

    if args.output_dir is not None:
        config.output_dir = args.output_dir

    if args.seed is not None:
        config.random_seed = args.seed

    # Mostra configurazione
    logger.info("Configurazione:")
    logger.info(f"  - Experiment: {config.experiment_name}")
    logger.info(f"  - Random seed: {config.random_seed}")
    logger.info(f"  - Baseline queries: {config.baseline_queries}")
    logger.info(f"  - Training iterations: {config.training_iterations}")
    logger.info(f"  - Queries per iteration: {config.queries_per_training}")
    logger.info(f"  - User pool: {sum(config.user_distribution.values())} users")
    logger.info(f"  - LLM Judge: {'Enabled' if config.use_llm_judge else 'Disabled'}")
    if config.use_llm_judge:
        logger.info(f"  - Judge model: {config.llm_judge_model}")
    logger.info(f"  - Output dir: {config.output_dir}")
    logger.info(f"  - Mode: {'REAL components' if args.real else 'Mock components'}")
    if args.real:
        logger.info(f"  - Graph name: {args.graph_name}")

    if args.dry_run:
        logger.info("\n[DRY RUN] Configurazione mostrata. Nessuna esecuzione.")
        return

    # Verifica API key se LLM Judge attivo
    if config.use_llm_judge:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OPENROUTER_API_KEY non impostata. LLM Judge potrebbe fallire.")
            logger.info("Puoi disabilitare LLM Judge con --no-llm-judge")

    # Crea ExperimentConfig
    exp_config = ExperimentConfig(
        experiment_name=config.experiment_name,
        random_seed=config.random_seed,
        baseline_queries=config.baseline_queries,
        training_iterations=config.training_iterations,
        queries_per_training=config.queries_per_training,
        user_distribution=config.user_distribution,
        use_llm_judge=config.use_llm_judge,
        llm_judge_model=config.llm_judge_model,
        objective_weight=config.objective_weight,
        subjective_weight=config.subjective_weight,
        output_dir=config.output_dir,
    )

    # Progress callback per terminale
    def progress_callback(phase: str, progress: float):
        bar_len = 30
        filled = int(bar_len * progress)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{bar}] {phase}: {progress:.0%}", end="", flush=True)
        if progress >= 1.0:
            print()  # Newline quando completo

    # Crea e esegui esperimento
    logger.info("\nAvvio esperimento...")
    start_time = datetime.now()

    experiment = None
    try:
        if args.real:
            # Usa componenti reali
            from merlt.rlcf.simulator.integration import (
                create_integrated_experiment,
                cleanup_experiment,
            )

            logger.info("Inizializzazione componenti reali...")
            experiment = await create_integrated_experiment(
                config=exp_config,
                use_real_components=True,
                graph_name=args.graph_name,
                falkordb_port=args.falkordb_port,
                progress_callback=progress_callback,
            )
            logger.info("Componenti reali inizializzati ✓")
        else:
            # Usa mock
            experiment = RLCFExperiment(
                config=exp_config,
                expert_system=None,
                rlcf_orchestrator=None,
                weight_store=None,
                progress_callback=progress_callback
            )

        results = await experiment.run()

    except Exception as e:
        logger.error(f"Errore durante l'esperimento: {e}")
        raise
    finally:
        # Cleanup componenti reali
        if args.real and experiment:
            from merlt.rlcf.simulator.integration import cleanup_experiment
            await cleanup_experiment(experiment)

    # Analisi statistica
    logger.info("\nAnalisi statistica...")
    analyzer = StatisticalAnalyzer(
        alpha=0.05,
        use_bonferroni=True,
        bootstrap_samples=1000
    )
    stats = analyzer.analyze(results)

    # Genera output
    logger.info("\nGenerazione output...")
    output_gen = ThesisOutputGenerator(
        output_dir=config.output_dir,
        formats=config.output_formats
    )
    paths = output_gen.generate_all(results, stats)

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 60)
    logger.info("RISULTATI ESPERIMENTO")
    logger.info("=" * 60)

    # Ipotesi
    def result_emoji(passed: bool) -> str:
        return "✓" if passed else "✗"

    logger.info(f"\nH1: Feedback Persistence = {stats.h1_feedback_persistence.value:.1%} "
                f"(target: {stats.h1_feedback_persistence.target:.0%}) "
                f"[{result_emoji(stats.h1_feedback_persistence.passed)}]")

    logger.info(f"H2: Authority Convergence = {stats.h2_authority_convergence.value:+.1%} "
                f"(target: >{stats.h2_authority_convergence.target:.0%}) "
                f"[{result_emoji(stats.h2_authority_convergence.passed)}]")

    logger.info(f"H3: Weight Stability (WDC) = {stats.h3_weight_stability.value:.2f} "
                f"(target: <{stats.h3_weight_stability.target:.1f}) "
                f"[{result_emoji(stats.h3_weight_stability.passed)}]")

    logger.info(f"H4: Response Improvement = {stats.h4_response_improvement.value:+.1%} "
                f"(target: >{stats.h4_response_improvement.target:.0%}) "
                f"[{result_emoji(stats.h4_response_improvement.passed)}]")

    # Summary
    logger.info(f"\nSuccesso complessivo: {result_emoji(stats.overall_success)} "
                f"{'TUTTE LE IPOTESI CONFERMATE' if stats.overall_success else 'Alcune ipotesi non confermate'}")

    logger.info(f"\nStatistiche:")
    logger.info(f"  - Durata totale: {duration:.1f}s")
    logger.info(f"  - Query processate: {results.baseline.queries_processed + results.post_training.queries_processed + sum(t.queries_processed for t in results.training)}")
    logger.info(f"  - Feedback generati: {results.total_feedbacks}")
    logger.info(f"  - Feedback persistiti: {results.total_feedbacks_persisted}")

    logger.info(f"\nOutput salvati in: {config.output_dir}")
    if paths.json_trace:
        logger.info(f"  - JSON: {os.path.basename(paths.json_trace)}")
    if paths.csv_metrics:
        logger.info(f"  - CSV: {os.path.basename(paths.csv_metrics)}")
    if paths.pdf_authority:
        logger.info(f"  - PDF: {os.path.basename(paths.pdf_authority)}")
    if paths.tex_results:
        logger.info(f"  - LaTeX: {os.path.basename(paths.tex_results)}")
    if paths.md_report:
        logger.info(f"  - Report: {os.path.basename(paths.md_report)}")

    logger.info("\n" + "=" * 60)
    logger.info("Simulazione completata!")
    logger.info("=" * 60)

    return 0 if stats.overall_success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Errore fatale: {e}")
        sys.exit(1)
