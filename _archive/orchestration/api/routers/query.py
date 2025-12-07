"""
Query Router

FastAPI router for query execution endpoints.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from ..schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryStatus,
    QueryHistoryResponse,
    QueryHistoryItem,
    QueryRetrieveResponse,
)
from ..schemas.examples import (
    QUERY_REQUEST_EXAMPLES,
    QUERY_RESPONSE_EXAMPLES,
    ERROR_RESPONSE_EXAMPLES,
)
from ..services.query_executor import QueryExecutor
from ..services.cache_service import cache_service
from ..services.persistence_service import persistence_service
from ..middleware.auth import verify_api_key
from ..middleware.rate_limit import check_rate_limit
from ..models import ApiKey

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["Query Execution"]
)

# Global QueryExecutor instance (singleton pattern)
query_executor = QueryExecutor()


@router.post(
    "/execute",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Legal Query",
    description="""
Execute a complete MERL-T pipeline for a legal query.

The query flows through:
1. **Preprocessing**: Query understanding, NER, concept mapping
2. **Routing**: LLM Router generates ExecutionPlan
3. **Retrieval**: Parallel execution of KG, API, VectorDB agents
4. **Reasoning**: Parallel execution of 4 expert types
5. **Synthesis**: Convergent or divergent synthesis
6. **Iteration**: Multi-turn refinement if needed

Returns the final answer with confidence, legal basis, execution trace, and metadata.

**Try different examples** using the dropdown in the request body to see various query scenarios.
    """,
    responses={
        200: {
            "description": "Query executed successfully",
            "content": {
                "application/json": {
                    "examples": QUERY_RESPONSE_EXAMPLES
                }
            }
        },
        400: {
            "description": "Invalid query request - validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "validation_error": ERROR_RESPONSE_EXAMPLES["validation_error"]
                    }
                }
            }
        },
        408: {
            "description": "Query execution timeout",
            "content": {
                "application/json": {
                    "examples": {
                        "timeout": ERROR_RESPONSE_EXAMPLES["timeout"]
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "examples": {
                        "internal_error": ERROR_RESPONSE_EXAMPLES["internal_error"]
                    }
                }
            }
        }
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": QUERY_REQUEST_EXAMPLES
                }
            }
        }
    }
)
async def execute_query(
    request: QueryRequest,
    api_key: ApiKey = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit)
) -> QueryResponse:
    """
    Execute a legal query through the complete MERL-T pipeline.

    Args:
        request: QueryRequest with query text, context, and options
        api_key: Verified API key (injected by auth middleware)
        _rate_limit: Rate limit check (injected by rate limit middleware)

    Returns:
        QueryResponse with answer, trace, and metadata

    Raises:
        HTTPException: 400 for invalid request, 401 for auth, 408 for timeout, 429 for rate limit, 500 for errors
    """
    try:
        logger.info(f"Received query: {request.query[:100]}...")

        # Execute query via QueryExecutor (handles caching and database persistence)
        response = await query_executor.execute_query(request)

        logger.info(f"[{response.trace_id}] Query executed successfully")
        return response

    except asyncio.TimeoutError:
        logger.error("Query execution timeout")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Query execution exceeded maximum timeout. Please try again with a simpler query or increase timeout."
        )

    except ValueError as e:
        logger.error(f"Invalid query request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query request: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during query execution: {str(e)}"
        )


@router.get(
    "/status/{trace_id}",
    response_model=QueryStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Query Status",
    description="""
Retrieve the execution status of a query by trace ID.

Useful for:
- Async queries running in background
- Polling for completion
- Debugging failed queries

Returns the current status, progress percentage, and result (if completed).
    """,
    responses={
        200: {
            "description": "Query status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "trace_id": "QRY-20250105-abc123",
                        "status": "completed",
                        "started_at": "2025-01-05T14:30:22Z",
                        "completed_at": "2025-01-05T14:30:25Z",
                        "result": {"answer": {"primary_answer": "..."}}
                    }
                }
            }
        },
        404: {"description": "Query not found"}
    }
)
async def get_query_status(
    trace_id: str,
    api_key: ApiKey = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit)
) -> QueryStatus:
    """
    Get execution status for a query by trace ID.

    Args:
        trace_id: Unique query trace identifier
        api_key: Verified API key (injected by auth middleware)
        _rate_limit: Rate limit check (injected by rate limit middleware)

    Returns:
        QueryStatus with current status and result (if completed)

    Raises:
        HTTPException: 401 for auth, 404 if trace_id not found, 429 for rate limit
    """
    logger.info(f"Status request for trace_id: {trace_id}")

    # Try Redis cache first
    cached_status = await cache_service.get_query_status(trace_id)

    if cached_status:
        logger.info(f"[{trace_id}] Status found in Redis cache")
        # Build QueryStatus response from cache
        query_status = QueryStatus(
            trace_id=cached_status.get("trace_id", trace_id),
            status=cached_status.get("status", "processing"),
            current_stage=cached_status.get("current_stage"),
            progress_percent=cached_status.get("progress_percent"),
            stage_logs=cached_status.get("stage_logs"),
            started_at=cached_status.get("started_at", datetime.utcnow()),
            completed_at=cached_status.get("completed_at"),
            estimated_completion_ms=None,
            result=cached_status.get("result"),
            error=cached_status.get("error"),
        )
        return query_status

    # Fallback to database
    logger.info(f"[{trace_id}] Cache miss, checking database...")
    query = await persistence_service.get_query(trace_id)

    if not query:
        logger.warning(f"Trace ID not found: {trace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with trace_id '{trace_id}' not found. It may have expired or never existed."
        )

    # Get result if completed
    result = None
    if query.status == "completed":
        query_result = await persistence_service.get_query_result(trace_id)
        if query_result:
            result = {
                "answer": query_result.primary_answer,
                "confidence": float(query_result.confidence),
                "legal_basis": query_result.legal_basis,
            }

    # Build QueryStatus response
    query_status = QueryStatus(
        trace_id=query.trace_id,
        status=query.status,
        current_stage=None,
        progress_percent=100.0 if query.status == "completed" else None,
        started_at=query.started_at,
        completed_at=query.completed_at,
        estimated_completion_ms=None,
        result=result,
        error=None,
    )

    logger.info(f"[{trace_id}] Status: {query_status.status} (from database)")
    return query_status


@router.get(
    "/history/{user_id}",
    response_model=QueryHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Query History",
    description="""
Retrieve paginated query history for a user.

Returns a list of past queries with:
- Query text
- Timestamp
- User rating (if provided)
- Answer confidence

Supports pagination via `limit` and `offset` query parameters.
    """,
    responses={
        200: {
            "description": "Query history retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "queries": [
                            {
                                "trace_id": "QRY-20250105-abc123",
                                "query_text": "È valido un contratto...",
                                "timestamp": "2025-01-05T14:30:22Z",
                                "rating": 4,
                                "answered": True
                            }
                        ],
                        "total": 127,
                        "limit": 50,
                        "offset": 0
                    }
                }
            }
        },
        404: {"description": "User not found"}
    }
)
async def get_query_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    since: Optional[str] = None,
    api_key: ApiKey = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit)
) -> QueryHistoryResponse:
    """
    Get query history for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of results (default: 50)
        offset: Pagination offset (default: 0)
        since: ISO date filter (optional)
        api_key: Verified API key (injected by auth middleware)
        _rate_limit: Rate limit check (injected by rate limit middleware)

    Returns:
        QueryHistoryResponse with paginated query list

    Raises:
        HTTPException: 401 for auth, 404 if user not found, 429 for rate limit
    """
    logger.info(f"Query history request for user_id={user_id}, limit={limit}, offset={offset}")

    # Get query history from database
    queries, total = await persistence_service.get_query_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    # Build QueryHistoryItem list
    history_items = []
    for query in queries:
        # Get query result for confidence (if completed)
        confidence = None
        if query.status == "completed":
            query_result = await persistence_service.get_query_result(query.trace_id)
            if query_result:
                confidence = float(query_result.confidence)

        # Get user feedback rating (if any)
        rating = None
        user_feedbacks = await persistence_service.get_user_feedback_by_trace(query.trace_id)
        if user_feedbacks:
            # Take most recent rating
            rating = user_feedbacks[-1].rating

        history_items.append(
            QueryHistoryItem(
                trace_id=query.trace_id,
                query_text=query.query_text[:100] + "..." if len(query.query_text) > 100 else query.query_text,
                timestamp=query.created_at,
                rating=rating,
                answered=(query.status == "completed"),
                confidence=confidence,
            )
        )

    # Build response
    response = QueryHistoryResponse(
        queries=history_items,
        total=total,
        limit=limit,
        offset=offset,
        user_id=user_id,
    )

    logger.info(f"Returning {len(history_items)} queries (total: {total}) for user_id={user_id}")
    return response


@router.get(
    "/retrieve/{trace_id}",
    response_model=QueryRetrieveResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Query",
    description="""
Retrieve complete details for a past query by trace ID.

Returns:
- Full answer with legal basis
- Execution trace (if available)
- All submitted feedback

Useful for:
- Reviewing past queries
- Analyzing feedback
- Debugging query execution
    """,
    responses={
        200: {
            "description": "Query retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "trace_id": "QRY-20250105-abc123",
                        "query": "È valido un contratto...",
                        "answer": {"primary_answer": "...", "confidence": 0.87},
                        "feedback": [{"type": "user", "rating": 4}]
                    }
                }
            }
        },
        404: {"description": "Query not found"}
    }
)
async def retrieve_query(
    trace_id: str,
    api_key: ApiKey = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit)
) -> QueryRetrieveResponse:
    """
    Retrieve complete query details by trace ID.

    Args:
        trace_id: Unique query trace identifier
        api_key: Verified API key (injected by auth middleware)
        _rate_limit: Rate limit check (injected by rate limit middleware)

    Returns:
        QueryRetrieveResponse with full query details

    Raises:
        HTTPException: 401 for auth, 404 if trace_id not found, 429 for rate limit
    """
    logger.info(f"Query retrieve request for trace_id={trace_id}")

    # Get query from database
    query = await persistence_service.get_query(trace_id)
    if not query:
        logger.warning(f"Trace ID not found: {trace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with trace_id '{trace_id}' not found."
        )

    # Get query result
    query_result = await persistence_service.get_query_result(trace_id)
    if not query_result:
        logger.warning(f"Query result not found for trace_id={trace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query result not found for trace_id '{trace_id}'."
        )

    # Fetch feedback from stores
    user_feedbacks = await persistence_service.get_user_feedback_by_trace(trace_id)
    feedback_list = [
        {
            "feedback_type": "user",
            "rating": fb.rating,
            "text": fb.feedback_text,
            "timestamp": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb in user_feedbacks
    ]

    # Reconstruct Answer object
    from ..schemas.query import Answer
    answer = Answer(
        primary_answer=query_result.primary_answer,
        confidence=float(query_result.confidence),
        legal_basis=[],  # TODO: Reconstruct LegalBasis objects from JSON
        jurisprudence=None,
        alternative_interpretations=None,
        uncertainty_preserved=query_result.uncertainty_preserved,
        consensus_level=None,
    )

    # Build response
    response = QueryRetrieveResponse(
        trace_id=query.trace_id,
        query=query.query_text,
        answer=answer,
        execution_trace=query_result.execution_trace,
        metadata=query_result.query_metadata,
        feedback=feedback_list,
        timestamp=query.created_at,
    )

    logger.info(f"[{trace_id}] Query retrieved successfully")
    return response


# TODO: Future endpoint for Phase 3
# @router.post("/stream")  # SSE streaming (optional)
