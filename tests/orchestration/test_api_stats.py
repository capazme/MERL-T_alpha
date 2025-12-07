"""
Tests for Statistics API endpoints.

Tests:
- GET /stats/pipeline
- GET /stats/feedback
- GET /health
- GET /
"""

import pytest

from merlt.orchestration.api.main import app
from fastapi.testclient import TestClient

# Test client
client = TestClient(app)


# ============================================================================
# GET /stats/pipeline TESTS
# ============================================================================

def test_get_pipeline_stats_default_period():
    """Test pipeline stats retrieval with default period."""
    response = client.get("/stats/pipeline")

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert "period" in data
    assert "queries_total" in data
    assert "avg_response_time_ms" in data
    assert "p95_response_time_ms" in data
    assert "success_rate" in data
    assert "stages_performance" in data
    assert "avg_iterations" in data
    assert "expert_usage" in data

    # Validate data types and ranges
    assert data["queries_total"] >= 0
    assert data["avg_response_time_ms"] >= 0.0
    assert data["p95_response_time_ms"] >= 0.0
    assert 0.0 <= data["success_rate"] <= 1.0
    assert data["avg_iterations"] >= 1.0


def test_get_pipeline_stats_custom_period():
    """Test pipeline stats with custom period."""
    response = client.get("/stats/pipeline?period=last_30_days")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "last_30_days"


def test_pipeline_stats_stages_performance():
    """Test pipeline stats include all stage performance metrics."""
    response = client.get("/stats/pipeline")

    assert response.status_code == 200
    data = response.json()
    stages = data["stages_performance"]

    # Check all expected stages
    expected_stages = [
        "query_understanding",
        "kg_enrichment",
        "router",
        "retrieval",
        "experts",
        "synthesis"
    ]

    for stage in expected_stages:
        assert stage in stages
        assert "avg_ms" in stages[stage]
        assert "p95_ms" in stages[stage]
        assert "count" in stages[stage]


def test_pipeline_stats_expert_usage():
    """Test pipeline stats include expert usage rates."""
    response = client.get("/stats/pipeline")

    assert response.status_code == 200
    data = response.json()
    expert_usage = data["expert_usage"]

    # Check all 4 experts
    expected_experts = [
        "literal_interpreter",
        "systemic_teleological",
        "principles_balancer",
        "precedent_analyst"
    ]

    for expert in expected_experts:
        assert expert in expert_usage
        assert 0.0 <= expert_usage[expert] <= 1.0


# ============================================================================
# GET /stats/feedback TESTS
# ============================================================================

def test_get_feedback_stats_default_period():
    """Test feedback stats retrieval with default period."""
    response = client.get("/stats/feedback")

    assert response.status_code == 200
    data = response.json()

    # Check all required fields
    assert "period" in data
    assert "user_feedback_count" in data
    assert "avg_user_rating" in data
    assert "rlcf_expert_feedback_count" in data
    assert "ner_corrections_count" in data

    # Validate data types and ranges
    assert data["user_feedback_count"] >= 0
    assert data["rlcf_expert_feedback_count"] >= 0
    assert data["ner_corrections_count"] >= 0


def test_get_feedback_stats_custom_period():
    """Test feedback stats with custom period."""
    response = client.get("/stats/feedback?period=last_7_days")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "last_7_days"


def test_feedback_stats_model_improvements():
    """Test feedback stats include model improvements."""
    response = client.get("/stats/feedback")

    assert response.status_code == 200
    data = response.json()

    if data.get("model_improvements"):
        improvements = data["model_improvements"]
        for metric_name, metric_data in improvements.items():
            assert "before" in metric_data
            assert "after" in metric_data
            assert "improvement" in metric_data
            assert 0.0 <= metric_data["before"] <= 1.0
            assert 0.0 <= metric_data["after"] <= 1.0


def test_feedback_stats_retraining_events():
    """Test feedback stats include retraining events."""
    response = client.get("/stats/feedback")

    assert response.status_code == 200
    data = response.json()

    if data.get("retraining_events"):
        events = data["retraining_events"]
        assert isinstance(events, list)

        for event in events:
            assert "model" in event
            assert "version" in event
            assert "date" in event
            assert "improvements" in event


def test_feedback_stats_distribution():
    """Test feedback stats include rating distribution."""
    response = client.get("/stats/feedback")

    assert response.status_code == 200
    data = response.json()

    if data.get("feedback_distribution"):
        distribution = data["feedback_distribution"]
        # Should have ratings 1-5
        for rating in ["1", "2", "3", "4", "5"]:
            if rating in distribution:
                assert distribution[rating] >= 0


# ============================================================================
# GET /health TESTS
# ============================================================================

def test_health_check():
    """Test system health check."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "components" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_health_check_components():
    """Test health check includes all component statuses."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    components = data["components"]

    # Check expected components
    expected_components = [
        "query_understanding",
        "kg_enrichment",
        "router",
        "kg_agent",
        "api_agent",
        "vectordb_agent",
        "experts",
        "synthesizer"
    ]

    for component in expected_components:
        assert component in components
        assert "status" in components[component]
        assert components[component]["status"] in ["healthy", "degraded", "unhealthy"]


def test_health_check_version():
    """Test health check returns correct version."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v0.2.0"


# ============================================================================
# GET / (ROOT) TESTS
# ============================================================================

def test_root_endpoint():
    """Test API root endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "message" in data
    assert "version" in data
    assert "documentation" in data
    assert "status" in data

    # Check values
    assert data["version"] == "0.2.0"
    assert data["documentation"] == "/docs"
    assert data["status"] == "operational"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_api_docs_available():
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")

    assert response.status_code == 200


def test_api_redoc_available():
    """Test that ReDoc is available."""
    response = client.get("/redoc")

    assert response.status_code == 200


def test_api_openapi_schema():
    """Test that OpenAPI schema is available."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()

    # Check OpenAPI structure
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data

    # Check API metadata
    assert data["info"]["title"] == "MERL-T API"
    assert data["info"]["version"] == "0.2.0"
