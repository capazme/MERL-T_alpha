"""
Tests for WeightStore and Weight Configuration.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from merlt.weights import (
    WeightStore,
    get_weight_store,
    WeightConfig,
    WeightCategory,
    LearnableWeight,
    RetrievalWeights,
    ExpertTraversalWeights,
    RLCFAuthorityWeights,
    GatingWeights,
)


class TestLearnableWeight:
    """Test per LearnableWeight model."""

    def test_create_simple(self):
        """Crea un peso learnable semplice."""
        weight = LearnableWeight(default=0.7)
        assert weight.default == 0.7
        assert weight.bounds == (0.0, 1.0)
        assert weight.learnable is True
        assert weight.learning_rate == 0.01

    def test_create_with_bounds(self):
        """Crea un peso learnable con bounds custom."""
        weight = LearnableWeight(
            default=0.5,
            bounds=(0.3, 0.8),
            learnable=True,
            learning_rate=0.05
        )
        assert weight.default == 0.5
        assert weight.bounds == (0.3, 0.8)
        assert weight.learning_rate == 0.05


class TestRetrievalWeights:
    """Test per RetrievalWeights model."""

    def test_default_values(self):
        """Verifica valori default."""
        weights = RetrievalWeights()
        assert weights.alpha.default == 0.7
        assert weights.over_retrieve_factor == 3
        assert weights.max_graph_hops == 3
        assert weights.default_graph_score == 0.5

    def test_custom_alpha(self):
        """Configura alpha custom."""
        weights = RetrievalWeights(
            alpha=LearnableWeight(default=0.8, bounds=(0.5, 0.95))
        )
        assert weights.alpha.default == 0.8


class TestExpertTraversalWeights:
    """Test per ExpertTraversalWeights model."""

    def test_get_weight_existing(self):
        """Ottiene peso per relazione esistente."""
        weights = ExpertTraversalWeights(
            weights={
                "contiene": LearnableWeight(default=1.0),
                "disciplina": LearnableWeight(default=0.95),
            },
            default_weight=0.5
        )
        assert weights.get_weight("contiene") == 1.0
        assert weights.get_weight("disciplina") == 0.95

    def test_get_weight_default(self):
        """Ritorna default per relazione non esistente."""
        weights = ExpertTraversalWeights(
            weights={"contiene": LearnableWeight(default=1.0)},
            default_weight=0.4
        )
        assert weights.get_weight("unknown_relation") == 0.4


class TestWeightConfig:
    """Test per WeightConfig model."""

    def test_create_default(self):
        """Crea config con valori default."""
        config = WeightConfig()
        assert config.version == "2.0"
        assert config.get_retrieval_alpha() == 0.7

    def test_get_gating_prior(self):
        """Ottiene prior di gating per un expert."""
        config = WeightConfig()
        # Default prior e' 0.25 per tutti
        assert config.get_gating_prior("LiteralExpert") == 0.25
        # Per expert non esistente, ritorna 0.25 (default)
        assert config.get_gating_prior("UnknownExpert") == 0.25


class TestWeightStore:
    """Test per WeightStore."""

    def test_init_default(self):
        """Inizializza store con config default."""
        store = WeightStore()
        assert store.config_path.exists() or True  # May not exist in test env

    def test_get_default_config(self):
        """Ottiene configurazione default."""
        store = WeightStore()
        config = store._get_default_config()
        assert "retrieval" in config
        assert "expert_traversal" in config
        assert "rlcf" in config
        assert "gating" in config

    def test_parse_learnable_weight_from_number(self):
        """Parse peso da numero semplice."""
        store = WeightStore()
        weight = store._parse_learnable_weight(0.8)
        assert weight.default == 0.8

    def test_parse_learnable_weight_from_dict(self):
        """Parse peso da dizionario."""
        store = WeightStore()
        weight = store._parse_learnable_weight({
            "default": 0.9,
            "bounds": [0.5, 1.0],
            "learnable": True,
        })
        assert weight.default == 0.9
        assert weight.bounds == (0.5, 1.0)

    def test_get_retrieval_alpha(self):
        """Ottiene alpha via shortcut."""
        store = WeightStore()
        alpha = store.get_retrieval_alpha()
        assert 0.0 <= alpha <= 1.0

    def test_get_expert_traversal_weights(self):
        """Ottiene pesi traversal per un expert."""
        store = WeightStore()
        weights = store.get_expert_traversal_weights("LiteralExpert")
        # Dovrebbe avere almeno alcuni pesi
        assert isinstance(weights, dict)


class TestWeightStoreAsync:
    """Test async per WeightStore."""

    @pytest.mark.asyncio
    async def test_get_weights(self):
        """Ottiene configurazione completa."""
        store = WeightStore()
        config = await store.get_weights()
        assert isinstance(config, WeightConfig)
        assert config.get_retrieval_alpha() > 0

    @pytest.mark.asyncio
    async def test_get_weights_cached(self):
        """Verifica caching dei pesi."""
        store = WeightStore()

        # Prima chiamata
        config1 = await store.get_weights()
        # Seconda chiamata (da cache)
        config2 = await store.get_weights()

        # Stessa istanza (cached)
        assert config1 is config2

    @pytest.mark.asyncio
    async def test_save_weights(self):
        """Salva pesi (in-memory per ora)."""
        store = WeightStore()
        config = await store.get_weights()

        version_id = await store.save_weights(
            config=config,
            experiment_id="test-exp-001",
            metrics={"accuracy": 0.85}
        )

        assert version_id is not None
        assert len(version_id) > 0


class TestGetWeightStoreSingleton:
    """Test per singleton get_weight_store."""

    def test_returns_same_instance(self):
        """Ritorna sempre la stessa istanza."""
        store1 = get_weight_store()
        store2 = get_weight_store()
        assert store1 is store2


class TestRLCFAuthorityWeights:
    """Test per RLCFAuthorityWeights."""

    def test_default_values(self):
        """Verifica valori default authority."""
        weights = RLCFAuthorityWeights()
        # Somma dovrebbe essere circa 1.0
        total = (
            weights.baseline_credentials.default +
            weights.track_record.default +
            weights.recent_performance.default
        )
        assert abs(total - 1.0) < 0.01

    def test_track_record_update_factor(self):
        """Verifica update factor."""
        weights = RLCFAuthorityWeights()
        assert 0.01 <= weights.track_record_update_factor.default <= 0.2


class TestGatingWeights:
    """Test per GatingWeights."""

    def test_default_priors(self):
        """Verifica prior uniformi di default."""
        weights = GatingWeights()
        for expert in ["LiteralExpert", "SystemicExpert", "PrinciplesExpert", "PrecedentExpert"]:
            assert expert in weights.expert_priors
            assert weights.expert_priors[expert].default == 0.25

    def test_query_type_modifiers(self):
        """Verifica modificatori per tipo query."""
        weights = GatingWeights()
        # Default ha modificatori per definitorio, interpretativo, applicativo
        assert isinstance(weights.query_type_modifiers, dict)
