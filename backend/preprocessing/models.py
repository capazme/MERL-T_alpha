"""
Data models for MERL-T Knowledge Graph with rich metadata and traceability.

This module defines the core data structures for a legally rigorous
knowledge graph system with full audit trail support.

Attribution: Adapted from NormGraph (github.com/user/NormGraph)
Modifications: Integrated with MERL-T preprocessing pipeline and Neo4j backend
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4


class EntityType(Enum):
    """Legal entity types for Italian legal system."""
    NORMA = "norma"  # Legal norm/article
    CONCETTO_GIURIDICO = "concetto_giuridico"  # Legal concept
    PERSONA = "persona"  # Person (judge, author, etc.)
    ORGANIZZAZIONE = "organizzazione"  # Organization
    GIURISPRUDENZA = "giurisprudenza"  # Case law
    DOTTRINA = "dottrina"  # Legal doctrine
    PROCEDURA = "procedura"  # Legal procedure
    ATTO = "atto"  # Legal act
    SENTENZA = "sentenza"  # Court decision
    CUSTOM = "custom"  # User-defined entity


class RelationType(Enum):
    """Relationship types between legal entities."""
    RIFERISCE = "riferisce"  # References
    MODIFICA = "modifica"  # Modifies/amends
    ABROGA = "abroga"  # Repeals
    DEROGA = "deroga"  # Derogates
    INTEGRA = "integra"  # Supplements
    APPLICA = "applica"  # Applies
    INTERPRETA = "interpreta"  # Interprets
    CONTRADDICE = "contraddice"  # Contradicts
    PRECEDE = "precede"  # Precedes (temporal)
    SEGUE = "segue"  # Follows (temporal)
    PARTE_DI = "parte_di"  # Part of (hierarchical)
    CONTIENE = "contiene"  # Contains (hierarchical)
    SIMILE_A = "simile_a"  # Similar to (semantic)
    DISCIPLINA = "disciplina"  # Governs
    CITA = "cita"  # Cites
    CUSTOM = "custom"  # User-defined relation


class ValidationStatus(Enum):
    """Validation status by domain experts."""
    PENDING = "pending"  # Awaiting validation
    APPROVED = "approved"  # Validated and approved
    REJECTED = "rejected"  # Rejected by validator
    NEEDS_REVIEW = "needs_review"  # Requires additional review
    MODIFIED = "modified"  # Modified by validator


class ExtractionMethod(Enum):
    """Method used to extract information."""
    AUTOMATIC = "automatic"  # LLM/NLP extraction
    MANUAL = "manual"  # Manual entry by user
    SEMI_AUTOMATIC = "semi_automatic"  # Automatic with manual correction
    IMPORTED = "imported"  # Imported from external source


@dataclass
class Provenance:
    """
    Provenance information for data traceability.

    Tracks the origin and chain of custody for any piece of information.
    """
    source_file: Optional[str] = None  # Original file path
    source_url: Optional[str] = None  # Original URL
    source_type: str = "unknown"  # Type of source (api, file, manual)

    # Location in source
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page: Optional[int] = None
    section: Optional[str] = None

    # Metadata
    extraction_method: ExtractionMethod = ExtractionMethod.AUTOMATIC
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    extractor_version: str = "1.0.0"

    # Raw context
    raw_text: Optional[str] = None  # Original text snippet
    context_before: Optional[str] = None
    context_after: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_file": self.source_file,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page": self.page,
            "section": self.section,
            "extraction_method": self.extraction_method.value,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "extractor_version": self.extractor_version,
            "raw_text": self.raw_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
        }


@dataclass
class Validation:
    """
    Validation record by domain expert.

    Tracks who validated what, when, and with what outcome.
    """
    validator_id: str  # ID of validator (username, email, etc.)
    validation_timestamp: datetime = field(default_factory=datetime.now)
    status: ValidationStatus = ValidationStatus.PENDING

    # Feedback
    comments: str = ""
    confidence: float = 1.0  # 0.0 to 1.0

    # Changes made during validation
    changes_made: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    validation_criteria: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # Supporting references

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "validator_id": self.validator_id,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "status": self.status.value,
            "comments": self.comments,
            "confidence": self.confidence,
            "changes_made": self.changes_made,
            "validation_criteria": self.validation_criteria,
            "references": self.references,
        }


@dataclass
class Node:
    """
    Graph node representing a legal entity with full traceability.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    label: str = ""
    entity_type: EntityType = EntityType.CUSTOM

    # Content
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Legal-specific metadata
    article_number: Optional[str] = None
    law_reference: Optional[str] = None  # e.g., "Codice Penale, Art. 123"
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

    # Traceability
    provenance: Optional[Provenance] = None
    confidence: float = 1.0  # 0.0 to 1.0

    # Validation
    validations: List[Validation] = field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.PENDING

    # Versioning
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    modified_by: str = "system"
    version: int = 1

    # Tags and categories
    tags: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)

    def add_validation(self, validation: Validation):
        """Add a validation record and update status."""
        self.validations.append(validation)
        self.validation_status = validation.status
        self.modified_at = datetime.now()

    def get_latest_validation(self) -> Optional[Validation]:
        """Get the most recent validation."""
        if not self.validations:
            return None
        return max(self.validations, key=lambda v: v.validation_timestamp)

    def is_validated(self) -> bool:
        """Check if node is validated and approved."""
        return self.validation_status == ValidationStatus.APPROVED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "attributes": self.attributes,
            "article_number": self.article_number,
            "law_reference": self.law_reference,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "confidence": self.confidence,
            "validations": [v.to_dict() for v in self.validations],
            "validation_status": self.validation_status.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "created_by": self.created_by,
            "modified_by": self.modified_by,
            "version": self.version,
            "tags": list(self.tags),
            "categories": list(self.categories),
        }


@dataclass
class Edge:
    """
    Graph edge representing a relationship between legal entities.
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: RelationType = RelationType.CUSTOM

    # Content
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Relationship strength and directionality
    weight: float = 1.0  # Relationship strength (0.0 to 1.0)
    directed: bool = True  # Whether relationship is directional

    # Legal-specific metadata
    legal_basis: Optional[str] = None  # Legal basis for relationship
    temporal_validity_start: Optional[datetime] = None
    temporal_validity_end: Optional[datetime] = None

    # Traceability
    provenance: Optional[Provenance] = None
    confidence: float = 1.0  # 0.0 to 1.0

    # Validation
    validations: List[Validation] = field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.PENDING

    # Versioning
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    modified_by: str = "system"
    version: int = 1

    # Tags
    tags: Set[str] = field(default_factory=set)

    def add_validation(self, validation: Validation):
        """Add a validation record and update status."""
        self.validations.append(validation)
        self.validation_status = validation.status
        self.modified_at = datetime.now()

    def get_latest_validation(self) -> Optional[Validation]:
        """Get the most recent validation."""
        if not self.validations:
            return None
        return max(self.validations, key=lambda v: v.validation_timestamp)

    def is_validated(self) -> bool:
        """Check if edge is validated and approved."""
        return self.validation_status == ValidationStatus.APPROVED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "description": self.description,
            "attributes": self.attributes,
            "weight": self.weight,
            "directed": self.directed,
            "legal_basis": self.legal_basis,
            "temporal_validity_start": self.temporal_validity_start.isoformat() if self.temporal_validity_start else None,
            "temporal_validity_end": self.temporal_validity_end.isoformat() if self.temporal_validity_end else None,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "confidence": self.confidence,
            "validations": [v.to_dict() for v in self.validations],
            "validation_status": self.validation_status.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "created_by": self.created_by,
            "modified_by": self.modified_by,
            "version": self.version,
            "tags": list(self.tags),
        }


@dataclass
class GraphMetadata:
    """
    Metadata for the entire knowledge graph.
    """
    graph_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""

    # Versioning
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"

    # Source information
    source_documents: List[str] = field(default_factory=list)
    construction_strategy: str = "unknown"

    # Statistics
    node_count: int = 0
    edge_count: int = 0
    validated_node_count: int = 0
    validated_edge_count: int = 0

    # Quality metrics
    average_confidence: float = 0.0
    completeness_score: float = 0.0  # % of expected entities found
    consistency_score: float = 0.0  # Internal consistency

    # Tags and categories
    tags: Set[str] = field(default_factory=set)
    domain: str = "legal"
    language: str = "it"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "created_by": self.created_by,
            "source_documents": self.source_documents,
            "construction_strategy": self.construction_strategy,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "validated_node_count": self.validated_node_count,
            "validated_edge_count": self.validated_edge_count,
            "average_confidence": self.average_confidence,
            "completeness_score": self.completeness_score,
            "consistency_score": self.consistency_score,
            "tags": list(self.tags),
            "domain": self.domain,
            "language": self.language,
        }


@dataclass
class ExtractionResult:
    """
    Result of an extraction operation.

    Contains extracted nodes and edges with metadata.
    """
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    extraction_stats: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node):
        """Add a node to the extraction result."""
        self.nodes.append(node)

    def add_edge(self, edge: Edge):
        """Add an edge to the extraction result."""
        self.edges.append(edge)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "extraction_stats": self.extraction_stats,
        }


@dataclass
class AuditLogEntry:
    """
    Single entry in the audit trail.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    # Operation details
    operation: str = ""  # add_node, modify_edge, validate, etc.
    entity_type: str = ""  # node, edge, graph
    entity_id: str = ""

    # Actor
    actor_id: str = "system"
    actor_type: str = "system"  # system, user, validator, script

    # Change details
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    diff: Optional[Dict[str, Any]] = None

    # Context
    operation_context: Dict[str, Any] = field(default_factory=dict)
    comments: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "diff": self.diff,
            "operation_context": self.operation_context,
            "comments": self.comments,
        }


# Export all models
__all__ = [
    "EntityType",
    "RelationType",
    "ValidationStatus",
    "ExtractionMethod",
    "Provenance",
    "Validation",
    "Node",
    "Edge",
    "GraphMetadata",
    "ExtractionResult",
    "AuditLogEntry",
]
