"""
Database Models for Intent Classification & RLCF Feedback
==========================================================

Extends RLCF framework with intent classification tracking and community
feedback collection for ground truth dataset building.

Tables:
1. IntentClassification - All intent classifications (Phase 1+)
2. IntentValidationFeedback - Community feedback on classifications (RLCF)

Supports Phase 1→2→3 evolution:
- Phase 1: OpenRouter classifications + community review
- Phase 2: Fine-tuned model + community validation
- Phase 3: Community-trained model with continuous learning

Reference: backend/orchestration/intent_classifier.py
Integration: backend/rlcf_framework/routers/intent_router.py
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .database import Base


# ===================================
# Enums
# ===================================

class IntentTypeEnum(str, Enum):
    """Intent classification types"""
    CONTRACT_INTERPRETATION = "contract_interpretation"
    COMPLIANCE_QUESTION = "compliance_question"
    NORM_EXPLANATION = "norm_explanation"
    PRECEDENT_SEARCH = "precedent_search"
    UNKNOWN = "unknown"


class ClassificationSourceEnum(str, Enum):
    """Source of classification"""
    OPENROUTER_LLM = "openrouter_llm"  # Phase 1
    PRIMARY_MODEL = "primary_model"    # Phase 2
    COMMUNITY_MODEL = "community_model"  # Phase 3
    FALLBACK = "fallback"


class ValidationStatusEnum(str, Enum):
    """Status of community validation"""
    PENDING_REVIEW = "pending_review"
    VALIDATED = "validated"
    DISPUTED = "disputed"
    GROUND_TRUTH = "ground_truth"


# ===================================
# Intent Classification Table
# ===================================

class IntentClassification(Base):
    """
    Records all intent classifications for tracking and RLCF feedback collection.

    One record per query classification, linked to community feedback for
    ground truth building.
    """
    __tablename__ = "intent_classifications"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Classification Data
    query_text = Column(String(2000), nullable=False, index=True)
    predicted_intent = Column(SQLEnum(IntentTypeEnum), nullable=False, index=True)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(String(1000), nullable=True)

    # NER Integration
    norm_references = Column(JSON, nullable=True)  # References from NER pipeline
    norm_references_count = Column(Integer, default=0)

    # Classification Source & Versioning
    classification_source = Column(
        SQLEnum(ClassificationSourceEnum),
        nullable=False,
        default=ClassificationSourceEnum.OPENROUTER_LLM,
        index=True
    )
    model_version = Column(String(50), nullable=True)  # e.g., "phase1_openrouter", "phase2_finetuned"

    # RLCF Community Validation
    community_validated = Column(Boolean, default=False, index=True)
    validated_intent = Column(SQLEnum(IntentTypeEnum), nullable=True)  # Ground truth
    validation_status = Column(
        SQLEnum(ValidationStatusEnum),
        default=ValidationStatusEnum.PENDING_REVIEW,
        index=True
    )

    # Authority Scoring (RLCF aggregation)
    authority_scores_aggregated = Column(Float, nullable=True)  # Aggregated RLCF authority
    num_community_validations = Column(Integer, default=0)
    min_authority_for_ground_truth = Column(Float, default=0.6)

    # Active Learning
    uncertainty_score = Column(Float, nullable=True)  # For sampling uncertain cases (Phase 2+)
    needs_community_review = Column(Boolean, default=False, index=True)
    is_hard_example = Column(Boolean, default=False)  # Flagged for difficult cases

    # Training Dataset Integration
    used_for_training = Column(Boolean, default=False)
    training_batch_id = Column(String(36), nullable=True)  # Reference to training batch
    training_split = Column(String(20), nullable=True)  # 'train', 'val', 'test'

    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Any additional metadata (renamed from metadata - reserved name)

    # Relationships
    feedback_records = relationship(
        "IntentValidationFeedback",
        back_populates="classification",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<IntentClassification {self.id}: {self.predicted_intent} ({self.confidence:.2f})>"

    @property
    def is_consensus(self) -> bool:
        """Check if classification has consensus from community"""
        if not self.community_validated or not self.feedback_records:
            return False
        # Consensus if 80%+ feedback agrees with validated intent
        agree_count = sum(
            1 for f in self.feedback_records
            if f.validated_intent == self.validated_intent
        )
        return agree_count / len(self.feedback_records) >= 0.8

    @property
    def disagreement_count(self) -> int:
        """Count how many community validations disagree with current predicted intent"""
        if not self.feedback_records:
            return 0
        return sum(
            1 for f in self.feedback_records
            if f.validated_intent != self.predicted_intent
        )


# ===================================
# Intent Validation Feedback Table
# ===================================

class IntentValidationFeedback(Base):
    """
    Records individual community feedback on intent classifications.

    RLCF feedback loop: community experts validate/correct intent classifications
    to build ground truth dataset for Phase 2 fine-tuning.

    Each feedback record includes:
    - User authority score (A_u(t) from RLCF)
    - Whether feedback is correct/incorrect
    - Authority-weighted contribution to aggregated score
    """
    __tablename__ = "intent_validation_feedbacks"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    classification_id = Column(
        String(36),
        ForeignKey("intent_classifications.id"),
        nullable=False,
        index=True
    )

    # User & Authority
    user_id = Column(String(36), nullable=False, index=True)  # Links to users table
    user_authority_score = Column(Float, nullable=False)  # A_u(t) at time of feedback
    user_expertise_level = Column(String(50), nullable=True)  # 'novice', 'experienced', 'expert'

    # Validation Data
    validated_intent = Column(SQLEnum(IntentTypeEnum), nullable=False)  # Expert's correction/validation
    is_correct = Column(Boolean, nullable=True)  # True if matches predicted, False if correction
    correction_reasoning = Column(String(1000), nullable=True)  # Why expert changed prediction
    confidence_in_validation = Column(Float, nullable=True)  # Expert's confidence in their feedback

    # RLCF Weighting
    feedback_weight = Column(Float, nullable=False)  # Authority-weighted contribution
    # weight = (user_authority_score ** 1.5) / total_authority_sum
    # Higher authority → higher weight in aggregation

    # Agreement Tracking
    agrees_with_majority = Column(Boolean, nullable=True)  # Computed after aggregation
    num_supporting_feedbacks = Column(Integer, default=0)  # Other experts agreeing

    # Learning Metrics
    helps_model_improvement = Column(Boolean, nullable=True)  # Whether feedback improved model
    was_hard_case = Column(Boolean, default=False)  # Marked as hard during annotation

    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    extra_metadata = Column(JSON, nullable=True)  # Renamed from metadata - reserved name

    # Relationships
    classification = relationship(
        "IntentClassification",
        back_populates="feedback_records"
    )

    def __repr__(self):
        return f"<IntentValidationFeedback {self.id}: {self.validated_intent} (weight={self.feedback_weight:.3f})>"

    @property
    def is_disagreement(self) -> bool:
        """Check if this feedback disagrees with original prediction"""
        if self.classification:
            return self.validated_intent != self.classification.predicted_intent
        return False


# ===================================
# View/Query Helper (SQLAlchemy ORM)
# ===================================

class IntentClassificationStats:
    """Helper for aggregating intent classification statistics"""

    @staticmethod
    def get_pending_reviews(session, limit: int = 10):
        """Get classifications pending community review (sorted by uncertainty)"""
        return session.query(IntentClassification).filter(
            IntentClassification.validation_status == ValidationStatusEnum.PENDING_REVIEW,
            IntentClassification.needs_community_review == True
        ).order_by(
            IntentClassification.uncertainty_score.desc() if IntentClassification.uncertainty_score else None
        ).limit(limit).all()

    @staticmethod
    def get_ground_truth_dataset(session, min_authority: float = 0.6):
        """Get validated ground truth for training (Phase 2)"""
        return session.query(IntentClassification).filter(
            IntentClassification.validation_status == ValidationStatusEnum.GROUND_TRUTH,
            IntentClassification.authority_scores_aggregated >= min_authority,
            IntentClassification.community_validated == True
        ).all()

    @staticmethod
    def get_consensus_classifications(session):
        """Get classifications with strong community consensus (Phase 3)"""
        return session.query(IntentClassification).filter(
            IntentClassification.is_consensus == True
        ).all()

    @staticmethod
    def get_disputed_cases(session):
        """Get classifications with disagreement (need more review)"""
        return session.query(IntentClassification).filter(
            IntentClassification.validation_status == ValidationStatusEnum.DISPUTED
        ).all()
