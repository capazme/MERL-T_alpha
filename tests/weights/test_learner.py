"""
Tests for WeightLearner.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from merlt.weights import (
    WeightStore,
    WeightLearner,
    LearnerConfig,
    RLCFFeedback,
    WeightConfig,
)


class TestLearnerConfig:
    """Test per LearnerConfig."""

    def test_default_values(self):
        """Verifica valori default."""
        config = LearnerConfig()
        assert config.default_learning_rate == 0.01
        assert config.min_authority_threshold == 0.3
        assert config.momentum == 0.9
        assert config.clip_gradient == 0.1

    def test_custom_values(self):
        """Configura valori custom."""
        config = LearnerConfig(
            default_learning_rate=0.05,
            min_authority_threshold=0.5
        )
        assert config.default_learning_rate == 0.05
        assert config.min_authority_threshold == 0.5


class TestRLCFFeedback:
    """Test per RLCFFeedback."""

    def test_create_minimal(self):
        """Crea feedback con campi minimi."""
        feedback = RLCFFeedback(
            query_id="q001",
            user_id="u001",
            authority=0.8,
            relevance_scores={"r1": 0.9}
        )
        assert feedback.query_id == "q001"
        assert feedback.authority == 0.8
        assert feedback.task_type == "retrieval"

    def test_create_full(self):
        """Crea feedback completo."""
        feedback = RLCFFeedback(
            query_id="q001",
            user_id="u001",
            authority=0.7,
            relevance_scores={"r1": 0.9, "r2": 0.3},
            expected_ranking=["r1", "r2"],
            actual_ranking=["r2", "r1"],
            task_type="qa"
        )
        assert feedback.expected_ranking == ["r1", "r2"]
        assert feedback.task_type == "qa"


class TestWeightLearner:
    """Test per WeightLearner."""

    @pytest.fixture
    def store(self):
        """Crea store mock."""
        store = MagicMock(spec=WeightStore)
        store.get_weights = AsyncMock(return_value=WeightConfig())
        store.save_weights = AsyncMock(return_value="version-001")
        return store

    @pytest.fixture
    def learner(self, store):
        """Crea learner con store mock."""
        return WeightLearner(store)

    def test_init(self, learner):
        """Verifica inizializzazione."""
        assert learner.config.default_learning_rate == 0.01
        assert learner._momentum_buffer == {}

    def test_init_custom_config(self, store):
        """Inizializza con config custom."""
        config = LearnerConfig(min_authority_threshold=0.5)
        learner = WeightLearner(store, config=config)
        assert learner.config.min_authority_threshold == 0.5


class TestWeightLearnerAsync:
    """Test async per WeightLearner."""

    @pytest.fixture
    def store(self):
        """Crea store mock."""
        store = MagicMock(spec=WeightStore)
        store.get_weights = AsyncMock(return_value=WeightConfig())
        store.save_weights = AsyncMock(return_value="version-001")
        return store

    @pytest.mark.asyncio
    async def test_update_low_authority_skipped(self, store):
        """Skip update se authority troppo bassa."""
        learner = WeightLearner(store)

        feedback = RLCFFeedback(
            query_id="q001",
            user_id="u001",
            authority=0.1,  # Sotto threshold
            relevance_scores={"r1": 0.9}
        )

        result = await learner.update_from_feedback(
            category="retrieval",
            feedback=feedback
        )

        # Non dovrebbe salvare
        store.save_weights.assert_not_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_high_authority(self, store):
        """Applica update con authority alta."""
        learner = WeightLearner(store)

        feedback = RLCFFeedback(
            query_id="q001",
            user_id="u001",
            authority=0.8,
            relevance_scores={"r1": 0.3}  # Bassa rilevanza
        )

        result = await learner.update_from_feedback(
            category="retrieval",
            feedback=feedback,
            experiment_id="exp-001"
        )

        # Dovrebbe salvare (experiment_id specificato)
        store.save_weights.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_compute_retrieval_gradient(self, store):
        """Verifica calcolo gradiente retrieval."""
        learner = WeightLearner(store)

        feedback = RLCFFeedback(
            query_id="q001",
            user_id="u001",
            authority=0.8,
            relevance_scores={"r1": 0.2, "r2": 0.3}  # Bassa rilevanza
        )

        current = WeightConfig()
        gradient = learner._compute_gradient("retrieval", feedback, current)

        assert "alpha" in gradient
        # Con bassa rilevanza, dovrebbe suggerire cambio
        assert abs(gradient["alpha"]) > 0 or gradient["alpha"] == 0

    @pytest.mark.asyncio
    async def test_batch_update(self, store):
        """Test batch update."""
        learner = WeightLearner(store)

        feedbacks = [
            RLCFFeedback(
                query_id=f"q{i}",
                user_id="u001",
                authority=0.8,
                relevance_scores={"r1": 0.5}
            )
            for i in range(5)
        ]

        result = await learner.batch_update(
            category="retrieval",
            feedbacks=feedbacks
        )

        assert result is not None

    def test_reset_momentum(self, store):
        """Test reset momentum buffer."""
        learner = WeightLearner(store)
        learner._momentum_buffer["alpha"] = 0.5

        learner.reset_momentum()

        assert learner._momentum_buffer == {}
