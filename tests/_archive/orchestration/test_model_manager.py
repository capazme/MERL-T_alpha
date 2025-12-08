"""
Unit Tests for Model Manager
=============================

Tests the hot-swappable ML model management system.
Supports model registration, activation, comparison, and A/B testing.

Test coverage:
- Model registration and metadata storage
- Model activation and switching
- Metrics comparison between models
- Auto-selection by metric
- Model status tracking
- Singleton pattern
- Statistics and reporting
"""

import pytest
from datetime import datetime
from merlt.orchestration.model_manager import (
    ModelManager,
    ModelMetrics,
    TrainedModelInfo,
    ModelStatus,
    get_model_manager
)


# ===================================
# Fixtures
# ===================================

@pytest.fixture
def model_manager():
    """Create ModelManager instance."""
    # Note: This will be a singleton, so reset it for testing
    manager = ModelManager()
    # Clear any previous state
    manager._loaded_models = {}
    manager._active_model_version = None
    manager._active_pipeline = None
    return manager


@pytest.fixture
def sample_metrics():
    """Create sample evaluation metrics."""
    return ModelMetrics(
        f1_score=0.92,
        precision=0.94,
        recall=0.90,
        accuracy=0.91,
        loss=0.08,
        dataset_size=1000,
        evaluation_date=datetime.now(),
        notes="Sample evaluation"
    )


@pytest.fixture
def model_v1(sample_metrics):
    """Create model v1 info."""
    return TrainedModelInfo(
        version="1.0",
        model_path="/models/v1.0",
        created_at=datetime.now(),
        metrics=sample_metrics,
        status=ModelStatus.INACTIVE
    )


@pytest.fixture
def model_v2():
    """Create model v2 info with better metrics."""
    metrics = ModelMetrics(
        f1_score=0.95,
        precision=0.96,
        recall=0.94,
        accuracy=0.95,
        loss=0.05,
        dataset_size=1000,
        evaluation_date=datetime.now(),
        notes="Improved model"
    )

    return TrainedModelInfo(
        version="2.0",
        model_path="/models/v2.0",
        created_at=datetime.now(),
        metrics=metrics,
        status=ModelStatus.INACTIVE
    )


# ===================================
# Test Cases: Model Registration
# ===================================

def test_register_model_basic(model_manager, sample_metrics):
    """Test basic model registration."""
    info = model_manager.register_model("1.0", "/path/to/model/1.0", sample_metrics)

    assert info.version == "1.0", "Should register version"
    assert info.model_path == "/path/to/model/1.0", "Should store model path"
    assert info.status == ModelStatus.INACTIVE, "Should start as inactive"
    assert info.metrics == sample_metrics, "Should store metrics"


def test_register_multiple_models(model_manager, sample_metrics):
    """Test registering multiple models."""
    m1 = model_manager.register_model("1.0", "/path/v1.0", sample_metrics)
    m2 = model_manager.register_model("2.0", "/path/v2.0", sample_metrics)
    m3 = model_manager.register_model("3.0", "/path/v3.0", sample_metrics)

    assert len(model_manager._loaded_models) == 3, "Should register all models"
    assert model_manager._loaded_models["1.0"] == m1
    assert model_manager._loaded_models["2.0"] == m2
    assert model_manager._loaded_models["3.0"] == m3


def test_register_duplicate_version_overwrites(model_manager, sample_metrics):
    """Test that registering duplicate version overwrites."""
    metrics1 = ModelMetrics(
        f1_score=0.90, precision=0.92, recall=0.88, accuracy=0.89,
        loss=0.10, dataset_size=1000, evaluation_date=datetime.now()
    )

    metrics2 = ModelMetrics(
        f1_score=0.95, precision=0.97, recall=0.93, accuracy=0.94,
        loss=0.05, dataset_size=1000, evaluation_date=datetime.now()
    )

    model_manager.register_model("1.0", "/path/v1.0", metrics1)
    model_manager.register_model("1.0", "/path/v1.0-updated", metrics2)

    assert len(model_manager._loaded_models) == 1, "Should have one model"
    assert model_manager._loaded_models["1.0"].metrics.f1_score == 0.95, "Should overwrite"


# ===================================
# Test Cases: Model Activation
# ===================================

def test_activate_model_success(model_manager, model_v1):
    """Test successful model activation."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)

    result = model_manager.activate_model("1.0")

    assert result["success"], "Should activate successfully"
    assert model_manager._active_model_version == "1.0", "Should set as active"
    assert model_manager._loaded_models["1.0"].status == ModelStatus.ACTIVE


def test_activate_nonexistent_model(model_manager):
    """Test activating non-existent model."""
    result = model_manager.activate_model("nonexistent")

    assert not result["success"], "Should fail for non-existent model"
    assert "error" in result, "Should include error message"
    assert "not found" in result["error"].lower(), "Should mention not found"


def test_activate_deactivates_previous(model_manager, model_v1, model_v2):
    """Test that activating new model deactivates previous."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    # Activate first model
    model_manager.activate_model("1.0")
    assert model_manager._loaded_models["1.0"].status == ModelStatus.ACTIVE

    # Activate second model
    model_manager.activate_model("2.0")
    assert model_manager._loaded_models["2.0"].status == ModelStatus.ACTIVE
    assert model_manager._loaded_models["1.0"].status == ModelStatus.INACTIVE, "Should deactivate previous"


# ===================================
# Test Cases: Get Active Model
# ===================================

def test_get_active_model_when_active(model_manager, model_v1):
    """Test getting active model when one is set."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.activate_model("1.0")

    active = model_manager.get_active_model()

    assert active is not None, "Should return active model"
    assert active.version == "1.0", "Should return correct model"


def test_get_active_model_when_none_active(model_manager):
    """Test getting active model when none is set."""
    active = model_manager.get_active_model()

    assert active is None, "Should return None when no model active"


# ===================================
# Test Cases: List Models
# ===================================

def test_list_models_empty(model_manager):
    """Test listing models when none registered."""
    models = model_manager.list_models()

    assert isinstance(models, list), "Should return list"
    assert len(models) == 0, "Should be empty"


def test_list_models_with_models(model_manager, model_v1, model_v2):
    """Test listing registered models."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    models = model_manager.list_models()

    assert len(models) == 2, "Should list all models"

    versions = [m["version"] for m in models]
    assert "1.0" in versions, "Should include v1.0"
    assert "2.0" in versions, "Should include v2.0"


def test_list_models_includes_metrics(model_manager, model_v1):
    """Test that listed models include metrics."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)

    models = model_manager.list_models()
    model = models[0]

    assert "metrics" in model, "Should include metrics"
    assert "f1_score" in model["metrics"], "Should include f1_score"
    assert model["metrics"]["f1_score"] == 0.92, "Should have correct metric"


def test_list_models_includes_active_flag(model_manager, model_v1, model_v2):
    """Test that list includes is_active flag."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    model_manager.activate_model("1.0")

    models = model_manager.list_models()

    v1_model = next((m for m in models if m["version"] == "1.0"), None)
    v2_model = next((m for m in models if m["version"] == "2.0"), None)

    assert v1_model["is_active"], "v1.0 should be marked active"
    assert not v2_model["is_active"], "v2.0 should be marked inactive"


# ===================================
# Test Cases: Model Comparison
# ===================================

def test_compare_models_success(model_manager, model_v1, model_v2):
    """Test comparing two models."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    result = model_manager.compare_models("1.0", "2.0")

    assert "model_1" in result, "Should have model_1 metrics"
    assert "model_2" in result, "Should have model_2 metrics"
    assert "delta" in result, "Should include delta"
    assert "winner" in result, "Should declare winner"


def test_compare_models_correctly_identifies_winner(model_manager, model_v1, model_v2):
    """Test that comparison correctly identifies best model."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)  # F1: 0.92
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)  # F1: 0.95

    result = model_manager.compare_models("1.0", "2.0")

    assert result["winner"] == "2.0", "Should identify v2.0 as winner (higher F1)"


def test_compare_models_delta_calculation(model_manager, model_v1, model_v2):
    """Test that delta is correctly calculated."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)  # F1: 0.92
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)  # F1: 0.95

    result = model_manager.compare_models("1.0", "2.0")

    delta = result["delta"]
    assert abs(delta["f1_score"] - 0.03) < 0.001, "F1 delta should be ~0.03"


def test_compare_nonexistent_model(model_manager, model_v1):
    """Test comparing with non-existent model."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)

    result = model_manager.compare_models("1.0", "nonexistent")

    assert "error" in result, "Should include error"


def test_compare_models_without_metrics(model_manager):
    """Test comparing models without metrics."""
    # Register models without metrics
    model_manager.register_model("1.0", "/path/v1.0", metrics=None)
    model_manager.register_model("2.0", "/path/v2.0", metrics=None)

    result = model_manager.compare_models("1.0", "2.0")

    assert "error" in result, "Should error when metrics missing"


# ===================================
# Test Cases: Auto-Select Best Model
# ===================================

def test_auto_select_by_f1_score(model_manager, model_v1, model_v2):
    """Test auto-selection by F1 score."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    result = model_manager.auto_select_best_model(metric="f1_score")

    assert result["success"], "Should auto-select successfully"
    assert model_manager._active_model_version == "2.0", "Should select model with highest F1"


def test_auto_select_by_precision(model_manager, model_v1, model_v2):
    """Test auto-selection by precision."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    result = model_manager.auto_select_best_model(metric="precision")

    assert result["success"], "Should auto-select by precision"
    assert model_manager._active_model_version == "2.0", "Should select model with highest precision"


def test_auto_select_no_models(model_manager):
    """Test auto-select when no models available."""
    result = model_manager.auto_select_best_model()

    assert not result["success"], "Should fail when no models available"
    assert "error" in result, "Should include error message"


def test_auto_select_no_metrics(model_manager):
    """Test auto-select when models have no metrics."""
    model_manager.register_model("1.0", "/path/v1.0", metrics=None)
    model_manager.register_model("2.0", "/path/v2.0", metrics=None)

    result = model_manager.auto_select_best_model()

    assert not result["success"], "Should fail when no metrics available"


# ===================================
# Test Cases: Model Status Management
# ===================================

def test_update_model_status(model_manager, model_v1):
    """Test updating model status."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)

    model_manager.update_model_status("1.0", ModelStatus.TESTING, notes="Testing model")

    assert model_manager._loaded_models["1.0"].status == ModelStatus.TESTING, "Should update status"
    assert model_manager._loaded_models["1.0"].notes == "Testing model", "Should save notes"


# ===================================
# Test Cases: Statistics & Reporting
# ===================================

def test_get_model_stats(model_manager, model_v1, model_v2):
    """Test getting model statistics."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    stats = model_manager.get_model_stats()

    assert stats["total_models"] == 2, "Should count total models"
    assert "models_by_status" in stats, "Should include status distribution"


def test_get_model_stats_no_active(model_manager, model_v1):
    """Test stats when no model is active."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)

    stats = model_manager.get_model_stats()

    assert stats["active_model"] is None, "Should show no active model"


def test_get_model_stats_with_active(model_manager, model_v1):
    """Test stats with active model."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.activate_model("1.0")

    stats = model_manager.get_model_stats()

    assert stats["active_model"] == "1.0", "Should show active model"


# ===================================
# Test Cases: Singleton Pattern
# ===================================

def test_singleton_pattern():
    """Test that ModelManager is a singleton."""
    m1 = ModelManager()
    m2 = ModelManager()

    assert m1 is m2, "Should return same instance (singleton)"


def test_get_model_manager_singleton():
    """Test get_model_manager returns singleton."""
    m1 = get_model_manager()
    m2 = get_model_manager()

    assert m1 is m2, "Should return same instance"
    assert isinstance(m1, ModelManager), "Should return ModelManager"


# ===================================
# Test Cases: String Representation
# ===================================

def test_repr_method(model_manager, model_v1, model_v2):
    """Test __repr__ method."""
    model_manager.register_model(model_v1.version, model_v1.model_path, model_v1.metrics)
    model_manager.register_model(model_v2.version, model_v2.model_path, model_v2.metrics)

    repr_str = repr(model_manager)

    assert "ModelManager" in repr_str, "Should include class name"
    assert "total_models" in repr_str, "Should include total_models"


# ===================================
# Test Cases: Edge Cases
# ===================================

def test_model_with_very_long_path(model_manager, sample_metrics):
    """Test model with very long file path."""
    long_path = "/very/deep/directory/structure/" + ("subdir/" * 20) + "model.pt"

    info = model_manager.register_model("1.0", long_path, sample_metrics)

    assert info.model_path == long_path, "Should handle long paths"


def test_model_with_special_version_string(model_manager, sample_metrics):
    """Test model with special version string."""
    special_versions = ["1.0-rc1", "2.0-alpha", "3.0.1", "v1.0"]

    for version in special_versions:
        model_manager.register_model(version, f"/path/{version}", sample_metrics)

    all_models = model_manager.list_models()
    versions = [m["version"] for m in all_models]

    for version in special_versions:
        assert version in versions, f"Should handle version {version}"
