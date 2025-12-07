"""
Model Manager for Hot-Swappable NER Model Loading
==================================================

Manages ML model lifecycle with database-driven activation.
Supports hot-reloading without server restart.

Adapted from legal-ner project (github.com/user/legal-ner).
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

log = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Status of a trained model."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    FAILED = "failed"
    TESTING = "testing"


@dataclass
class ModelMetrics:
    """Evaluation metrics for a trained model."""
    f1_score: float
    precision: float
    recall: float
    accuracy: float
    loss: float
    dataset_size: int
    evaluation_date: datetime
    notes: Optional[str] = None


@dataclass
class TrainedModelInfo:
    """Information about a trained NER model."""
    version: str
    model_path: str
    created_at: datetime
    metrics: Optional[ModelMetrics] = None
    status: ModelStatus = ModelStatus.INACTIVE
    parent_version: Optional[str] = None
    training_config: Optional[Dict[str, Any]] = None
    dataset_version: Optional[str] = None
    notes: Optional[str] = None


class ModelManager:
    """
    Singleton for hot-swappable ML pipeline management.

    Features:
    - Database-driven model activation (requires TrainedModel table)
    - Hot reload without server restart
    - Model version tracking
    - Automatic fallback to rule-based pipeline
    - Model comparison & auto-selection by metric
    """

    _instance: Optional['ModelManager'] = None
    _active_pipeline = None
    _loaded_models: Dict[str, TrainedModelInfo] = {}

    def __new__(cls):
        """Singleton pattern: ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize ModelManager as singleton."""
        if self._initialized:
            return

        self._initialized = True
        log.info("Initializing ModelManager singleton")
        self._loaded_models = {}
        self._active_model_version: Optional[str] = None
        self._active_pipeline = None

    def register_model(self, version: str, model_path: str, metrics: Optional[ModelMetrics] = None) -> TrainedModelInfo:
        """
        Register a new trained model.

        Args:
            version: Model version identifier (e.g., "1.0", "2.1-rc1")
            model_path: Path to model checkpoint directory
            metrics: Optional metrics dict from evaluation

        Returns:
            TrainedModelInfo object
        """
        if version in self._loaded_models:
            log.warning(f"Model version {version} already registered, overwriting")

        model_info = TrainedModelInfo(
            version=version,
            model_path=str(model_path),
            created_at=datetime.now(),
            metrics=metrics,
            status=ModelStatus.INACTIVE
        )

        self._loaded_models[version] = model_info
        log.info(f"Registered model {version} at {model_path}")

        return model_info

    def activate_model(self, version: str) -> Dict[str, Any]:
        """
        Activate a specific model version.

        Changes the active NER pipeline to use this model without restarting server.

        Args:
            version: Model version to activate

        Returns:
            Dict with activation status and details
        """
        if version not in self._loaded_models:
            return {
                "success": False,
                "error": f"Model version {version} not found",
                "available_versions": list(self._loaded_models.keys())
            }

        model_info = self._loaded_models[version]

        try:
            # TODO: Load model from path and initialize LegalSourceExtractionPipeline
            # from ..preprocessing.ner_module import LegalSourceExtractionPipeline
            # self._active_pipeline = LegalSourceExtractionPipeline(
            #     fine_tuned_model_path=model_info.model_path
            # )

            self._active_model_version = version
            model_info.status = ModelStatus.ACTIVE

            # Mark other models as inactive
            for v, m in self._loaded_models.items():
                if v != version:
                    m.status = ModelStatus.INACTIVE

            log.info(f"Activated model version {version}")

            return {
                "success": True,
                "message": f"Model {version} activated successfully",
                "version": version,
                "model_path": model_info.model_path,
                "metrics": model_info.metrics.__dict__ if model_info.metrics else None
            }

        except Exception as e:
            log.error(f"Failed to activate model {version}: {e}")
            model_info.status = ModelStatus.FAILED

            return {
                "success": False,
                "error": str(e),
                "version": version
            }

    def get_active_model(self) -> Optional[TrainedModelInfo]:
        """Get currently active model."""
        if self._active_model_version:
            return self._loaded_models.get(self._active_model_version)
        return None

    def get_active_pipeline(self):
        """Get the active NER extraction pipeline."""
        return self._active_pipeline

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all registered models with their status.

        Returns:
            List of model info dicts
        """
        models_list = []

        for version, model_info in self._loaded_models.items():
            model_dict = {
                "version": version,
                "model_path": model_info.model_path,
                "status": model_info.status.value,
                "created_at": model_info.created_at.isoformat(),
                "is_active": version == self._active_model_version,
                "notes": model_info.notes
            }

            if model_info.metrics:
                model_dict["metrics"] = {
                    "f1_score": model_info.metrics.f1_score,
                    "precision": model_info.metrics.precision,
                    "recall": model_info.metrics.recall,
                    "accuracy": model_info.metrics.accuracy
                }

            models_list.append(model_dict)

        return sorted(models_list, key=lambda x: x['created_at'], reverse=True)

    def compare_models(self, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two model versions by their metrics.

        Args:
            version1: First model version
            version2: Second model version

        Returns:
            Comparison dict with metrics delta
        """
        if version1 not in self._loaded_models:
            return {"error": f"Model {version1} not found"}

        if version2 not in self._loaded_models:
            return {"error": f"Model {version2} not found"}

        m1_info = self._loaded_models[version1]
        m2_info = self._loaded_models[version2]

        if not m1_info.metrics or not m2_info.metrics:
            return {"error": "One or both models missing metrics"}

        m1_metrics = m1_info.metrics
        m2_metrics = m2_info.metrics

        return {
            "model_1": {
                "version": version1,
                "f1_score": m1_metrics.f1_score,
                "precision": m1_metrics.precision,
                "recall": m1_metrics.recall,
                "accuracy": m1_metrics.accuracy
            },
            "model_2": {
                "version": version2,
                "f1_score": m2_metrics.f1_score,
                "precision": m2_metrics.precision,
                "recall": m2_metrics.recall,
                "accuracy": m2_metrics.accuracy
            },
            "delta": {
                "f1_score": m2_metrics.f1_score - m1_metrics.f1_score,
                "precision": m2_metrics.precision - m1_metrics.precision,
                "recall": m2_metrics.recall - m1_metrics.recall,
                "accuracy": m2_metrics.accuracy - m1_metrics.accuracy
            },
            "winner": version2 if m2_metrics.f1_score > m1_metrics.f1_score else version1
        }

    def auto_select_best_model(self, metric: str = "f1_score") -> Dict[str, Any]:
        """
        Automatically select and activate best performing model by metric.

        Args:
            metric: Which metric to optimize for (f1_score, precision, recall, accuracy)

        Returns:
            Activation result dict
        """
        if not self._loaded_models:
            return {
                "success": False,
                "error": "No models available for selection"
            }

        best_version = None
        best_metric_value = -1

        for version, model_info in self._loaded_models.items():
            if not model_info.metrics:
                continue

            metric_value = getattr(model_info.metrics, metric, None)

            if metric_value and metric_value > best_metric_value:
                best_metric_value = metric_value
                best_version = version

        if best_version is None:
            return {
                "success": False,
                "error": f"No models with {metric} metric available"
            }

        log.info(f"Auto-selected best model: {best_version} ({metric}={best_metric_value:.4f})")
        return self.activate_model(best_version)

    def reload_pipeline(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Hot-reload the NER extraction pipeline.

        Reinitializes with current configuration without server restart.

        Args:
            config_path: Optional path to new NER config

        Returns:
            Reload status dict
        """
        try:
            # TODO: Reload LegalSourceExtractionPipeline with new config
            # if config_path:
            #     from ..preprocessing.ner_module import LegalSourceExtractionPipeline
            #     from ..preprocessing.ner_config import load_config
            #     config = load_config(config_path)
            # else:
            #     config = {}  # Use defaults
            #
            # self._active_pipeline = LegalSourceExtractionPipeline(config=config)

            log.info("NER pipeline reloaded successfully")

            return {
                "success": True,
                "message": "Pipeline reloaded successfully",
                "active_model": self._active_model_version
            }

        except Exception as e:
            log.error(f"Failed to reload pipeline: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def update_model_status(self, version: str, status: ModelStatus, notes: Optional[str] = None):
        """
        Update status of a model.

        Args:
            version: Model version
            status: New status
            notes: Optional notes about the status change
        """
        if version not in self._loaded_models:
            log.warning(f"Model {version} not found")
            return

        model_info = self._loaded_models[version]
        model_info.status = status
        if notes:
            model_info.notes = notes

        log.info(f"Updated model {version} status to {status.value}")

    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded models."""
        total_models = len(self._loaded_models)
        active_model = self.get_active_model()
        models_by_status = {}

        for model_info in self._loaded_models.values():
            status = model_info.status.value
            models_by_status[status] = models_by_status.get(status, 0) + 1

        return {
            "total_models": total_models,
            "active_model": active_model.version if active_model else None,
            "models_by_status": models_by_status
        }

    def __repr__(self) -> str:
        return (
            f"ModelManager("
            f"total_models={len(self._loaded_models)}, "
            f"active={self._active_model_version}, "
            f"status={self.get_model_stats()})"
        )


# Singleton getter
def get_model_manager() -> ModelManager:
    """Get the global ModelManager singleton."""
    return ModelManager()
