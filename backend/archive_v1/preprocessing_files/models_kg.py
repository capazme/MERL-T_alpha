"""
Knowledge Graph Database Models (SQLAlchemy 2.0)
=================================================

PostgreSQL tables for KG enrichment service:
- staging_entities: Review queue for new entities
- kg_edge_audit: Provenance tracking for relationships
- kg_quality_metrics: Nightly quality statistics
- controversy_records: Flagged controversial items
- contributions: Community contribution tracking

All models use SQLAlchemy 2.0 async patterns.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    JSON, Text, ForeignKey, Enum, Index, UniqueConstraint,
    ARRAY, event
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSON as PGJSON

# Assume this base is defined elsewhere or import from existing models
try:
    from backend.rlcf_framework.models import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


# ==========================================
# Enums
# ==========================================

class EntityTypeEnum(PyEnum):
    """Entity types in staging queue (13 types from LLM extraction)."""
    NORMA = "norma"
    CONCETTO_GIURIDICO = "concetto_giuridico"
    SOGGETTO_GIURIDICO = "soggetto_giuridico"
    ATTO_GIUDIZIARIO = "atto_giudiziario"
    DOTTRINA = "dottrina"
    PROCEDURA = "procedura"
    PRINCIPIO_GIURIDICO = "principio_giuridico"
    RESPONSABILITA = "responsabilita"
    DIRITTO_SOGGETTIVO = "diritto_soggettivo"
    SANZIONE = "sanzione"
    DEFINIZIONE_LEGALE = "definizione_legale"
    FATTO_GIURIDICO = "fatto_giuridico"
    MODALITA_GIURIDICA = "modalita_giuridica"
    # Legacy types
    SENTENZA = "sentenza"
    CONTRIBUTION = "contribution"


class SourceTypeEnum(PyEnum):
    """Source types for entities."""
    VISUALEX = "visualex"  # visualex API (Normattiva + BrocardiInfo)
    NORMATTIVA = "normattiva"
    CASSAZIONE = "cassazione"
    TAR = "tar"
    CORTE_COSTITUZIONALE = "corte_costituzionale"
    CURATED_DOCTRINE = "curated_doctrine"
    COMMUNITY_CONTRIBUTION = "community_contribution"
    RLCF_FEEDBACK = "rlcf_feedback"
    DOCUMENTS = "documents"  # PDF/DOCX with LLM extraction


class ReviewStatusEnum(PyEnum):
    """Status of entity in review queue."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    HOLD = "hold"


class DoctrineTypeEnum(PyEnum):
    """Type of doctrine commentary."""
    INTERPRETATIVO = "interpretativo"
    CRITICO = "critico"
    APPLICATIVO = "applicativo"
    SISTEMATICO = "sistematico"


class ContributionTypeEnum(PyEnum):
    """Type of community contribution."""
    ACADEMIC_PAPER = "academic_paper"
    EXPERT_COMMENTARY = "expert_commentary"
    CASE_ANALYSIS = "case_analysis"
    PRACTICE_GUIDE = "practice_guide"


class RelationshipTypeEnum(PyEnum):
    """Relationship types (subset of 65 total)."""
    APPLICA = "applica"
    INTERPRETA = "interpreta"
    COMMENTA = "commenta"
    CITA = "cita"
    DISCIPLINA = "disciplina"
    IMPONE = "impone"
    ESPRIME_PRINCIPIO = "esprime_principio"
    CONTIENE = "contiene"
    HA_VERSIONE = "ha_versione"
    SOSTIUISCE = "sostituisce"
    INSERISCE = "inserisce"
    ABROGA = "abroga"
    DIPENDE_DA = "dipende_da"
    PRESUPPONE = "presuppone"
    OTHER = "other"


# ==========================================
# Staging Queue Table
# ==========================================

class StagingEntity(Base):
    """
    Review queue for new entities (NER extraction, API imports, etc).

    Entities wait here for expert approval before entering Neo4j graph.
    """

    __tablename__ = "kg_staging_entities"

    id = Column(String(36), primary_key=True)
    entity_type = Column(Enum(EntityTypeEnum), nullable=False, index=True)
    source_type = Column(Enum(SourceTypeEnum), nullable=False, index=True)

    # Entity metadata
    label = Column(String(500), nullable=False)
    description = Column(Text)
    metadata_json = Column(PGJSON, default={})

    # Confidence from extraction (NER, API, etc)
    confidence_initial = Column(Float, default=0.5)
    confidence_final = Column(Float, nullable=True)

    # Review workflow
    status = Column(Enum(ReviewStatusEnum), default=ReviewStatusEnum.PENDING, index=True)
    reviewer_id = Column(String(100), nullable=True, index=True)
    review_comments = Column(Text, nullable=True)
    review_suggestions = Column(PGJSON, default={})  # Structured suggestions

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Neo4j reference (if approved)
    neo4j_node_id = Column(String(100), nullable=True, unique=True)

    # Auditing
    created_by = Column(String(100), nullable=True)
    last_modified_by = Column(String(100), nullable=True)
    last_modified_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_staging_entity_status_created", "status", "created_at"),
        Index("idx_staging_entity_reviewer", "reviewer_id", "status"),
    )

    def __repr__(self):
        return f"<StagingEntity id={self.id} status={self.status}>"


class StagingRelationship(Base):
    """
    Review queue for extracted relationships (LLM extraction, community, etc).

    Relationships wait here for expert approval before entering Neo4j graph.
    """

    __tablename__ = "kg_staging_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relationship_type = Column(String(100), nullable=False, index=True)  # CITA, MODIFICA, etc.

    # Source and target identification
    source_entity_data = Column(PGJSON, nullable=False)  # {entity_type, identifier, properties}
    target_entity_data = Column(PGJSON, nullable=False)  # {entity_type, identifier, properties}

    # Relationship properties
    properties = Column(PGJSON, default={})

    # Source tracking
    source_type = Column(Enum(SourceTypeEnum), nullable=False, index=True)
    raw_data = Column(PGJSON, default={})  # Full extraction data

    # Confidence from extraction
    confidence_score = Column(Float, default=0.5, nullable=False)

    # Review workflow
    status = Column(Enum(ReviewStatusEnum), default=ReviewStatusEnum.PENDING, index=True)
    reviewer_id = Column(String(100), nullable=True, index=True)
    review_comments = Column(Text, nullable=True)

    # Extra metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    extra_metadata = Column(PGJSON, default={})  # source_article, llm_model, etc.

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Neo4j reference (if approved)
    neo4j_edge_id = Column(String(100), nullable=True)

    # Auditing
    created_by = Column(String(100), nullable=True)
    last_modified_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_staging_rel_status_created", "status", "created_at"),
        Index("idx_staging_rel_type", "relationship_type", "status"),
    )

    def __repr__(self):
        return f"<StagingRelationship id={self.id} type={self.relationship_type} status={self.status}>"


# ==========================================
# Edge Audit Trail Table
# ==========================================

class KGEdgeAudit(Base):
    """
    Audit trail for relationship provenance.

    Every relationship (edge) in Neo4j is traceable to its source(s).
    Multiple audit records can exist for same edge (different sources).
    """

    __tablename__ = "kg_edge_audit"

    id = Column(String(36), primary_key=True)

    # Edge identification
    edge_id = Column(String(100), nullable=False, index=True)
    source_node_id = Column(String(100), nullable=False)
    target_node_id = Column(String(100), nullable=False)
    relationship_type = Column(Enum(RelationshipTypeEnum), nullable=False)

    # Source tracking
    source_type = Column(Enum(SourceTypeEnum), nullable=False, index=True)
    source_record_id = Column(String(100), nullable=True)  # e.g., norm_id, sentenza_numero

    # Authority & confidence
    confidence_score = Column(Float, default=0.5)
    authority_score = Column(Float, nullable=True)  # RLCF authority if applicable

    # RLCF quorum (if relationship was created via RLCF)
    rlcf_quorum_satisfied = Column(Boolean, default=False)
    rlcf_expert_count = Column(Integer, nullable=True)
    rlcf_authority_aggregated = Column(Float, nullable=True)

    # Relationship context
    relationship_metadata = Column(PGJSON, default={})
    # Example: {
    #   "tipo_commento": "interpretativo",
    #   "relation_context": "contract_interpretation",
    #   "conflicting_interpretation": false
    # }

    # Lineage
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)

    # Modifications
    modified_at = Column(DateTime, onupdate=datetime.utcnow)
    modified_by = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    __table_args__ = (
        Index("idx_edge_audit_source", "source_node_id", "target_node_id", "relationship_type"),
        Index("idx_edge_audit_created", "created_at"),
        Index("idx_edge_audit_active", "is_active"),
    )

    def __repr__(self):
        return f"<KGEdgeAudit edge={self.edge_id} source={self.source_type}>"


# ==========================================
# Quality Metrics Table
# ==========================================

class KGQualityMetrics(Base):
    """
    Daily/hourly quality statistics for the knowledge graph.

    Computed nightly or on-demand to track:
    - Node/edge counts
    - Confidence distributions
    - Controversy ratio
    - Completeness scores
    """

    __tablename__ = "kg_quality_metrics"

    id = Column(String(36), primary_key=True)

    # Computation metadata
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    computation_duration_ms = Column(Integer)  # How long did computation take

    # Counts
    total_nodes = Column(Integer, default=0)
    total_edges = Column(Integer, default=0)

    # By type (JSON to handle dynamic types)
    nodes_by_type = Column(PGJSON, default={})  # {Norma: 2891, Sentenza: 145, ...}
    edges_by_type = Column(PGJSON, default={})  # {APPLICA: 12340, INTERPRETA: 8932, ...}

    # Confidence distribution
    avg_confidence = Column(Float, default=0.5)
    min_confidence = Column(Float)
    max_confidence = Column(Float)
    nodes_with_low_confidence = Column(Integer, default=0)  # confidence < 0.7

    # Controversy
    nodes_with_controversy = Column(Integer, default=0)
    controversy_ratio = Column(Float, default=0.0)  # controversy_nodes / total_nodes

    # Completeness
    orphaned_nodes = Column(Integer, default=0)  # Nodes with no edges
    circular_dependencies = Column(Integer, default=0)
    version_integrity_issues = Column(Integer, default=0)

    # Data freshness
    last_normattiva_sync = Column(DateTime, nullable=True)
    last_cassazione_sync = Column(DateTime, nullable=True)
    last_rlcf_update = Column(DateTime, nullable=True)

    # Staging queue
    staging_queue_pending = Column(Integer, default=0)
    staging_queue_hold = Column(Integer, default=0)
    staging_queue_processing_days_avg = Column(Float, default=0.0)

    # Community contributions
    community_contributions_awaiting_vote = Column(Integer, default=0)
    community_contributions_total = Column(Integer, default=0)
    community_upvote_ratio = Column(Float, default=0.0)

    # Audit trail
    total_audit_records = Column(Integer, default=0)
    audit_records_by_source = Column(PGJSON, default={})

    # Redis cache
    cache_entries = Column(Integer, default=0)
    cache_hit_ratio = Column(Float, default=0.0)

    # Status
    is_latest = Column(Boolean, default=True, index=True)

    __table_args__ = (
        Index("idx_metrics_computed", "computed_at"),
        Index("idx_metrics_latest", "is_latest"),
    )

    def __repr__(self):
        return f"<KGQualityMetrics computed={self.computed_at} nodes={self.total_nodes}>"


# ==========================================
# Controversy Records Table
# ==========================================

class ControversyRecord(Base):
    """
    Records of controversial/conflicting data in graph.

    Flagged when:
    - RLCF feedback contradicts official norms
    - Competing doctrine interpretations exist
    - Newer case law overrules precedents
    """

    __tablename__ = "kg_controversy_records"

    id = Column(String(36), primary_key=True)

    # Flagged item
    node_id = Column(String(100), nullable=False, index=True)
    node_type = Column(Enum(EntityTypeEnum), nullable=False)
    node_label = Column(String(500))

    # Controversy type
    controversy_type = Column(String(50), nullable=False)  # "rlcf_conflict", "doctrine_conflict", "overruled", etc
    description = Column(Text)

    # Conflicting data
    conflicting_sources = Column(ARRAY(String), default=[])  # Sources involved
    conflicting_opinions = Column(PGJSON, default={})  # {source: opinion, ...}

    # RLCF metrics (if RLCF-triggered)
    rlcf_votes = Column(PGJSON, nullable=True)  # {opinion: vote_count, ...}
    rlcf_authority_avg = Column(Float, nullable=True)
    rlcf_expert_count = Column(Integer, nullable=True)

    # Status
    flagged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, index=True)

    # Visibility
    severity = Column(String(20), default="medium")  # "low", "medium", "high", "critical"
    visible_to_users = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_controversy_node", "node_id"),
        Index("idx_controversy_type", "controversy_type"),
        Index("idx_controversy_resolved", "is_resolved"),
    )

    def __repr__(self):
        return f"<ControversyRecord node={self.node_id} type={self.controversy_type}>"


# ==========================================
# Contributions Table
# ==========================================

class Contribution(Base):
    """
    Community contributions to the knowledge graph.

    Users (ALIS members or community) can submit:
    - Academic papers
    - Expert commentary
    - Case analyses
    - Practice guides

    Workflow: Upload → Community voting (7 days) → Auto-approve OR expert review → Neo4j
    """

    __tablename__ = "kg_contributions"

    id = Column(String(36), primary_key=True)
    neo4j_node_id = Column(String(100), nullable=True, unique=True, index=True)

    # Contributor info
    author_id = Column(String(100), nullable=False, index=True)
    author_name = Column(String(200), nullable=True)
    author_email = Column(String(200), nullable=True)

    # Contribution details
    tipo = Column(Enum(ContributionTypeEnum), nullable=False)
    titolo = Column(String(500), nullable=False)
    descrizione = Column(Text)
    file_path = Column(String(255), nullable=True)  # S3 or local path
    file_hash = Column(String(64), nullable=True)  # SHA-256 for dedup

    # Content
    content_text = Column(Text, nullable=True)  # Extracted text
    content_metadata = Column(PGJSON, default={})
    # Example: {
    #   "pages": 5,
    #   "key_concepts": ["responsabilità", "danno"],
    #   "cited_norms": ["Art. 2043 c.c."]
    # }

    # Voting
    upvote_count = Column(Integer, default=0)
    downvote_count = Column(Integer, default=0)
    net_votes = Column(Integer, default=0)  # Computed as upvote_count - downvote_count

    # Status & confidence
    status = Column(String(20), default="pending", index=True)  # pending, voting, approved, rejected
    confidence = Column(Float, default=0.5)
    expert_reviewed = Column(Boolean, default=False)
    expert_reviewer_id = Column(String(100), nullable=True)
    expert_confidence = Column(Float, nullable=True)

    # Voting window
    submission_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    voting_end_date = Column(DateTime, nullable=True)  # submission_date + 7 days
    approval_date = Column(DateTime, nullable=True)

    # Tracking
    view_count = Column(Integer, default=0)
    citation_count = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_contribution_author", "author_id", "submission_date"),
        Index("idx_contribution_status", "status", "submission_date"),
        Index("idx_contribution_type", "tipo"),
        UniqueConstraint("author_id", "file_hash", name="uq_contribution_dedup"),
    )

    def __repr__(self):
        return f"<Contribution id={self.id} author={self.author_id} status={self.status}>"


# ==========================================
# Event Listeners
# ==========================================

@event.listens_for(StagingEntity, "before_update")
def update_staging_timestamp(mapper, connection, target):
    """Auto-update last_modified_at on any change."""
    target.last_modified_at = datetime.utcnow()


@event.listens_for(KGEdgeAudit, "before_update")
def update_audit_timestamp(mapper, connection, target):
    """Auto-update modified_at on any change."""
    target.modified_at = datetime.utcnow()


@event.listens_for(Contribution, "before_update")
def update_contribution_votes(mapper, connection, target):
    """Auto-compute net_votes."""
    target.net_votes = target.upvote_count - target.downvote_count


# ==========================================
# Database Initialization
# ==========================================

async def init_kg_tables(engine) -> bool:
    """
    Create all KG tables in PostgreSQL.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        True if successful
    """
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return True
    except Exception as e:
        print(f"Error initializing KG tables: {str(e)}")
        return False


async def create_indexes(engine) -> bool:
    """
    Create query performance indexes.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        True if successful
    """
    try:
        async with engine.begin() as conn:
            # Additional performance indexes
            await conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_staging_entity_type_status
                   ON kg_staging_entities(entity_type, status)"""
            )
            await conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_edge_audit_source_type
                   ON kg_edge_audit(source_type, created_at DESC)"""
            )
            await conn.execute(
                """CREATE INDEX IF NOT EXISTS idx_contribution_voting_status
                   ON kg_contributions(status, voting_end_date)"""
            )
        return True
    except Exception as e:
        print(f"Error creating indexes: {str(e)}")
        return False
