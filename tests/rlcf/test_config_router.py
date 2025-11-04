"""
Tests for the Configuration Management API endpoints.

This module tests the FastAPI router for dynamic configuration management,
including:
- Task configuration CRUD operations
- Model configuration retrieval
- Backup and restore functionality
- Authentication and authorization
- Request/response validation
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.rlcf_framework.main import app
from backend.rlcf_framework.config_manager import ConfigManager


# Test client fixture
@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """Create headers with admin API key for authenticated requests."""
    # Using the default API key that matches auth.py
    import os
    api_key = os.getenv("ADMIN_API_KEY", "supersecretkey")
    return {"X-API-Key": api_key}


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestGetTaskConfiguration:
    """Test cases for GET /config/task endpoint."""

    def test_get_task_configuration_success(self, client):
        """Test successfully retrieving task configuration."""
        response = client.get("/config/task")

        assert response.status_code == 200
        data = response.json()

        # Should have task_types key
        assert "task_types" in data
        assert isinstance(data["task_types"], dict)

        # Should have at least the official RLCF task types
        assert len(data["task_types"]) >= 10  # We have 11 official types

    def test_get_task_configuration_format(self, client):
        """Test that task configuration has correct format."""
        response = client.get("/config/task")

        assert response.status_code == 200
        data = response.json()

        # Pick a task type and verify structure
        task_types = data["task_types"]
        if "QA" in task_types:
            qa_config = task_types["QA"]
            assert "input_data" in qa_config
            assert "feedback_data" in qa_config
            assert isinstance(qa_config["input_data"], dict)
            assert isinstance(qa_config["feedback_data"], dict)


class TestGetModelConfiguration:
    """Test cases for GET /config/model endpoint."""

    def test_get_model_configuration_success(self, client):
        """Test successfully retrieving model configuration."""
        response = client.get("/config/model")

        assert response.status_code == 200
        data = response.json()

        # Should have key configuration sections
        assert "authority_weights" in data
        assert "baseline_credentials" in data
        assert "thresholds" in data

    def test_get_model_configuration_format(self, client):
        """Test that model configuration has correct format."""
        response = client.get("/config/model")

        assert response.status_code == 200
        data = response.json()

        # Authority weights should be a dict with specific keys
        authority_weights = data["authority_weights"]
        assert isinstance(authority_weights, dict)
        assert "baseline_credentials" in authority_weights
        assert "track_record" in authority_weights
        assert "recent_performance" in authority_weights


class TestCreateTaskType:
    """Test cases for POST /config/task/type endpoint."""

    def test_create_task_type_success(self, client, admin_headers, temp_config_dir):
        """Test successfully creating a new task type."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create initial config
        initial_data = {"task_types": {"EXISTING_TASK": {"input_data": {"test": "str"}}}}
        with open(temp_config_file, 'w') as f:
            yaml.dump(initial_data, f)

        manager._task_config_path = temp_config_file

        try:
            # Create new task type
            request_data = {
                "task_type_name": "NEW_LEGAL_ANALYSIS",
                "schema": {
                    "input_data": {"case_text": "str", "jurisdiction": "str"},
                    "feedback_data": {"analysis": "str", "confidence": "float"},
                    "ground_truth_keys": ["analysis"]
                }
            }

            response = client.post(
                "/config/task/type",
                json=request_data,
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["task_type_name"] == "NEW_LEGAL_ANALYSIS"
            assert "created successfully" in data["message"].lower()

        finally:
            manager._task_config_path = original_task_config_path

    def test_create_task_type_without_auth(self, client):
        """Test creating task type without authentication fails."""
        request_data = {
            "task_type_name": "UNAUTHORIZED_TASK",
            "schema": {
                "input_data": {"test": "str"},
                "feedback_data": {"result": "str"}
            }
        }

        response = client.post("/config/task/type", json=request_data)

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_create_duplicate_task_type(self, client, admin_headers, temp_config_dir):
        """Test creating a task type that already exists."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create config with existing task
        initial_data = {"task_types": {"DUPLICATE_TASK": {"input_data": {"test": "str"}}}}
        with open(temp_config_file, 'w') as f:
            yaml.dump(initial_data, f)

        manager._task_config_path = temp_config_file

        try:
            # Try to create duplicate
            request_data = {
                "task_type_name": "DUPLICATE_TASK",
                "schema": {
                    "input_data": {"new": "str"},
                    "feedback_data": {"result": "str"}
                }
            }

            response = client.post(
                "/config/task/type",
                json=request_data,
                headers=admin_headers
            )

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "already exists" in data["message"].lower()

        finally:
            manager._task_config_path = original_task_config_path

    def test_create_task_type_invalid_schema(self, client, admin_headers):
        """Test creating task type with invalid schema."""
        request_data = {
            "task_type_name": "INVALID_TASK",
            "schema": {
                # Missing required fields
                "input_data": {}
            }
        }

        response = client.post(
            "/config/task/type",
            json=request_data,
            headers=admin_headers
        )

        # Should return validation error
        assert response.status_code == 422  # Pydantic validation error


class TestUpdateTaskType:
    """Test cases for PUT /config/task/type/{name} endpoint."""

    def test_update_task_type_success(self, client, admin_headers, temp_config_dir):
        """Test successfully updating an existing task type."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create config with existing task
        initial_data = {
            "task_types": {
                "UPDATE_ME_TASK": {
                    "input_data": {"old_field": "str"},
                    "feedback_data": {"old_feedback": "str"}
                }
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(initial_data, f)

        manager._task_config_path = temp_config_file

        try:
            # Update task type
            request_data = {
                "schema": {
                    "input_data": {"new_field": "str", "context": "str"},
                    "feedback_data": {"new_feedback": "str", "score": "float"},
                    "ground_truth_keys": ["new_feedback"]
                }
            }

            response = client.put(
                "/config/task/type/UPDATE_ME_TASK",
                json=request_data,
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "updated successfully" in data["message"].lower()

        finally:
            manager._task_config_path = original_task_config_path

    def test_update_nonexistent_task_type(self, client, admin_headers):
        """Test updating a task type that doesn't exist."""
        request_data = {
            "schema": {
                "input_data": {"test": "str"},
                "feedback_data": {"result": "str"}
            }
        }

        response = client.put(
            "/config/task/type/NONEXISTENT_TASK_12345",
            json=request_data,
            headers=admin_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False


class TestDeleteTaskType:
    """Test cases for DELETE /config/task/type/{name} endpoint."""

    def test_delete_task_type_success(self, client, admin_headers, temp_config_dir):
        """Test successfully deleting a task type."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create config with task to delete
        initial_data = {
            "task_types": {
                "DELETE_ME_TASK": {"input_data": {"test": "str"}},
                "KEEP_ME_TASK": {"input_data": {"keep": "str"}}
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(initial_data, f)

        manager._task_config_path = temp_config_file

        try:
            # Delete task type
            response = client.delete(
                "/config/task/type/DELETE_ME_TASK",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "deleted successfully" in data["message"].lower()

            # Verify task was actually deleted
            with open(temp_config_file, 'r') as f:
                updated_data = yaml.safe_load(f)

            assert "DELETE_ME_TASK" not in updated_data["task_types"]
            assert "KEEP_ME_TASK" in updated_data["task_types"]

        finally:
            manager._task_config_path = original_task_config_path

    def test_delete_nonexistent_task_type(self, client, admin_headers):
        """Test deleting a task type that doesn't exist."""
        response = client.delete(
            "/config/task/type/NONEXISTENT_TASK_12345",
            headers=admin_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_delete_task_type_without_auth(self, client):
        """Test deleting task type without authentication fails."""
        response = client.delete("/config/task/type/SOME_TASK")

        # Should require authentication
        assert response.status_code in [401, 403]


class TestListTaskTypes:
    """Test cases for GET /config/task/types endpoint."""

    def test_list_task_types_success(self, client):
        """Test successfully listing all task types."""
        response = client.get("/config/task/types")

        assert response.status_code == 200
        data = response.json()

        assert "task_types" in data
        assert isinstance(data["task_types"], list)
        assert len(data["task_types"]) >= 10  # Official RLCF types

        # Each task type should have name and schema
        for task_type in data["task_types"]:
            assert "name" in task_type
            assert "schema" in task_type


class TestBackupManagement:
    """Test cases for backup management endpoints."""

    def test_list_backups_success(self, client, admin_headers):
        """Test successfully listing backups."""
        response = client.get("/config/backups", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()

        assert "backups" in data
        assert "total_count" in data
        assert isinstance(data["backups"], list)
        assert data["total_count"] == len(data["backups"])

        # Each backup should have required fields
        for backup in data["backups"]:
            assert "filename" in backup
            assert "type" in backup
            assert "timestamp" in backup
            assert "size_bytes" in backup
            assert "formatted_date" in backup

    def test_list_backups_without_auth(self, client):
        """Test listing backups without authentication fails."""
        response = client.get("/config/backups")

        # Should require authentication
        assert response.status_code in [401, 403]

    def test_restore_backup_success(self, client, admin_headers, temp_config_dir):
        """Test successfully restoring from a backup."""
        manager = ConfigManager.get_instance()

        # Override directories for testing
        original_backup_dir = manager._backup_dir
        original_task_config_path = manager._task_config_path

        # Create temporary config file
        temp_config_file = temp_config_dir / "task_config.yaml"
        original_data = {"task_types": {"ORIGINAL_TASK": {"input_data": {"test": "str"}}}}

        with open(temp_config_file, 'w') as f:
            yaml.dump(original_data, f)

        manager._backup_dir = temp_config_dir / "backups"
        manager._backup_dir.mkdir(exist_ok=True)
        manager._task_config_path = temp_config_file

        try:
            # Create a backup
            backup_path = manager._create_backup("task")
            backup_filename = backup_path.name

            # Modify the config file
            modified_data = {"task_types": {"MODIFIED_TASK": {"input_data": {"modified": "str"}}}}
            with open(temp_config_file, 'w') as f:
                yaml.dump(modified_data, f)

            # Restore from backup via API
            request_data = {"backup_filename": backup_filename}
            response = client.post(
                "/config/backups/restore",
                json=request_data,
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "restored successfully" in data["message"].lower()

        finally:
            manager._backup_dir = original_backup_dir
            manager._task_config_path = original_task_config_path

    def test_restore_nonexistent_backup(self, client, admin_headers):
        """Test restoring from a non-existent backup."""
        request_data = {"backup_filename": "nonexistent_backup_12345.yaml"}
        response = client.post(
            "/config/backups/restore",
            json=request_data,
            headers=admin_headers
        )

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()


class TestConfigurationStatus:
    """Test cases for GET /config/status endpoint."""

    def test_get_status_success(self, client):
        """Test successfully retrieving configuration status."""
        response = client.get("/config/status")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "config_files" in data

        # Config files should include model and task configs
        config_files = data["config_files"]
        assert "model_config" in config_files
        assert "task_config" in config_files

        # Each config file should have status info
        for config_name, config_info in config_files.items():
            assert "exists" in config_info
            assert "last_modified" in config_info

    def test_get_status_includes_task_type_count(self, client):
        """Test that status includes task type count."""
        response = client.get("/config/status")

        assert response.status_code == 200
        data = response.json()

        assert "task_types_count" in data
        assert isinstance(data["task_types_count"], int)
        assert data["task_types_count"] >= 10  # Official RLCF types


class TestValidationEndpoint:
    """Test cases for configuration validation endpoint."""

    def test_validate_task_config_valid(self, client, admin_headers):
        """Test validating a valid task configuration."""
        request_data = {
            "input_data": {"question": "str", "context": "str"},
            "feedback_data": {"answer": "str", "confidence": "float"},
            "ground_truth_keys": ["answer"]
        }

        response = client.post(
            "/config/task/validate",
            json=request_data,
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "errors" in data
        assert len(data["errors"]) == 0

    def test_validate_task_config_invalid(self, client, admin_headers):
        """Test validating an invalid task configuration."""
        request_data = {
            "input_data": {},  # Empty input_data is invalid
            "feedback_data": {"result": "str"}
        }

        response = client.post(
            "/config/task/validate",
            json=request_data,
            headers=admin_headers
        )

        # May return 422 for validation error or 200 with valid=False
        assert response.status_code in [200, 422]


class TestRateLimiting:
    """Test cases for rate limiting (if implemented)."""

    def test_multiple_rapid_requests(self, client):
        """Test that multiple rapid requests are handled correctly."""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/config/task")
            responses.append(response)

        # All requests should succeed (no rate limiting for reads in basic implementation)
        for response in responses:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
