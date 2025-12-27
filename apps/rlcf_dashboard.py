"""
RLCF Simulation Dashboard - Streamlit App

Dashboard interattiva per monitoraggio e visualizzazione
della simulazione RLCF.

Features:
1. Configurazione parametri simulazione
2. Esecuzione con progress tracking
3. Visualizzazione live di authority e pesi
4. Risultati ipotesi con grafici
5. Export risultati in vari formati

Avvio:
    streamlit run apps/rlcf_dashboard.py --server.port 8503
"""

import streamlit as st
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# Aggiungi root al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Import componenti
try:
    from merlt.rlcf.simulator.config import SimulationConfig
    from merlt.rlcf.simulator.experiment import RLCFExperiment, ExperimentConfig
    from merlt.rlcf.simulator.statistics import StatisticalAnalyzer
    from merlt.rlcf.simulator.outputs import ThesisOutputGenerator
    from merlt.rlcf.simulator.users import PROFILES
    SIMULATOR_AVAILABLE = True
except ImportError as e:
    SIMULATOR_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Page config
st.set_page_config(
    page_title="RLCF Simulation Dashboard",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .passed {
        color: #28a745;
        font-weight: bold;
    }
    .failed {
        color: #dc3545;
        font-weight: bold;
    }
    .hypothesis-box {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("🔄 RLCF Simulation Dashboard")
    st.markdown("*Validazione scientifica del loop di feedback*")

    if not SIMULATOR_AVAILABLE:
        st.error(f"Simulator non disponibile: {IMPORT_ERROR}")
        st.stop()

    # Sidebar - Configuration
    with st.sidebar:
        st.header("⚙️ Configurazione")

        st.subheader("Experiment")
        experiment_name = st.text_input("Nome Esperimento", "EXP-021_RLCF_Simulation")
        random_seed = st.number_input("Random Seed", value=42, min_value=0)

        st.subheader("Fasi")
        baseline_queries = st.number_input("Query Baseline", value=10, min_value=1, max_value=50)
        training_iterations = st.slider("Iterazioni Training", 1, 10, 5)
        queries_per_training = st.number_input("Query per Iterazione", value=20, min_value=5, max_value=50)

        st.subheader("Utenti")
        st.markdown("Distribuzione pool utenti:")
        strict_expert = st.number_input("Strict Expert", value=3, min_value=0, max_value=10)
        domain_specialist = st.number_input("Domain Specialist", value=5, min_value=0, max_value=10)
        lenient_student = st.number_input("Lenient Student", value=8, min_value=0, max_value=10)
        random_noise = st.number_input("Random Noise", value=4, min_value=0, max_value=10)

        total_users = strict_expert + domain_specialist + lenient_student + random_noise
        st.info(f"Totale utenti: {total_users}")

        st.subheader("Valutazione")
        use_llm_judge = st.checkbox("Usa LLM-as-Judge", value=True)
        if use_llm_judge:
            llm_model = st.selectbox(
                "Modello Judge",
                [
                    "google/gemini-2.5-flash",
                    "google/gemini-2.5-pro",
                    "anthropic/claude-3.5-sonnet",
                    "openai/gpt-4o-mini",
                ]
            )
        else:
            llm_model = "google/gemini-2.5-flash"

        objective_weight = st.slider("Peso Metriche Oggettive", 0.0, 1.0, 0.4)
        subjective_weight = 1.0 - objective_weight
        st.caption(f"Peso Metriche Soggettive: {subjective_weight:.1f}")

    # Main content - Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 Esecuzione", "📊 Risultati", "📈 Grafici", "📥 Export"])

    # Tab 1: Execution
    with tab1:
        st.header("Esecuzione Simulazione")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Configurazione Corrente")

            config_df = pd.DataFrame({
                "Parametro": [
                    "Baseline Queries",
                    "Training Iterations",
                    "Queries/Iteration",
                    "Total Users",
                    "LLM Judge",
                    "Objective Weight",
                ],
                "Valore": [
                    baseline_queries,
                    training_iterations,
                    queries_per_training,
                    total_users,
                    "✓" if use_llm_judge else "✗",
                    f"{objective_weight:.1f}",
                ]
            })
            st.table(config_df)

        with col2:
            st.subheader("User Pool")

            user_data = pd.DataFrame({
                "Profilo": ["Strict Expert", "Domain Specialist", "Lenient Student", "Random Noise"],
                "Count": [strict_expert, domain_specialist, lenient_student, random_noise],
                "Authority Base": [0.85, 0.70, 0.25, 0.10],
            })
            st.bar_chart(user_data.set_index("Profilo")["Count"])

        st.divider()

        # Run button
        if st.button("▶️ Avvia Simulazione", type="primary", use_container_width=True):
            run_simulation(
                experiment_name=experiment_name,
                random_seed=random_seed,
                baseline_queries=baseline_queries,
                training_iterations=training_iterations,
                queries_per_training=queries_per_training,
                user_distribution={
                    "strict_expert": strict_expert,
                    "domain_specialist": domain_specialist,
                    "lenient_student": lenient_student,
                    "random_noise": random_noise,
                },
                use_llm_judge=use_llm_judge,
                llm_model=llm_model,
                objective_weight=objective_weight,
            )

    # Tab 2: Results
    with tab2:
        st.header("Risultati Ipotesi")

        if "results" not in st.session_state:
            st.info("Esegui una simulazione per vedere i risultati")
        else:
            results = st.session_state["results"]
            stats = st.session_state["stats"]

            # Hypothesis cards
            col1, col2 = st.columns(2)

            with col1:
                render_hypothesis_card(
                    "H1: Feedback Persistence",
                    stats.h1_feedback_persistence,
                    "Rate = 100%"
                )
                render_hypothesis_card(
                    "H3: Weight Stability",
                    stats.h3_weight_stability,
                    "WDC < 0.5"
                )

            with col2:
                render_hypothesis_card(
                    "H2: Authority Convergence",
                    stats.h2_authority_convergence,
                    "> 20%"
                )
                render_hypothesis_card(
                    "H4: Response Improvement",
                    stats.h4_response_improvement,
                    "> 10%"
                )

            st.divider()

            # Overall result
            if stats.overall_success:
                st.success("✅ **SUCCESSO**: Tutte le ipotesi sono state confermate!")
            elif stats.critical_success:
                st.warning("⚠️ **PARZIALE**: Ipotesi confermate a soglia critica")
            else:
                st.error("❌ **FALLITO**: Alcune ipotesi non sono state confermate")

    # Tab 3: Charts
    with tab3:
        st.header("Grafici")

        if "results" not in st.session_state:
            st.info("Esegui una simulazione per vedere i grafici")
        else:
            results = st.session_state["results"]

            chart_type = st.selectbox(
                "Seleziona grafico",
                ["Authority Evolution", "Weight Convergence", "Improvement Comparison", "User Distribution"]
            )

            if chart_type == "Authority Evolution":
                render_authority_chart(results)
            elif chart_type == "Weight Convergence":
                render_weight_chart(results)
            elif chart_type == "Improvement Comparison":
                render_improvement_chart(results)
            elif chart_type == "User Distribution":
                render_user_chart(results)

    # Tab 4: Export
    with tab4:
        st.header("Export Risultati")

        if "results" not in st.session_state:
            st.info("Esegui una simulazione per esportare i risultati")
        else:
            results = st.session_state["results"]
            stats = st.session_state["stats"]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("📄 JSON")
                json_data = json.dumps(results.to_dict(), indent=2, default=str)
                st.download_button(
                    "Download JSON",
                    json_data,
                    file_name=f"rlcf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            with col2:
                st.subheader("📊 CSV")
                if results.baseline.results:
                    df = create_metrics_df(results)
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv_data,
                        file_name=f"rlcf_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

            with col3:
                st.subheader("📝 Report")
                report = create_markdown_report(results, stats)
                st.download_button(
                    "Download Report",
                    report,
                    file_name=f"rlcf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )


def run_simulation(**kwargs):
    """Esegue la simulazione con progress tracking."""

    # Create config
    config = ExperimentConfig(
        experiment_name=kwargs["experiment_name"],
        random_seed=kwargs["random_seed"],
        baseline_queries=kwargs["baseline_queries"],
        training_iterations=kwargs["training_iterations"],
        queries_per_training=kwargs["queries_per_training"],
        user_distribution=kwargs["user_distribution"],
        use_llm_judge=kwargs["use_llm_judge"],
        llm_judge_model=kwargs["llm_model"],
        objective_weight=kwargs["objective_weight"],
        subjective_weight=1.0 - kwargs["objective_weight"],
        output_dir="",  # Non salvare file
    )

    # Progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    phase_text = st.empty()

    # Progress callback
    current_phase = {"name": "", "progress": 0}

    def progress_callback(phase: str, progress: float):
        current_phase["name"] = phase
        current_phase["progress"] = progress

    # Run experiment
    async def run_async():
        experiment = RLCFExperiment(
            config=config,
            expert_system=None,
            rlcf_orchestrator=None,
            weight_store=None,
            progress_callback=progress_callback
        )

        # Setup
        status_text.text("Inizializzazione...")
        await experiment.setup()

        # Run
        status_text.text("Esecuzione in corso...")
        results = await experiment.run()

        return results

    # Execute with progress updates
    try:
        # Run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create task
        task = loop.create_task(run_async())

        # Poll progress
        while not task.done():
            phase_name = current_phase["name"] or "Inizializzazione"
            phase_progress = current_phase["progress"]

            phase_text.text(f"Fase: {phase_name}")
            progress_bar.progress(phase_progress)

            loop.run_until_complete(asyncio.sleep(0.1))

        results = task.result()
        loop.close()

        progress_bar.progress(1.0)
        status_text.text("Completato!")

        # Statistical analysis
        analyzer = StatisticalAnalyzer()
        stats = analyzer.analyze(results)

        # Store in session
        st.session_state["results"] = results
        st.session_state["stats"] = stats

        st.success("Simulazione completata!")
        st.balloons()

    except Exception as e:
        st.error(f"Errore: {e}")
        import traceback
        st.code(traceback.format_exc())


def render_hypothesis_card(title: str, result: any, target_desc: str):
    """Render una card per un'ipotesi."""

    passed_class = "passed" if result.passed else "failed"
    passed_icon = "✓" if result.passed else "✗"

    st.markdown(f"""
    <div class="hypothesis-box">
        <h4>{title}</h4>
        <p><strong>Target:</strong> {target_desc}</p>
        <p><strong>Valore:</strong> {result.value:.2%}</p>
        <p class="{passed_class}"><strong>Esito:</strong> {passed_icon} {'Confermata' if result.passed else 'Non confermata'}</p>
    </div>
    """, unsafe_allow_html=True)

    # Details expander
    with st.expander("Dettagli statistici"):
        st.json(result.statistics)
        if result.effect_size:
            st.metric("Effect Size", f"{result.effect_size:.3f}", result.effect_size_interpretation)


def render_authority_chart(results):
    """Render grafico evoluzione authority."""

    if not results.authority_evolution:
        st.warning("Nessun dato di evoluzione authority disponibile")
        return

    # Prepara dati
    data = []
    for entry in results.authority_evolution:
        label = entry["label"]
        for user_id, user_data in entry.get("authorities", {}).items():
            data.append({
                "Iteration": label,
                "User ID": user_id,
                "Profile": user_data.get("profile", "unknown"),
                "Authority": user_data.get("authority", 0),
            })

    if not data:
        st.warning("Nessun dato disponibile")
        return

    df = pd.DataFrame(data)

    # Aggrega per profilo
    df_agg = df.groupby(["Iteration", "Profile"])["Authority"].mean().reset_index()

    # Pivot per chart
    df_pivot = df_agg.pivot(index="Iteration", columns="Profile", values="Authority")

    st.line_chart(df_pivot)


def render_weight_chart(results):
    """Render grafico evoluzione pesi."""

    if not results.weight_evolution:
        st.warning("Nessun dato di evoluzione pesi disponibile")
        return

    # Prepara dati
    data = []
    for entry in results.weight_evolution:
        label = entry["label"]
        weights = entry.get("weights", {})
        if isinstance(weights, dict):
            for k, v in weights.items():
                if isinstance(v, (int, float)):
                    data.append({
                        "Iteration": label,
                        "Weight": k,
                        "Value": v,
                    })

    if not data:
        st.warning("Nessun dato disponibile")
        return

    df = pd.DataFrame(data)

    # Seleziona pesi da visualizzare
    available_weights = df["Weight"].unique().tolist()
    selected = st.multiselect("Seleziona pesi", available_weights, default=available_weights[:5])

    if selected:
        df_filtered = df[df["Weight"].isin(selected)]
        df_pivot = df_filtered.pivot(index="Iteration", columns="Weight", values="Value")
        st.line_chart(df_pivot)


def render_improvement_chart(results):
    """Render grafico confronto improvement."""

    # Estrai metriche
    baseline_data = []
    post_data = []

    for r in results.baseline.results:
        baseline_data.append({
            "Source Grounding": r.objective_metrics.source_grounding,
            "Hallucination Rate": r.objective_metrics.hallucination_rate,
            "Combined Score": r.objective_metrics.combined_score,
        })

    for r in results.post_training.results:
        post_data.append({
            "Source Grounding": r.objective_metrics.source_grounding,
            "Hallucination Rate": r.objective_metrics.hallucination_rate,
            "Combined Score": r.objective_metrics.combined_score,
        })

    if not baseline_data or not post_data:
        st.warning("Dati insufficienti per il confronto")
        return

    df_baseline = pd.DataFrame(baseline_data)
    df_post = pd.DataFrame(post_data)

    # Compare means
    comparison = pd.DataFrame({
        "Metric": ["Source Grounding", "Hallucination Rate", "Combined Score"],
        "Baseline": [df_baseline["Source Grounding"].mean(), df_baseline["Hallucination Rate"].mean(), df_baseline["Combined Score"].mean()],
        "Post-Training": [df_post["Source Grounding"].mean(), df_post["Hallucination Rate"].mean(), df_post["Combined Score"].mean()],
    })

    st.bar_chart(comparison.set_index("Metric"))


def render_user_chart(results):
    """Render grafico distribuzione utenti."""

    if not results.authority_evolution:
        st.warning("Nessun dato disponibile")
        return

    # Prendi ultima iterazione
    final = results.authority_evolution[-1]
    authorities = final.get("authorities", {})

    data = []
    for user_id, user_data in authorities.items():
        data.append({
            "Profile": user_data.get("profile", "unknown"),
            "Authority": user_data.get("authority", 0),
        })

    df = pd.DataFrame(data)
    df_agg = df.groupby("Profile")["Authority"].agg(["mean", "std"]).reset_index()

    st.bar_chart(df_agg.set_index("Profile")["mean"])


def create_metrics_df(results) -> pd.DataFrame:
    """Crea DataFrame con metriche."""
    rows = []

    for r in results.baseline.results:
        rows.append({
            "phase": "baseline",
            "query_id": r.query_id,
            "source_grounding": r.objective_metrics.source_grounding,
            "hallucination_rate": r.objective_metrics.hallucination_rate,
            "combined_score": r.objective_metrics.combined_score,
        })

    for r in results.post_training.results:
        rows.append({
            "phase": "post_training",
            "query_id": r.query_id,
            "source_grounding": r.objective_metrics.source_grounding,
            "hallucination_rate": r.objective_metrics.hallucination_rate,
            "combined_score": r.objective_metrics.combined_score,
        })

    return pd.DataFrame(rows)


def create_markdown_report(results, stats) -> str:
    """Crea report markdown."""
    return f"""# RLCF Simulation Report

**Experiment ID**: {results.experiment_id}
**Generated**: {datetime.now().isoformat()}

## Hypothesis Results

| Hypothesis | Value | Target | Passed |
|------------|-------|--------|--------|
| H1: Persistence | {stats.h1_feedback_persistence.value:.1%} | 100% | {"✓" if stats.h1_feedback_persistence.passed else "✗"} |
| H2: Authority | {stats.h2_authority_convergence.value:+.1%} | >20% | {"✓" if stats.h2_authority_convergence.passed else "✗"} |
| H3: Convergence | {stats.h3_weight_stability.value:.2f} | <0.5 | {"✓" if stats.h3_weight_stability.passed else "✗"} |
| H4: Improvement | {stats.h4_response_improvement.value:+.1%} | >10% | {"✓" if stats.h4_response_improvement.passed else "✗"} |

## Summary

- Total feedbacks: {results.total_feedbacks}
- Duration: {results.total_duration_seconds:.1f}s
- Overall success: {"Yes" if stats.overall_success else "No"}
"""


if __name__ == "__main__":
    main()
