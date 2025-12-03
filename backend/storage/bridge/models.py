"""
Bridge Table SQLAlchemy Models
================================

ORM models for mapping vector chunks (Qdrant) to graph nodes (FalkorDB).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class BridgeTableEntry(Base):
    """
    Bridge Table entry mapping a vector chunk to a graph node.

    Represents a many-to-many relationship:
    - One chunk can reference multiple graph nodes
    - One graph node can appear in multiple chunks
    """

    __tablename__ = "bridge_table"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Qdrant side (vector embeddings)
    chunk_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    chunk_text = Column(Text, nullable=True)  # Cached for debugging

    # FalkorDB side (graph nodes)
    graph_node_urn = Column(String(500), nullable=False, index=True)
    node_type = Column(String(50), nullable=False, index=True)  # Norma, ConcettoGiuridico, etc.

    # Relation metadata
    relation_type = Column(String(50), nullable=True, index=True)  # contained_in, references, etc.
    confidence = Column(Float, nullable=True, index=True)

    # Provenance
    source = Column(String(100), nullable=True)  # visualex, manual, llm_extraction
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Additional metadata (flexible JSONB)
    # Note: renamed from 'metadata' to 'extra_metadata' to avoid SQLAlchemy reserved name
    extra_metadata = Column("metadata", JSONB, nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('chunk_id', 'graph_node_urn', name='bridge_table_chunk_id_graph_node_urn_key'),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='bridge_table_confidence_check'),
    )

    def __repr__(self) -> str:
        return (
            f"<BridgeTableEntry(id={self.id}, "
            f"chunk_id={self.chunk_id}, "
            f"node_urn={self.graph_node_urn[:50]}..., "
            f"node_type={self.node_type})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "chunk_id": str(self.chunk_id),
            "chunk_text": self.chunk_text,
            "graph_node_urn": self.graph_node_urn,
            "node_type": self.node_type,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.extra_metadata,
        }
