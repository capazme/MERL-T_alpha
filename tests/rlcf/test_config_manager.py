"""
Tests for the ConfigManager module.

This module tests the dynamic configuration management system, including:
- Singleton pattern implementation
- Configuration loading and reloading
- Backup and restore functionality
- Thread-safety and concurrent access
- YAML file validation
"""

import pytest
import tempfile
import shutil
import yaml
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from watchdog.events import FileModifiedEvent

from merlt.rlcf_framework.config_manager import ConfigManager, ConfigFileHandler
from merlt.rlcf_framework.config import ModelConfig, TaskConfig


class TestConfigManagerSingleton:
    """Test cases for ConfigManager singleton pattern."""

    def test_singleton_instance(self):
        """Test that ConfigManager returns the same instance."""
        manager1 = ConfigManager.get_instance()
        manager2 = ConfigManager.get_instance()

        assert manager1 is manager2, "ConfigManager should return the same instance"

    def test_singleton_thread_safety(self):
        """Test that singleton initialization is thread-safe."""
        instances = []

        def get_instance():
            instances.append(ConfigManager.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances), \
            "All threads should get the same ConfigManager instance"


class TestConfigManagerLoading:
    """Test cases for configuration loading."""

    def test_get_model_config(self):
        """Test getting model configuration."""
        manager = ConfigManager.get_instance()
        model_config = manager.get_model_config()

        assert isinstance(model_config, ModelConfig)
        assert hasattr(model_config, 'authority_weights')
        assert hasattr(model_config, 'baseline_credentials')

    def test_get_task_config(self):
        """Test getting task configuration."""
        manager = ConfigManager.get_instance()
        task_config = manager.get_task_config()

        assert isinstance(task_config, TaskConfig)
        assert hasattr(task_config, 'task_types')
        assert len(task_config.task_types) > 0

    def test_reload_model_config(self):
        """Test reloading model configuration."""
        manager = ConfigManager.get_instance()

        # Get initial config
        initial_config = manager.get_model_config()

        # Reload should not fail
        manager._reload_model_config()

        # Config should still be valid
        reloaded_config = manager.get_model_config()
        assert isinstance(reloaded_config, ModelConfig)

    def test_reload_task_config(self):
        """Test reloading task configuration."""
        manager = ConfigManager.get_instance()

        # Get initial config
        initial_config = manager.get_task_config()

        # Reload should not fail
        manager._reload_task_config()

        # Config should still be valid
        reloaded_config = manager.get_task_config()
        assert isinstance(reloaded_config, TaskConfig)


class TestConfigManagerBackup:
    """Test cases for backup functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_create_backup_model_config(self, temp_config_dir):
        """Test creating a backup of model configuration."""
        manager = ConfigManager.get_instance()

        # Override backup directory for testing
        original_backup_dir = manager._backup_dir
        manager._backup_dir = temp_config_dir

        try:
            # Create backup using the actual file path
            backup_path = manager._create_backup(manager._model_config_path)

            assert backup_path is not None
            assert backup_path.exists()
            assert "model_config" in backup_path.name
            assert backup_path.suffix == ".yaml"
        finally:
            manager._backup_dir = original_backup_dir

    def test_create_backup_task_config(self, temp_config_dir):
        """Test creating a backup of task configuration."""
        manager = ConfigManager.get_instance()

        # Override backup directory for testing
        original_backup_dir = manager._backup_dir
        manager._backup_dir = temp_config_dir

        try:
            # Create backup using the actual file path
            backup_path = manager._create_backup(manager._task_config_path)

            assert backup_path is not None
            assert backup_path.exists()
            assert "task_config" in backup_path.name
            assert backup_path.suffix == ".yaml"
        finally:
            manager._backup_dir = original_backup_dir

    def test_list_backups(self, temp_config_dir):
        """Test listing available backups."""
        manager = ConfigManager.get_instance()

        # Override backup directory for testing
        original_backup_dir = manager._backup_dir
        manager._backup_dir = temp_config_dir

        try:
            # Create some backups using actual file paths
            manager._create_backup(manager._model_config_path)
            manager._create_backup(manager._task_config_path)

            # List backups
            backups = manager.list_backups()

            assert len(backups) == 2
            assert any("model_config" in b["filename"] for b in backups)
            assert any("task_config" in b["filename"] for b in backups)

            for backup in backups:
                assert "filename" in backup
                assert "type" in backup
                assert "timestamp" in backup
                assert "size_bytes" in backup
        finally:
            manager._backup_dir = original_backup_dir

    def test_restore_backup(self, temp_config_dir):
        """Test restoring from a backup."""
        manager = ConfigManager.get_instance()

        # Override directories for testing
        original_backup_dir = manager._backup_dir
        original_task_config_path = manager._task_config_path

        # Create temporary config file
        temp_config_file = temp_config_dir / "task_config.yaml"
        original_data = {"task_types": {"TEST_TASK": {"input_data": {"test": "str"}}}}

        with open(temp_config_file, 'w') as f:
            yaml.dump(original_data, f)

        manager._backup_dir = temp_config_dir / "backups"
        manager._backup_dir.mkdir(exist_ok=True)
        manager._task_config_path = temp_config_file

        try:
            # Create a backup using the temp config file path
            backup_path = manager._create_backup(temp_config_file)
            backup_filename = backup_path.name

            # Modify the config file
            modified_data = {"task_types": {"MODIFIED_TASK": {"input_data": {"modified": "str"}}}}
            with open(temp_config_file, 'w') as f:
                yaml.dump(modified_data, f)

            # Restore from backup
            success, error = manager.restore_backup(backup_filename)

            assert success is True
            assert error is None

            # Verify restored content
            with open(temp_config_file, 'r') as f:
                restored_data = yaml.safe_load(f)

            assert "TEST_TASK" in restored_data["task_types"]
            assert "MODIFIED_TASK" not in restored_data["task_types"]

        finally:
            manager._backup_dir = original_backup_dir
            manager._task_config_path = original_task_config_path

    def test_restore_nonexistent_backup(self):
        """Test restoring from a non-existent backup."""
        manager = ConfigManager.get_instance()

        success, error = manager.restore_backup("nonexistent_backup_12345.yaml")

        assert success is False
        assert error is not None
        assert "not found" in error.lower()


class TestConfigManagerTaskTypeManagement:
    """Test cases for task type management."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_add_task_type_success(self, temp_config_dir):
        """Test successfully adding a new task type."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create initial config
        initial_data = {"task_types": {"EXISTING_TASK": {"input_data": {"existing": "str"}}}}
        with open(temp_config_file, 'w') as f:
            yaml.dump(initial_data, f)

        manager._task_config_path = temp_config_file

        try:
            # Add new task type
            new_schema = {
                "input_data": {"query": "str", "context": "str"},
                "feedback_data": {"answer": "str", "confidence": "float"},
                "ground_truth_keys": ["answer"]
            }

            success, error = manager.add_task_type("NEW_CUSTOM_TASK", new_schema)

            assert success is True
            assert error is None

            # Verify task was added
            with open(temp_config_file, 'r') as f:
                updated_data = yaml.safe_load(f)

            assert "NEW_CUSTOM_TASK" in updated_data["task_types"]
            assert updated_data["task_types"]["NEW_CUSTOM_TASK"]["input_data"] == new_schema["input_data"]

        finally:
            manager._task_config_path = original_task_config_path

    def test_add_duplicate_task_type(self, temp_config_dir):
        """Test adding a task type that already exists."""
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
            # Try to add duplicate task
            new_schema = {"input_data": {"new": "str"}}
            success, error = manager.add_task_type("DUPLICATE_TASK", new_schema)

            assert success is False
            assert error is not None
            assert "already exists" in error.lower()

        finally:
            manager._task_config_path = original_task_config_path

    def test_update_task_type_success(self, temp_config_dir):
        """Test successfully updating an existing task type."""
        manager = ConfigManager.get_instance()

        # Override config path for testing
        original_task_config_path = manager._task_config_path
        temp_config_file = temp_config_dir / "task_config.yaml"

        # Create config with existing task
        initial_data = {
            "task_types": {
                "UPDATE_TEST_TASK": {
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
            updated_schema = {
                "input_data": {"new_field": "str", "additional_field": "int"},
                "feedback_data": {"new_feedback": "str"},
                "ground_truth_keys": ["new_feedback"]
            }

            success, error = manager.update_task_type("UPDATE_TEST_TASK", updated_schema)

            assert success is True
            assert error is None

            # Verify task was updated
            with open(temp_config_file, 'r') as f:
                updated_data = yaml.safe_load(f)

            task_config = updated_data["task_types"]["UPDATE_TEST_TASK"]
            assert "new_field" in task_config["input_data"]
            assert "old_field" not in task_config["input_data"]

        finally:
            manager._task_config_path = original_task_config_path

    def test_delete_task_type_success(self, temp_config_dir):
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
            success, error = manager.delete_task_type("DELETE_ME_TASK")

            assert success is True
            assert error is None

            # Verify task was deleted
            with open(temp_config_file, 'r') as f:
                updated_data = yaml.safe_load(f)

            assert "DELETE_ME_TASK" not in updated_data["task_types"]
            assert "KEEP_ME_TASK" in updated_data["task_types"]

        finally:
            manager._task_config_path = original_task_config_path

    def test_delete_nonexistent_task_type(self):
        """Test deleting a task type that doesn't exist."""
        manager = ConfigManager.get_instance()

        success, error = manager.delete_task_type("NONEXISTENT_TASK_12345")

        assert success is False
        assert error is not None
        assert "does not exist" in error.lower() or "not found" in error.lower()


class TestConfigManagerThreadSafety:
    """Test cases for thread-safety."""

    def test_concurrent_reads(self):
        """Test concurrent read access to configurations."""
        manager = ConfigManager.get_instance()
        results = []
        errors = []

        def read_config():
            try:
                model_config = manager.get_model_config()
                task_config = manager.get_task_config()
                results.append((model_config, task_config))
            except Exception as e:
                errors.append(e)

        # Create multiple threads reading simultaneously
        threads = [threading.Thread(target=read_config) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors occurred during concurrent reads: {errors}"
        assert len(results) == 20
        # All results should be valid config objects
        for model_config, task_config in results:
            assert isinstance(model_config, ModelConfig)
            assert isinstance(task_config, TaskConfig)


class TestConfigFileHandler:
    """Test cases for ConfigFileHandler file watching."""

    def test_file_handler_initialization(self):
        """Test ConfigFileHandler initialization."""
        manager = ConfigManager.get_instance()
        callback = MagicMock()

        handler = ConfigFileHandler(manager, str(manager._task_config_path), callback)

        assert handler.config_manager is manager
        assert handler.file_path == manager._task_config_path.resolve()
        assert handler.reload_callback is callback

    def test_file_handler_debouncing(self):
        """Test that file handler debounces rapid events."""
        manager = ConfigManager.get_instance()
        callback = MagicMock()

        handler = ConfigFileHandler(manager, str(manager._task_config_path), callback)

        # Create a mock event
        event = MagicMock(spec=FileModifiedEvent)
        event.src_path = str(manager._task_config_path)

        # First call should trigger callback
        handler.on_modified(event)
        assert callback.call_count == 1

        # Immediate second call should be debounced (within 1 second)
        handler.on_modified(event)
        assert callback.call_count == 1  # Still 1, not 2

        # Wait for debounce period
        time.sleep(1.1)

        # Now it should trigger again
        handler.on_modified(event)
        assert callback.call_count == 2


class TestConfigManagerWatching:
    """Test cases for file watching functionality."""

    def test_start_watching(self):
        """Test starting file watching."""
        manager = ConfigManager.get_instance()

        # Start watching
        manager.start_watching()

        # Observer should be initialized
        assert manager._observer is not None
        assert manager._observer.is_alive()

        # Stop watching to clean up
        manager.stop_watching()

    def test_stop_watching(self):
        """Test stopping file watching."""
        manager = ConfigManager.get_instance()

        # Start watching first
        manager.start_watching()
        assert manager._observer is not None

        # Stop watching
        manager.stop_watching()

        # Observer should be stopped
        if manager._observer is not None:
            assert not manager._observer.is_alive()

    def test_multiple_start_watching_calls(self):
        """Test that multiple start_watching calls don't create multiple observers."""
        manager = ConfigManager.get_instance()

        # Start watching multiple times
        manager.start_watching()
        first_observer = manager._observer

        manager.start_watching()
        second_observer = manager._observer

        # Should be the same observer (or at least only one active)
        assert first_observer is second_observer or not first_observer.is_alive()

        # Clean up
        manager.stop_watching()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
