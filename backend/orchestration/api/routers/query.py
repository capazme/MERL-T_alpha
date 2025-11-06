"""
Query Router

FastAPI router for query execution endpoints.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryStatus,
    QueryHistoryResponse,
    QueryHistoryItem,
    QueryRetrieveResponse,
)
from ..services.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["Query Execution"]
)

# Global QueryExecutor instance (singleton pattern)
query_executor = QueryExecutor()

# In-memory cache for query status (TODO: Replace with Redis/PostgreSQL persistence)
_query_status_cache = {}


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
    """,
    responses={
        200: {
            "description": "Query executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "trace_id": "QRY-20250105-abc123",
                        "answer": {
                            "primary_answer": "Un contratto firmato da un minorenne è annullabile...",
                            "confidence": 0.87,
                            "legal_basis": [{"norm_id": "cc-art-2", "relevance": 0.95}]
                        },
                        "metadata": {
                            "complexity_score": 0.68,
                            "intent_detected": "validità_atto"
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid query request"},
        408: {"description": "Query execution timeout"},
        500: {"description": "Internal server error"}
    }
)
async def execute_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a legal query through the complete MERL-T pipeline.

    Args:
        request: QueryRequest with query text, context, and options

    Returns:
        QueryResponse with answer, trace, and metadata

    Raises:
        HTTPException: 400 for invalid request, 408 for timeout, 500 for errors
    """
    try:
        logger.info(f"Received query: {request.query[:100]}...")

        # Execute query via QueryExecutor
        response = await query_executor.execute_query(request)

        # Cache status (for GET /query/status endpoint)
        _query_status_cache[response.trace_id] = {
            "trace_id": response.trace_id,
            "status": "completed",
            "result": response,
            "started_at": response.timestamp,
            "completed_at": response.timestamp,
        }

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
async def get_query_status(trace_id: str) -> QueryStatus:
    """
    Get execution status for a query by trace ID.

    Args:
        trace_id: Unique query trace identifier

    Returns:
        QueryStatus with current status and result (if completed)

    Raises:
        HTTPException: 404 if trace_id not found
    """
    logger.info(f"Status request for trace_id: {trace_id}")

    # Check in-memory cache (TODO: Replace with Redis/PostgreSQL)
    if trace_id not in _query_status_cache:
        logger.warning(f"Trace ID not found: {trace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with trace_id '{trace_id}' not found. It may have expired or never existed."
        )

    cached_status = _query_status_cache[trace_id]

    # Build QueryStatus response
    query_status = QueryStatus(
        trace_id=cached_status["trace_id"],
        status=cached_status["status"],
        current_stage=cached_status.get("current_stage"),
        progress_percent=100.0 if cached_status["status"] == "completed" else None,
        started_at=cached_status["started_at"],
        completed_at=cached_status.get("completed_at"),
        estimated_completion_ms=None,
        result=cached_status.get("result"),
        error=cached_status.get("error"),
    )

    logger.info(f"[{trace_id}] Status: {query_status.status}")
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
    since: Optional[str] = None
) -> QueryHistoryResponse:
    """
    Get query history for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of results (default: 50)
        offset: Pagination offset (default: 0)
        since: ISO date filter (optional)

    Returns:
        QueryHistoryResponse with paginated query list

    Raises:
        HTTPException: 404 if user not found
    """
    logger.info(f"Query history request for user_id={user_id}, limit={limit}, offset={offset}")

    # TODO: Query PostgreSQL for user's query history
    # For now, return mock data from in-memory cache

    # Filter queries for this user
    user_queries = [
        query_data for query_data in _query_status_cache.values()
        if query_data.get("result") and query_data["result"].session_id == user_id
    ]

    # Apply date filter if provided
    if since:
        from datetime import datetime as dt
        since_date = dt.fromisoformat(since.replace('Z', '+00:00'))
        user_queries = [
            q for q in user_queries
            if q["started_at"] >= since_date
        ]

    # Sort by timestamp descending (most recent first)
    user_queries.sort(key=lambda q: q["started_at"], reverse=True)

    # Get total count before pagination
    total = len(user_queries)

    # Apply pagination
    paginated_queries = user_queries[offset:offset + limit]

    # Build QueryHistoryItem list
    history_items = []
    for query_data in paginated_queries:
        result: QueryResponse = query_data["result"]
        history_items.append(
            QueryHistoryItem(
                trace_id=result.trace_id,
                query_text=result.answer.primary_answer[:100] + "...",  # Truncate for history
                timestamp=result.timestamp,
                rating=None,  # TODO: Fetch from feedback store
                answered=True,
                confidence=result.answer.confidence,
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
async def retrieve_query(trace_id: str) -> QueryRetrieveResponse:
    """
    Retrieve complete query details by trace ID.

    Args:
        trace_id: Unique query trace identifier

    Returns:
        QueryRetrieveResponse with full query details

    Raises:
        HTTPException: 404 if trace_id not found
    """
    logger.info(f"Query retrieve request for trace_id={trace_id}")

    # Check in-memory cache (TODO: Replace with PostgreSQL)
    if trace_id not in _query_status_cache:
        logger.warning(f"Trace ID not found: {trace_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query with trace_id '{trace_id}' not found."
        )

    cached_query = _query_status_cache[trace_id]
    result: QueryResponse = cached_query["result"]

    # TODO: Fetch feedback from feedback stores
    feedback_list = []

    # Build response
    response = QueryRetrieveResponse(
        trace_id=result.trace_id,
        query=result.answer.primary_answer[:100] + "...",  # TODO: Store original query
        answer=result.answer,
        execution_trace=result.execution_trace,
        metadata=result.metadata,
        feedback=feedback_list,
        timestamp=result.timestamp,
    )

    logger.info(f"[{trace_id}] Query retrieved successfully")
    return response


# TODO: Future endpoint for Phase 3
# @router.post("/stream")  # SSE streaming (optional)
