"""
SQLAlchemy models for MERL-T Orchestration API.

This module defines database models for:
- Query tracking
- Query results (answers and execution traces)
- User feedback
- RLCF expert feedback
- NER corrections

All models use async SQLAlchemy 2.0 patterns.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from .database import Base

# ============================================================================
# Helper Functions
# ============================================================================

def generate_uuid() -> str:
    """Generate UUID as string for primary keys."""
    return str(uuid.uuid4())

# ============================================================================
# MODEL: Query
# ============================================================================

class Query(Base):
    """
    Core query tracking model.

    Stores all queries with metadata, execution status, and timing information.
    """

    __tablename__ = "queries"

    # Primary Key
    trace_id = Column(String(50), primary_key=True, index=True)

    # Query Identification
    session_id = Column(String(100), index=True, nullable=True)
    user_id = Column(String(100), index=True, nullable=True)

    # Query Data
    query_text = Column(Text, nullable=False)
    query_context = Column(JSONB, default={})
    enriched_context = Column(JSONB, default={})

    # Execution Status
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    # Execution Options
    options = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    result = relationship("QueryResult", back_populates="query", uselist=False, cascade="all, delete-orphan")
    user_feedbacks = relationship("UserFeedback", back_populates="query", cascade="all, delete-orphan")
    rlcf_feedbacks = relationship("RLCFFeedback", back_populates="query", cascade="all, delete-orphan")
    ner_corrections = relationship("NERCorrection", back_populates="query", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'timeout')",
            name="queries_status_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query_text": self.query_text,
            "query_context": self.query_context,
            "enriched_context": self.enriched_context,
            "status": self.status,
            "options": self.options,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Query(trace_id={self.trace_id}, status={self.status})>"


# ============================================================================
# MODEL: QueryResult
# ============================================================================

class QueryResult(Base):
    """
    Query result model.

    Stores the answer, execution trace, and metadata for each query.
    1:1 relationship with Query.
    """

    __tablename__ = "query_results"

    # Primary Key
    result_id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign Key to Query (unique = 1:1 relationship)
    trace_id = Column(String(50), ForeignKey("queries.trace_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Answer Data
    primary_answer = Column(Text, nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False, default=0.0)

    legal_basis = Column(JSONB, default=[])
    alternatives = Column(JSONB, default=[])

    uncertainty_preserved = Column(Boolean, default=False)
    sources_consulted = Column(JSONB, default=[])

    # Execution Trace
    execution_trace = Column(JSONB, default={})

    # Metadata
    metadata = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    query = relationship("Query", back_populates="result")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="query_results_confidence_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "result_id": self.result_id,
            "trace_id": self.trace_id,
            "primary_answer": self.primary_answer,
            "confidence": float(self.confidence) if self.confidence else 0.0,
            "legal_basis": self.legal_basis,
            "alternatives": self.alternatives,
            "uncertainty_preserved": self.uncertainty_preserved,
            "sources_consulted": self.sources_consulted,
            "execution_trace": self.execution_trace,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<QueryResult(trace_id={self.trace_id}, confidence={self.confidence})>"


# ============================================================================
# MODEL: UserFeedback
# ============================================================================

class UserFeedback(Base):
    """
    User feedback model.

    Stores user ratings (1-5 stars) and optional comments for queries.
    1:N relationship with Query.
    """

    __tablename__ = "user_feedback"

    # Primary Key
    feedback_id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign Key to Query
    trace_id = Column(String(50), ForeignKey("queries.trace_id", ondelete="CASCADE"), nullable=False, index=True)

    # User Identification
    user_id = Column(String(100), index=True, nullable=True)

    # Feedback Data
    rating = Column(Integer, nullable=False)
    feedback_text = Column(Text, nullable=True)
    categories = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    query = relationship("Query", back_populates="user_feedbacks")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="user_feedback_rating_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "categories": self.categories,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<UserFeedback(feedback_id={self.feedback_id}, rating={self.rating})>"


# ============================================================================
# MODEL: RLCFFeedback
# ============================================================================

class RLCFFeedback(Base):
    """
    RLCF expert feedback model.

    Stores expert corrections with authority weighting and training examples.
    1:N relationship with Query.
    """

    __tablename__ = "rlcf_feedback"

    # Primary Key
    feedback_id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign Key to Query
    trace_id = Column(String(50), ForeignKey("queries.trace_id", ondelete="CASCADE"), nullable=False, index=True)

    # Expert Identification
    expert_id = Column(String(100), nullable=False, index=True)

    # Authority Weighting
    authority_score = Column(Numeric(4, 3), nullable=False)

    # Corrections Data
    corrections = Column(JSONB, nullable=False, default={})

    overall_rating = Column(Integer, nullable=False)

    # Training Examples
    training_examples_generated = Column(Integer, default=0)
    scheduled_for_retraining = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    query = relationship("Query", back_populates="rlcf_feedbacks")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "authority_score >= 0.0 AND authority_score <= 1.0",
            name="rlcf_feedback_authority_check"
        ),
        CheckConstraint(
            "overall_rating >= 1 AND overall_rating <= 5",
            name="rlcf_feedback_rating_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "trace_id": self.trace_id,
            "expert_id": self.expert_id,
            "authority_score": float(self.authority_score) if self.authority_score else 0.0,
            "corrections": self.corrections,
            "overall_rating": self.overall_rating,
            "training_examples_generated": self.training_examples_generated,
            "scheduled_for_retraining": self.scheduled_for_retraining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<RLCFFeedback(feedback_id={self.feedback_id}, expert_id={self.expert_id}, authority={self.authority_score})>"


# ============================================================================
# MODEL: NERCorrection
# ============================================================================

class NERCorrection(Base):
    """
    NER correction model.

    Stores NER entity extraction corrections for model training.
    1:N relationship with Query.
    """

    __tablename__ = "ner_corrections"

    # Primary Key
    correction_id = Column(String(36), primary_key=True, default=generate_uuid)

    # Foreign Key to Query
    trace_id = Column(String(50), ForeignKey("queries.trace_id", ondelete="CASCADE"), nullable=False, index=True)

    # Expert Identification
    expert_id = Column(String(100), nullable=False, index=True)

    # Correction Type
    correction_type = Column(String(20), nullable=False, index=True)

    # Correction Data
    correction_data = Column(JSONB, nullable=False)

    # Training Example
    training_example_generated = Column(Boolean, default=True)
    scheduled_for_retraining = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    query = relationship("Query", back_populates="ner_corrections")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "correction_type IN ('MISSING_ENTITY', 'SPURIOUS_ENTITY', 'WRONG_BOUNDARY', 'WRONG_TYPE')",
            name="ner_corrections_type_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "correction_id": self.correction_id,
            "trace_id": self.trace_id,
            "expert_id": self.expert_id,
            "correction_type": self.correction_type,
            "correction_data": self.correction_data,
            "training_example_generated": self.training_example_generated,
            "scheduled_for_retraining": self.scheduled_for_retraining,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<NERCorrection(correction_id={self.correction_id}, type={self.correction_type})>"


# ============================================================================
# API Key Models (Week 8 Day 4 - Authentication & Rate Limiting)
# ============================================================================

class ApiKey(Base):
    """
    API Key model for authentication and rate limiting.

    Stores hashed API keys with role-based access control and rate limiting tiers.
    Never stores plaintext keys - only SHA-256 hashes.
    """
    __tablename__ = "api_keys"

    # Primary Key
    key_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # User Association (optional - for future user management)
    user_id = Column(String(100), index=True)

    # API Key (SHA-256 hash for security)
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Role-Based Access Control
    role = Column(String(20), nullable=False, default="user", index=True)

    # Rate Limiting Tier
    rate_limit_tier = Column(String(20), nullable=False, default="standard")

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Metadata
    description = Column(Text)
    created_by = Column(String(100))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), index=True)
    last_used_at = Column(DateTime(timezone=True))

    # Relationships
    usage_records = relationship("ApiUsage", back_populates="api_key", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'user', 'guest')",
            name="api_keys_role_check"
        ),
        CheckConstraint(
            "rate_limit_tier IN ('unlimited', 'premium', 'standard', 'limited')",
            name="api_keys_tier_check"
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary (excludes api_key_hash for security)."""
        return {
            "key_id": self.key_id,
            "user_id": self.user_id,
            "role": self.role,
            "rate_limit_tier": self.rate_limit_tier,
            "is_active": self.is_active,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def __repr__(self) -> str:
        return f"<ApiKey(key_id={self.key_id}, role={self.role}, is_active={self.is_active})>"


class ApiUsage(Base):
    """
    API Usage model for tracking requests and rate limiting.

    Records every API request with timing and response information for:
    - Rate limiting (sliding window algorithm)
    - Analytics and monitoring
    - Auditing and security
    """
    __tablename__ = "api_usage"

    # Primary Key
    usage_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key to API Key
    key_id = Column(String(36), ForeignKey("api_keys.key_id", ondelete="CASCADE"), nullable=False, index=True)

    # Request Information
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)

    # Response Information
    response_status = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Numeric(10, 2))

    # Client Information
    ip_address = Column(String(45))
    user_agent = Column(Text)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    api_key = relationship("ApiKey", back_populates="usage_records")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS')",
            name="api_usage_method_check"
        ),
        # Composite index for rate limiting queries
        Index("idx_api_usage_rate_limit", "key_id", "timestamp"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "usage_id": self.usage_id,
            "key_id": self.key_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "response_status": self.response_status,
            "response_time_ms": float(self.response_time_ms) if self.response_time_ms else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self) -> str:
        return f"<ApiUsage(usage_id={self.usage_id}, endpoint={self.endpoint}, status={self.response_status})>"
