"""
Tests for Query API endpoints.

Tests:
- POST /query/execute
- GET /query/status/{trace_id}
- GET /query/history/{user_id}
- GET /query/retrieve/{trace_id}
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from merlt.orchestration.api.main import app
from merlt.orchestration.api.schemas.query import (
    QueryRequest,
    QueryResponse,
    Answer,
    ExecutionTrace,
    AnswerMetadata,
)

from fastapi.testclient import TestClient

# Test client
client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_query_response():
    """Mock QueryResponse for testing."""
    return QueryResponse(
        trace_id="QRY-TEST-123",
        session_id="session_test",
        answer=Answer(
            primary_answer="Test legal answer",
            confidence=0.85,
            legal_basis=[],
            uncertainty_preserved=False,
        ),
        execution_trace=ExecutionTrace(
            trace_id="QRY-TEST-123",
            stages_executed=["router", "retrieval", "experts", "synthesis"],
            iterations=1,
            stop_reason="HIGH_CONFIDENCE_AND_CONSENSUS",
            experts_consulted=["literal_interpreter"],
            agents_used=["kg_agent"],
            total_time_ms=2500.0,
            errors=[],
        ),
        metadata=AnswerMetadata(
            complexity_score=0.6,
            intent_detected="test_intent",
            concepts_identified=["test_concept"],
            norms_consulted=3,
            jurisprudence_consulted=1,
        ),
        timestamp=datetime.utcnow(),
    )


# ============================================================================
# POST /query/execute TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_query_success(mock_query_response):
    """Test successful query execution."""
    with patch(
        "backend.orchestration.api.services.query_executor.QueryExecutor.execute_query",
        new_callable=AsyncMock,
        return_value=mock_query_response
    ):
        response = client.post(
            "/query/execute",
            json={
                "query": "Test query",
                "context": {"jurisdiction": "nazionale"},
                "options": {"max_iterations": 3, "return_trace": True}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == "QRY-TEST-123"
        assert data["answer"]["confidence"] == 0.85
        assert data["metadata"]["complexity_score"] == 0.6


def test_execute_query_invalid_request():
    """Test query execution with invalid request."""
    response = client.post(
        "/query/execute",
        json={
            "query": "Too short",  # Below min_length=10
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_execute_query_timeout():
    """Test query execution timeout."""
    with patch(
        "backend.orchestration.api.services.query_executor.QueryExecutor.execute_query",
        new_callable=AsyncMock,
        side_effect=TimeoutError("Query timeout")
    ):
        response = client.post(
            "/query/execute",
            json={
                "query": "Test query that will timeout",
                "options": {"timeout_ms": 1000}
            }
        )

        assert response.status_code == 408  # Timeout


# ============================================================================
# GET /query/status/{trace_id} TESTS
# ============================================================================

def test_get_query_status_success(mock_query_response):
    """Test successful query status retrieval."""
    # First execute a query to populate cache
    with patch(
        "backend.orchestration.api.services.query_executor.QueryExecutor.execute_query",
        new_callable=AsyncMock,
        return_value=mock_query_response
    ):
        exec_response = client.post(
            "/query/execute",
            json={"query": "Test query for status check"}
        )
        trace_id = exec_response.json()["trace_id"]

        # Now check status
        status_response = client.get(f"/query/status/{trace_id}")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["trace_id"] == trace_id
        assert status_data["status"] == "completed"


def test_get_query_status_not_found():
    """Test query status retrieval for non-existent trace_id."""
    response = client.get("/query/status/NONEXISTENT-TRACE-ID")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# GET /query/history/{user_id} TESTS
# ============================================================================

def test_get_query_history_success(mock_query_response):
    """Test successful query history retrieval."""
    # Execute a query to populate history
    mock_query_response.session_id = "user_test_123"

    with patch(
        "backend.orchestration.api.services.query_executor.QueryExecutor.execute_query",
        new_callable=AsyncMock,
        return_value=mock_query_response
    ):
        client.post(
            "/query/execute",
            json={
                "query": "Test query for history",
                "session_id": "user_test_123"
            }
        )

        # Get history
        history_response = client.get("/query/history/user_test_123")

        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["user_id"] == "user_test_123"
        assert "queries" in history_data
        assert history_data["total"] >= 0


def test_get_query_history_pagination():
    """Test query history pagination."""
    response = client.get("/query/history/user_test?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


# ============================================================================
# GET /query/retrieve/{trace_id} TESTS
# ============================================================================

def test_retrieve_query_success(mock_query_response):
    """Test successful query retrieval."""
    # Execute a query first
    with patch(
        "backend.orchestration.api.services.query_executor.QueryExecutor.execute_query",
        new_callable=AsyncMock,
        return_value=mock_query_response
    ):
        exec_response = client.post(
            "/query/execute",
            json={"query": "Test query for retrieval"}
        )
        trace_id = exec_response.json()["trace_id"]

        # Retrieve the query
        retrieve_response = client.get(f"/query/retrieve/{trace_id}")

        assert retrieve_response.status_code == 200
        retrieve_data = retrieve_response.json()
        assert retrieve_data["trace_id"] == trace_id
        assert "answer" in retrieve_data
        assert "metadata" in retrieve_data


def test_retrieve_query_not_found():
    """Test query retrieval for non-existent trace_id."""
    response = client.get("/query/retrieve/NONEXISTENT-TRACE-ID")

    assert response.status_code == 404
