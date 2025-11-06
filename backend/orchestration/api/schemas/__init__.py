"""
Pydantic schemas for API request/response validation.
"""

from .query import (
    QueryRequest,
    QueryResponse,
    QueryStatus,
    ExecutionTrace,
    AnswerMetadata,
    LegalBasis,
    AlternativeInterpretation,
    QueryHistoryItem,
    QueryHistoryResponse,
    QueryRetrieveResponse,
)
from .health import HealthResponse, ComponentStatus
from .feedback import (
    UserFeedbackRequest,
    RLCFFeedbackRequest,
    NERCorrectionRequest,
    FeedbackResponse,
)
from .stats import (
    PipelineStatsResponse,
    FeedbackStatsResponse,
)

__all__ = [
    "QueryRequest",
    "QueryResponse",
    "QueryStatus",
    "ExecutionTrace",
    "AnswerMetadata",
    "LegalBasis",
    "AlternativeInterpretation",
    "QueryHistoryItem",
    "QueryHistoryResponse",
    "QueryRetrieveResponse",
    "HealthResponse",
    "ComponentStatus",
    "UserFeedbackRequest",
    "RLCFFeedbackRequest",
    "NERCorrectionRequest",
    "FeedbackResponse",
    "PipelineStatsResponse",
    "FeedbackStatsResponse",
]
