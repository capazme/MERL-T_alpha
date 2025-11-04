"""
Database Models Extension for NER Module
=========================================

Extends the MERL-T database schema with models for training and evaluation
of fine-tuned NER models. These models support the Phase 2 Preprocessing Layer.

Includes:
- TrainedModel: Metadata about trained NER models
- EvaluationRun: Results from model evaluation
- AnnotationTask: Human annotation tasks for training data
- NERPrediction: Predictions from NER pipeline
"""

import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from .database import Base


class ModelStatus(str, enum.Enum):
    """Status of a trained NER model."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    FAILED = "failed"
    TESTING = "testing"


class AnnotationStatus(str, enum.Enum):
    """Status of an annotation task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    MERGED = "merged"


class EvaluationMetric(str, enum.Enum):
    """Metrics tracked during model evaluation."""
    F1_SCORE = "f1_score"
    PRECISION = "precision"
    RECALL = "recall"
    ACCURACY = "accuracy"
    LOSS = "loss"


class TrainedModel(Base):
    """
    Metadata about trained NER models.

    Tracks fine-tuned model versions, their performance metrics,
    and activation status for A/B testing and deployment.
    """
    __tablename__ = "trained_models"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, nullable=False, index=True)  # e.g., "1.0", "2.1-rc1"
    model_path = Column(String, nullable=False)  # Path to model checkpoint
    model_type = Column(String, default="ner")  # Type of model (ner, classifier, etc.)
    status = Column(String, default=ModelStatus.INACTIVE, index=True)

    # Training metadata
    parent_version = Column(String, nullable=True)  # Previous model version
    training_config = Column(JSON, nullable=True)  # Training hyperparameters
    dataset_version = Column(String, nullable=True)  # Which dataset was used
    dataset_size = Column(Integer, nullable=True)  # Number of training samples

    # Activation & deployment
    is_active = Column(Boolean, default=False, index=True)
    activated_at = Column(DateTime, nullable=True)  # When this model was activated
    deactivated_at = Column(DateTime, nullable=True)  # When this model was deactivated

    # Metrics (denormalized for quick access)
    f1_score = Column(Float, nullable=True, index=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    loss = Column(Float, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    evaluation_runs = relationship("EvaluationRun", back_populates="model")
    predictions = relationship("NERPrediction", back_populates="model")

    def __repr__(self) -> str:
        return f"TrainedModel(version={self.version}, status={self.status}, f1={self.f1_score:.4f})"


class EvaluationRun(Base):
    """
    Results from a model evaluation.

    Tracks comprehensive metrics from evaluating a model on a test dataset,
    including per-entity-type performance and error analysis.
    """
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("trained_models.id"), index=True)
    model_version = Column(String, nullable=True, index=True)

    # Dataset information
    test_dataset_path = Column(String, nullable=True)
    test_dataset_size = Column(Integer, nullable=True)
    test_split_ratio = Column(Float, default=0.2)

    # Overall metrics
    overall_f1_score = Column(Float, nullable=True)
    overall_precision = Column(Float, nullable=True)
    overall_recall = Column(Float, nullable=True)
    overall_accuracy = Column(Float, nullable=True)
    overall_loss = Column(Float, nullable=True)

    # Per-entity-type metrics (stored as JSON for flexibility)
    per_entity_metrics = Column(JSON, nullable=True)  # {entity_type: {f1, precision, recall}}

    # Error analysis
    error_analysis = Column(JSON, nullable=True)  # {error_type: count}
    confusion_matrix = Column(JSON, nullable=True)  # For classification tasks

    # Additional metadata
    evaluation_duration_seconds = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Relationships
    model = relationship("TrainedModel", back_populates="evaluation_runs")

    def __repr__(self) -> str:
        return f"EvaluationRun(model_version={self.model_version}, f1={self.overall_f1_score:.4f})"


class AnnotationTask(Base):
    """
    Task for human annotation of text for training data.

    Used by active learning system to identify uncertain predictions
    that need human review to improve model training.
    """
    __tablename__ = "annotation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String, nullable=True)  # Which model predicted this

    # Text and prediction
    text = Column(Text, nullable=False)
    entity_span = Column(String, nullable=True)  # The span identified for annotation
    predicted_label = Column(String, nullable=True)  # What the model predicted
    predicted_confidence = Column(Float, nullable=True)  # Confidence of prediction

    # Annotation
    ground_truth_label = Column(String, nullable=True)  # What human annotators say
    annotator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    annotation_notes = Column(Text, nullable=True)

    # Status tracking
    status = Column(String, default=AnnotationStatus.PENDING, index=True)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Active learning
    uncertainty_score = Column(Float, nullable=True)  # How uncertain the model was
    priority = Column(Integer, default=0, index=True)  # Priority for annotation

    # Relationships
    annotator = relationship("User")

    def __repr__(self) -> str:
        return f"AnnotationTask(status={self.status}, label={self.ground_truth_label})"


class NERPrediction(Base):
    """
    Predictions from NER pipeline on production inputs.

    Tracks predictions made by the NER pipeline on real documents,
    allowing for continuous monitoring and feedback loop integration.
    """
    __tablename__ = "ner_predictions"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("trained_models.id"), nullable=True, index=True)
    model_version = Column(String, nullable=True, index=True)

    # Input
    input_text = Column(Text, nullable=False)
    text_hash = Column(String, nullable=True, index=True)  # For deduplication

    # Predictions (JSON for flexibility)
    entities = Column(JSON, nullable=False)  # [{"text": "...", "label": "...", "confidence": 0.9, ...}]
    extraction_metadata = Column(JSON, nullable=True)  # Pipeline execution metadata

    # Quality metrics
    overall_confidence = Column(Float, nullable=True)
    requires_review = Column(Boolean, default=False, index=True)

    # Human review
    human_review_status = Column(String, default="none")  # none, pending, approved, rejected
    human_feedback = Column(JSON, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Temporal tracking
    predicted_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    model = relationship("TrainedModel", back_populates="predictions")
    reviewer = relationship("User")

    def __repr__(self) -> str:
        return f"NERPrediction(model_version={self.model_version}, entities={len(self.entities) if self.entities else 0})"


class ModelComparison(Base):
    """
    Comparison between two model versions for A/B testing.

    Tracks performance differences between models to support
    model selection and deployment decisions.
    """
    __tablename__ = "model_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    model_a_id = Column(Integer, ForeignKey("trained_models.id"), index=True)
    model_b_id = Column(Integer, ForeignKey("trained_models.id"), index=True)

    # Comparison metrics
    model_a_f1 = Column(Float, nullable=True)
    model_b_f1 = Column(Float, nullable=True)
    f1_delta = Column(Float, nullable=True)  # model_b_f1 - model_a_f1

    model_a_precision = Column(Float, nullable=True)
    model_b_precision = Column(Float, nullable=True)
    precision_delta = Column(Float, nullable=True)

    model_a_recall = Column(Float, nullable=True)
    model_b_recall = Column(Float, nullable=True)
    recall_delta = Column(Float, nullable=True)

    model_a_accuracy = Column(Float, nullable=True)
    model_b_accuracy = Column(Float, nullable=True)
    accuracy_delta = Column(Float, nullable=True)

    # Decision
    winner = Column(String, nullable=True)  # Which model is better
    recommendation = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"ModelComparison(winner={self.winner}, f1_delta={self.f1_delta:.4f})"


class ActiveLearningSession(Base):
    """
    Session for active learning iteration.

    Tracks each round of active learning: identify uncertain predictions,
    collect human annotations, retrain model.
    """
    __tablename__ = "active_learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    iteration_number = Column(Integer, nullable=False, index=True)
    source_model_version = Column(String, nullable=True)
    target_model_version = Column(String, nullable=True)

    # Configuration
    uncertainty_threshold = Column(Float, default=0.3)
    batch_size = Column(Integer, default=100)

    # Tracking
    candidates_identified = Column(Integer, default=0)
    annotations_collected = Column(Integer, default=0)
    retraining_completed = Column(Boolean, default=False)

    # Results
    model_improvement = Column(Float, nullable=True)  # Percentage improvement in F1
    notes = Column(Text, nullable=True)

    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"ActiveLearningSession(iteration={self.iteration_number}, annotations={self.annotations_collected})"
