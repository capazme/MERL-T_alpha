"""
Tests for Feedback API endpoints.

Tests:
- POST /feedback/user
- POST /feedback/rlcf
- POST /feedback/ner
- GET /feedback/stats
"""

import pytest
from datetime import datetime

from backend.orchestration.api.main import app
from fastapi.testclient import TestClient

# Test client
client = TestClient(app)


# ============================================================================
# POST /feedback/user TESTS
# ============================================================================

def test_submit_user_feedback_success():
    """Test successful user feedback submission."""
    response = client.post(
        "/feedback/user",
        json={
            "trace_id": "QRY-TEST-123",
            "user_id": "user_test",
            "rating": 4,
            "feedback_text": "Risposta utile",
            "categories": {
                "accuracy": 4,
                "completeness": 4,
                "clarity": 5,
                "legal_soundness": 4
            }
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["trace_id"] == "QRY-TEST-123"
    assert "feedback_id" in data


def test_submit_user_feedback_invalid_rating():
    """Test user feedback with invalid rating."""
    response = client.post(
        "/feedback/user",
        json={
            "trace_id": "QRY-TEST-123",
            "rating": 6,  # Invalid: should be 1-5
        }
    )

    assert response.status_code == 422  # Validation error


def test_submit_user_feedback_minimal():
    """Test user feedback with minimal required fields."""
    response = client.post(
        "/feedback/user",
        json={
            "trace_id": "QRY-TEST-123",
            "rating": 3,
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"


# ============================================================================
# POST /feedback/rlcf TESTS
# ============================================================================

def test_submit_rlcf_feedback_success():
    """Test successful RLCF feedback submission."""
    response = client.post(
        "/feedback/rlcf",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "authority_score": 0.85,
            "corrections": {
                "concept_mapping": {
                    "issue": "Missing concept: emancipazione",
                    "correction": {
                        "action": "add_concept",
                        "concept_id": "emancipazione"
                    }
                },
                "answer_quality": {
                    "validated_answer": "Corrected answer",
                    "position": "partially_correct",
                    "reasoning": "Incomplete reasoning",
                    "missing_norms": ["cc-art-390"]
                }
            },
            "overall_rating": 3
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["authority_weight"] == 0.85
    assert data["training_examples_generated"] >= 2  # concept_mapping + answer_quality


def test_submit_rlcf_feedback_invalid_authority():
    """Test RLCF feedback with invalid authority score."""
    response = client.post(
        "/feedback/rlcf",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "authority_score": 1.5,  # Invalid: should be 0-1
            "corrections": {},
            "overall_rating": 3
        }
    )

    assert response.status_code == 422  # Validation error


def test_submit_rlcf_feedback_routing_correction():
    """Test RLCF feedback with routing decision correction."""
    response = client.post(
        "/feedback/rlcf",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "authority_score": 0.90,
            "corrections": {
                "routing_decision": {
                    "issue": "Should have activated Precedent_Analyst",
                    "improved_plan": {
                        "experts": ["literal_interpreter", "precedent_analyst"]
                    }
                }
            },
            "overall_rating": 4
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["training_examples_generated"] >= 1


# ============================================================================
# POST /feedback/ner TESTS
# ============================================================================

def test_submit_ner_correction_missing_entity():
    """Test NER correction for MISSING_ENTITY."""
    response = client.post(
        "/feedback/ner",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "correction_type": "MISSING_ENTITY",
            "correction": {
                "text_span": "sedicenne",
                "start_char": 37,
                "end_char": 46,
                "correct_label": "PERSON",
                "incorrect_label": None,
                "attributes": {"age": 16}
            }
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "accepted"
    assert data["training_examples_generated"] == 1


def test_submit_ner_correction_wrong_type():
    """Test NER correction for WRONG_TYPE."""
    response = client.post(
        "/feedback/ner",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "correction_type": "WRONG_TYPE",
            "correction": {
                "text_span": "Milano",
                "start_char": 10,
                "end_char": 16,
                "correct_label": "GPE",
                "incorrect_label": "ORG"
            }
        }
    )

    assert response.status_code == 201


def test_submit_ner_correction_invalid_type():
    """Test NER correction with invalid correction_type."""
    response = client.post(
        "/feedback/ner",
        json={
            "trace_id": "QRY-TEST-123",
            "expert_id": "expert_456",
            "correction_type": "INVALID_TYPE",  # Invalid
            "correction": {
                "text_span": "test",
                "start_char": 0,
                "end_char": 4,
                "correct_label": "TEST"
            }
        }
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# GET /feedback/stats TESTS
# ============================================================================

def test_get_feedback_stats():
    """Test feedback statistics retrieval."""
    response = client.get("/feedback/stats")

    assert response.status_code == 200
    data = response.json()
    assert "user_feedback_count" in data
    assert "rlcf_feedback_count" in data
    assert "ner_corrections_count" in data
    assert "rlcf_retrain_threshold" in data
    assert "ner_retrain_threshold" in data


def test_feedback_stats_after_submissions():
    """Test feedback stats reflect submitted feedback."""
    # Submit user feedback
    client.post(
        "/feedback/user",
        json={"trace_id": "QRY-TEST-123", "rating": 5}
    )

    # Check stats
    response = client.get("/feedback/stats")
    data = response.json()

    assert data["user_feedback_count"] >= 1
