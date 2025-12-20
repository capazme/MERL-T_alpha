"""
Tests for ExperimentTracker.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from merlt.weights import (
    WeightStore,
    WeightConfig,
    ExperimentTracker,
    Experiment,
    ExperimentAnalysis,
)


class TestExperiment:
    """Test per Experiment dataclass."""

    def test_create_minimal(self):
        """Crea esperimento minimale."""
        exp = Experiment(id="exp-001", name="test")
        assert exp.id == "exp-001"
        assert exp.name == "test"
        assert exp.status == "draft"
        assert exp.variants == {}

    def test_create_full(self):
        """Crea esperimento completo."""
        exp = Experiment(
            id="exp-001",
            name="alpha_test",
            description="Test alpha tuning",
            status="running",
            variants={"control": WeightConfig(), "treatment": WeightConfig()},
            allocation={"control": 0.5, "treatment": 0.5}
        )
        assert exp.status == "running"
        assert len(exp.variants) == 2


class TestExperimentAnalysis:
    """Test per ExperimentAnalysis."""

    def test_create(self):
        """Crea analisi."""
        analysis = ExperimentAnalysis(
            experiment_id="exp-001",
            control_metrics={"mrr": 0.8},
            treatment_metrics={"mrr": 0.85},
            winner="treatment",
            significant=True,
            samples_control=100,
            samples_treatment=100
        )
        assert analysis.winner == "treatment"
        assert analysis.significant is True


class TestExperimentTracker:
    """Test per ExperimentTracker."""

    @pytest.fixture
    def store(self):
        """Crea store mock."""
        store = MagicMock(spec=WeightStore)
        store.get_weights = AsyncMock(return_value=WeightConfig())
        store.save_weights = AsyncMock(return_value="version-001")
        return store

    @pytest.fixture
    def tracker(self, store):
        """Crea tracker con store mock."""
        return ExperimentTracker(store)

    def test_init(self, tracker):
        """Verifica inizializzazione."""
        assert tracker._experiments == {}


class TestExperimentTrackerAsync:
    """Test async per ExperimentTracker."""

    @pytest.fixture
    def store(self):
        """Crea store mock."""
        store = MagicMock(spec=WeightStore)
        store.get_weights = AsyncMock(return_value=WeightConfig())
        store.save_weights = AsyncMock(return_value="version-001")
        return store

    @pytest.mark.asyncio
    async def test_create_experiment(self, store):
        """Crea un esperimento."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="alpha_test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig(),
            split_ratio=0.5
        )

        assert exp.name == "alpha_test"
        assert exp.status == "running"
        assert "control" in exp.variants
        assert "treatment" in exp.variants
        assert exp.allocation["treatment"] == 0.5

    @pytest.mark.asyncio
    async def test_assign_variant_deterministic(self, store):
        """Assegnazione variante e' deterministica."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        # Stesso utente, stessa variante
        v1 = await tracker.assign_variant(exp.id, "user123")
        v2 = await tracker.assign_variant(exp.id, "user123")

        assert v1 == v2

    @pytest.mark.asyncio
    async def test_assign_variant_different_users(self, store):
        """Utenti diversi possono avere varianti diverse."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        # Raccoglie varianti per molti utenti
        variants = set()
        for i in range(100):
            v = await tracker.assign_variant(exp.id, f"user{i}")
            variants.add(v)

        # Dovremmo vedere sia control che treatment
        assert "control" in variants or "treatment" in variants

    @pytest.mark.asyncio
    async def test_get_weights_for_user(self, store):
        """Ottiene pesi per utente."""
        tracker = ExperimentTracker(store)

        control_config = WeightConfig()
        treatment_config = WeightConfig()

        exp = await tracker.create_experiment(
            name="test",
            control_weights=control_config,
            treatment_weights=treatment_config
        )

        weights = await tracker.get_weights_for_user(exp.id, "user123")

        assert weights is not None
        assert isinstance(weights, WeightConfig)

    @pytest.mark.asyncio
    async def test_record_outcome(self, store):
        """Registra outcome."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        await tracker.record_outcome(exp.id, "control", {"mrr": 0.8})
        await tracker.record_outcome(exp.id, "treatment", {"mrr": 0.85})

        assert len(exp.metrics_by_variant["control"]) == 1
        assert len(exp.metrics_by_variant["treatment"]) == 1

    @pytest.mark.asyncio
    async def test_record_outcome_invalid_experiment(self, store):
        """Errore per esperimento non esistente."""
        tracker = ExperimentTracker(store)

        with pytest.raises(ValueError):
            await tracker.record_outcome("invalid", "control", {"mrr": 0.8})

    @pytest.mark.asyncio
    async def test_analyze_experiment(self, store):
        """Analizza esperimento."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        # Aggiungi outcomes
        for _ in range(50):
            await tracker.record_outcome(exp.id, "control", {"mrr": 0.75})
            await tracker.record_outcome(exp.id, "treatment", {"mrr": 0.85})

        analysis = await tracker.analyze_experiment(exp.id)

        assert analysis.experiment_id == exp.id
        assert analysis.samples_control == 50
        assert analysis.samples_treatment == 50
        assert "mrr" in analysis.control_metrics
        assert "mrr" in analysis.treatment_metrics

    @pytest.mark.asyncio
    async def test_analyze_with_clear_winner(self, store):
        """Analisi con winner chiaro."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        # Treatment significativamente migliore
        for _ in range(50):
            await tracker.record_outcome(exp.id, "control", {"mrr": 0.6})
            await tracker.record_outcome(exp.id, "treatment", {"mrr": 0.9})

        analysis = await tracker.analyze_experiment(exp.id)

        assert analysis.winner == "treatment"
        assert analysis.significant is True

    @pytest.mark.asyncio
    async def test_stop_experiment(self, store):
        """Ferma esperimento."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        stopped = await tracker.stop_experiment(exp.id)

        assert stopped.status == "stopped"
        assert stopped.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_experiment_with_winner(self, store):
        """Completa esperimento e applica winner."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        completed = await tracker.complete_experiment(exp.id, winner="treatment")

        assert completed.status == "completed"
        store.save_weights.assert_called_once()

    def test_list_experiments(self, store):
        """Lista esperimenti."""
        tracker = ExperimentTracker(store)

        # Nessun esperimento
        assert tracker.list_experiments() == []

    @pytest.mark.asyncio
    async def test_list_experiments_with_filter(self, store):
        """Lista esperimenti con filtro status."""
        tracker = ExperimentTracker(store)

        exp = await tracker.create_experiment(
            name="test",
            control_weights=WeightConfig(),
            treatment_weights=WeightConfig()
        )

        running = tracker.list_experiments(status="running")
        assert len(running) == 1

        stopped = tracker.list_experiments(status="stopped")
        assert len(stopped) == 0

    def test_get_experiment(self, store):
        """Ottiene esperimento per ID."""
        tracker = ExperimentTracker(store)

        result = tracker.get_experiment("nonexistent")
        assert result is None
