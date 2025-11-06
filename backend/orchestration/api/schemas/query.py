"""
Pydantic schemas for query execution endpoints.

Aligned with MERL-T methodology requirements for request/response structures.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class QueryOptions(BaseModel):
    """Optional execution parameters for query."""

    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum refinement iterations (1-10)"
    )
    return_trace: bool = Field(
        default=True,
        description="Include full execution trace in response"
    )
    stream_response: bool = Field(
        default=False,
        description="Enable SSE streaming (future feature)"
    )
    timeout_ms: Optional[int] = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="Query timeout in milliseconds (1s-120s)"
    )


class QueryContext(BaseModel):
    """Additional context for query understanding."""

    temporal_reference: Optional[str] = Field(
        default=None,
        description="Temporal reference for legal interpretation (ISO date or 'latest')",
        examples=["2010-01-01", "latest"]
    )
    jurisdiction: Optional[str] = Field(
        default="nazionale",
        description="Legal jurisdiction scope",
        examples=["nazionale", "regionale", "comunitario"]
    )
    user_role: Optional[str] = Field(
        default="cittadino",
        description="User role for context-aware responses",
        examples=["cittadino", "avvocato", "giudice", "studente"]
    )
    previous_queries: Optional[List[str]] = Field(
        default=None,
        description="Previous queries in conversation (multi-turn context)"
    )


class QueryRequest(BaseModel):
    """
    Main request schema for POST /query/execute endpoint.

    Represents a legal query from the user with optional context and execution options.
    """

    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Legal query text",
        examples=["È valido un contratto firmato da un sedicenne?"]
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn conversations"
    )
    context: Optional[QueryContext] = Field(
        default=None,
        description="Additional query context"
    )
    options: Optional[QueryOptions] = Field(
        default_factory=QueryOptions,
        description="Execution options"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "È valido un contratto firmato da un sedicenne?",
                "session_id": "session_abc123",
                "context": {
                    "temporal_reference": "latest",
                    "jurisdiction": "nazionale",
                    "user_role": "cittadino"
                },
                "options": {
                    "max_iterations": 3,
                    "return_trace": True
                }
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class LegalBasis(BaseModel):
    """Reference to a legal norm supporting the answer."""

    norm_id: str = Field(..., description="Unique norm identifier")
    norm_title: str = Field(..., description="Norm title or description")
    article: Optional[str] = Field(None, description="Specific article/section")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    excerpt: Optional[str] = Field(None, description="Relevant text excerpt")


class AlternativeInterpretation(BaseModel):
    """Alternative legal interpretation with minority support."""

    position: str = Field(..., description="Alternative interpretation text")
    support_level: Literal["minority", "contested", "emerging"] = Field(
        ...,
        description="Level of legal support for this interpretation"
    )
    supporting_norms: List[str] = Field(
        default_factory=list,
        description="Norm IDs supporting this interpretation"
    )
    supporting_jurisprudence: Optional[List[str]] = Field(
        default=None,
        description="Case law supporting this interpretation"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Explanation of this alternative view"
    )


class Answer(BaseModel):
    """
    Complete legal answer with supporting evidence.

    Includes primary answer, confidence, legal basis, and alternative views.
    """

    primary_answer: str = Field(
        ...,
        description="Main legal answer synthesized from expert opinions"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score (0-1)"
    )
    legal_basis: List[LegalBasis] = Field(
        default_factory=list,
        description="Norms and legal sources supporting the answer"
    )
    jurisprudence: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Relevant case law (sentenze)"
    )
    alternative_interpretations: Optional[List[AlternativeInterpretation]] = Field(
        default=None,
        description="Alternative legal interpretations (if any)"
    )
    uncertainty_preserved: bool = Field(
        default=False,
        description="Whether expert disagreement was preserved (RLCF principle)"
    )
    consensus_level: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Expert consensus level (0-1, if multiple experts consulted)"
    )


class ExecutionTrace(BaseModel):
    """
    Complete execution trace for observability.

    Tracks all stages executed, experts consulted, agents used, and performance metrics.
    """

    trace_id: str = Field(..., description="Unique trace identifier")
    stages_executed: List[str] = Field(
        ...,
        description="Pipeline stages executed in order"
    )
    iterations: int = Field(..., ge=1, description="Number of refinement iterations")
    stop_reason: Optional[str] = Field(
        None,
        description="Reason for stopping iteration (if applicable)"
    )
    experts_consulted: List[str] = Field(
        default_factory=list,
        description="Expert types activated for this query"
    )
    agents_used: List[str] = Field(
        default_factory=list,
        description="Retrieval agents used (kg_agent, api_agent, vectordb_agent)"
    )
    total_time_ms: float = Field(..., ge=0.0, description="Total execution time (ms)")
    stage_timings: Optional[Dict[str, float]] = Field(
        None,
        description="Per-stage execution times (ms)"
    )
    tokens_used: Optional[int] = Field(
        None,
        description="Total LLM tokens consumed"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during execution"
    )


class AnswerMetadata(BaseModel):
    """Metadata about query processing."""

    complexity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Query complexity score (0-1)"
    )
    intent_detected: str = Field(
        ...,
        description="Detected query intent category"
    )
    concepts_identified: List[str] = Field(
        default_factory=list,
        description="Legal concepts extracted from query"
    )
    entities_identified: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Named entities extracted (NER)"
    )
    norms_consulted: int = Field(..., ge=0, description="Number of norms consulted")
    jurisprudence_consulted: int = Field(..., ge=0, description="Number of cases consulted")
    synthesis_mode: Optional[Literal["convergent", "divergent"]] = Field(
        None,
        description="Synthesis mode used"
    )


class QueryResponse(BaseModel):
    """
    Complete response for POST /query/execute endpoint.

    Contains the final answer, execution trace, and metadata.
    """

    trace_id: str = Field(..., description="Unique trace identifier for this query")
    session_id: Optional[str] = Field(None, description="Session ID (if provided)")
    answer: Answer = Field(..., description="Complete legal answer")
    execution_trace: Optional[ExecutionTrace] = Field(
        None,
        description="Full execution trace (if return_trace=True)"
    )
    metadata: AnswerMetadata = Field(..., description="Query processing metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp (UTC)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "session_id": "session_abc123",
                "answer": {
                    "primary_answer": "Un contratto firmato da un minorenne è annullabile...",
                    "confidence": 0.87,
                    "legal_basis": [
                        {
                            "norm_id": "cc-art-2",
                            "norm_title": "Maggiore età",
                            "relevance": 0.95
                        }
                    ],
                    "alternative_interpretations": [
                        {
                            "position": "Se il minorenne è emancipato...",
                            "support_level": "minority",
                            "supporting_norms": ["cc-art-390"]
                        }
                    ]
                },
                "metadata": {
                    "complexity_score": 0.68,
                    "intent_detected": "validità_atto",
                    "concepts_identified": ["capacità_di_agire", "validità_contrattuale"],
                    "norms_consulted": 4,
                    "jurisprudence_consulted": 2
                }
            }
        }


# ============================================================================
# STATUS SCHEMAS
# ============================================================================

class QueryStatus(BaseModel):
    """
    Query execution status for GET /query/status/{trace_id}.

    Used for async queries to check progress.
    """

    trace_id: str = Field(..., description="Query trace identifier")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        ...,
        description="Current execution status"
    )
    current_stage: Optional[str] = Field(
        None,
        description="Currently executing stage (if in_progress)"
    )
    progress_percent: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Completion percentage (0-100)"
    )
    started_at: datetime = Field(..., description="Execution start time (UTC)")
    completed_at: Optional[datetime] = Field(
        None,
        description="Execution completion time (UTC, if completed)"
    )
    estimated_completion_ms: Optional[int] = Field(
        None,
        description="Estimated time to completion (ms, if in_progress)"
    )
    result: Optional[QueryResponse] = Field(
        None,
        description="Complete result (if status=completed)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message (if status=failed)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "status": "in_progress",
                "current_stage": "experts",
                "progress_percent": 60.0,
                "started_at": "2025-01-05T14:30:22Z",
                "estimated_completion_ms": 1200
            }
        }


# ============================================================================
# HISTORY SCHEMAS
# ============================================================================

class QueryHistoryItem(BaseModel):
    """Single query item in user history."""

    trace_id: str = Field(..., description="Query trace identifier")
    query_text: str = Field(..., description="Original query text")
    timestamp: datetime = Field(..., description="Query submission time (UTC)")
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="User rating (if provided)"
    )
    answered: bool = Field(..., description="Whether query was answered successfully")
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Answer confidence (if answered)"
    )


class QueryHistoryResponse(BaseModel):
    """
    Response schema for GET /query/history/{user_id}.

    Returns paginated list of user's past queries.
    """

    queries: List[QueryHistoryItem] = Field(
        ...,
        description="List of query history items"
    )
    total: int = Field(..., ge=0, description="Total number of queries for user")
    limit: int = Field(..., ge=1, description="Page size limit")
    offset: int = Field(..., ge=0, description="Pagination offset")
    user_id: str = Field(..., description="User identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "queries": [
                    {
                        "trace_id": "QRY-20250105-abc123",
                        "query_text": "È valido un contratto...",
                        "timestamp": "2025-01-05T14:30:22Z",
                        "rating": 4,
                        "answered": True,
                        "confidence": 0.87
                    },
                    {
                        "trace_id": "QRY-20250104-def456",
                        "query_text": "Quali sono i limiti di età...",
                        "timestamp": "2025-01-04T10:15:00Z",
                        "rating": None,
                        "answered": True,
                        "confidence": 0.92
                    }
                ],
                "total": 127,
                "limit": 50,
                "offset": 0,
                "user_id": "user_789"
            }
        }


class QueryRetrieveResponse(BaseModel):
    """
    Response schema for GET /query/retrieve/{trace_id}.

    Returns complete query details including answer and feedback.
    """

    trace_id: str = Field(..., description="Query trace identifier")
    query: str = Field(..., description="Original query text")
    answer: Answer = Field(..., description="Complete answer")
    execution_trace: Optional[ExecutionTrace] = Field(
        None,
        description="Full execution trace"
    )
    metadata: AnswerMetadata = Field(..., description="Query metadata")
    feedback: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All feedback submitted for this query"
    )
    timestamp: datetime = Field(..., description="Query submission time (UTC)")

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "QRY-20250105-abc123",
                "query": "È valido un contratto firmato da un sedicenne?",
                "answer": {
                    "primary_answer": "Un contratto firmato da un minorenne è annullabile...",
                    "confidence": 0.87
                },
                "feedback": [
                    {
                        "type": "user",
                        "rating": 4,
                        "timestamp": "2025-01-05T14:35:00Z"
                    }
                ],
                "timestamp": "2025-01-05T14:30:22Z"
            }
        }
