"""
Dynamic Configuration Manager with Hot-Reload Support

This module implements a thread-safe configuration management system that supports:
- Hot-reload: configurations are reloaded when YAML files change
- File watching: automatic detection of file modifications
- Backup/versioning: automatic backup before each modification
- Validation: robust schema validation before applying changes
- Thread-safety: safe concurrent access from multiple workers

References:
    RLCF.md Section 3.4 - Dynamic Task Handler System
    docs/02-methodology/rlcf/technical/configuration.md
"""

import yaml
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from pydantic import ValidationError

from .config import ModelConfig, TaskConfig, load_model_config, load_task_config


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for YAML configuration files."""

    def __init__(self, config_manager: 'ConfigManager', file_path: str, reload_callback: Callable):
        self.config_manager = config_manager
        self.file_path = Path(file_path).resolve()
        self.reload_callback = reload_callback
        self.last_modified = time.time()

    def on_modified(self, event):
        """Called when a file is modified."""
        if isinstance(event, FileModifiedEvent):
            event_path = Path(event.src_path).resolve()

            # Check if this is the file we're watching
            if event_path == self.file_path:
                # Debounce: ignore events within 1 second of each other
                current_time = time.time()
                if current_time - self.last_modified < 1.0:
                    return

                self.last_modified = current_time

                # Reload configuration in a thread-safe manner
                try:
                    self.reload_callback()
                    print(f"[ConfigManager] Hot-reloaded: {self.file_path.name}")
                except Exception as e:
                    print(f"[ConfigManager] Failed to reload {self.file_path.name}: {e}")


class ConfigManager:
    """
    Thread-safe configuration manager with hot-reload support.

    This singleton class manages model and task configurations, providing:
    - Atomic configuration updates with rollback on error
    - Automatic file watching and hot-reload
    - Configuration backup/versioning
    - Thread-safe access to configurations

    Usage:
        manager = ConfigManager.get_instance()
        task_config = manager.get_task_config()

        # Update configuration
        success, error = manager.update_task_config(new_config_dict)
    """

    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the configuration manager."""
        self._model_config: ModelConfig = load_model_config()
        self._task_config: TaskConfig = load_task_config()

        # Thread locks for safe concurrent access
        self._model_lock = threading.RLock()
        self._task_lock = threading.RLock()

        # File paths
        self._base_dir = Path(__file__).parent
        self._model_config_path = self._base_dir / "model_config.yaml"
        self._task_config_path = self._base_dir / "task_config.yaml"
        self._backup_dir = self._base_dir / "config_backups"

        # Create backup directory
        self._backup_dir.mkdir(exist_ok=True)

        # File watching
        self._observer: Optional[Observer] = None
        self._watching = False

        # Callbacks for configuration changes
        self._model_callbacks: list[Callable[[ModelConfig], None]] = []
        self._task_callbacks: list[Callable[[TaskConfig], None]] = []

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Get or create the singleton ConfigManager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_watching(self):
        """Start watching configuration files for changes."""
        if self._watching:
            return

        self._observer = Observer()

        # Watch model_config.yaml
        model_handler = ConfigFileHandler(
            self,
            str(self._model_config_path),
            self._reload_model_config
        )
        self._observer.schedule(
            model_handler,
            str(self._model_config_path.parent),
            recursive=False
        )

        # Watch task_config.yaml
        task_handler = ConfigFileHandler(
            self,
            str(self._task_config_path),
            self._reload_task_config
        )
        self._observer.schedule(
            task_handler,
            str(self._task_config_path.parent),
            recursive=False
        )

        self._observer.start()
        self._watching = True
        print("[ConfigManager] Started watching configuration files")

    def stop_watching(self):
        """Stop watching configuration files."""
        if self._watching and self._observer:
            self._observer.stop()
            self._observer.join()
            self._watching = False
            print("[ConfigManager] Stopped watching configuration files")

    def _reload_model_config(self):
        """Reload model configuration from file (internal use)."""
        with self._model_lock:
            try:
                new_config = load_model_config()
                self._model_config = new_config

                # Trigger callbacks
                for callback in self._model_callbacks:
                    try:
                        callback(new_config)
                    except Exception as e:
                        print(f"[ConfigManager] Callback error: {e}")

            except Exception as e:
                print(f"[ConfigManager] Failed to reload model config: {e}")

    def _reload_task_config(self):
        """Reload task configuration from file (internal use)."""
        with self._task_lock:
            try:
                new_config = load_task_config()
                self._task_config = new_config

                # Trigger callbacks
                for callback in self._task_callbacks:
                    try:
                        callback(new_config)
                    except Exception as e:
                        print(f"[ConfigManager] Callback error: {e}")

            except Exception as e:
                print(f"[ConfigManager] Failed to reload task config: {e}")

    def get_model_config(self) -> ModelConfig:
        """Get current model configuration (thread-safe)."""
        with self._model_lock:
            return self._model_config

    def get_task_config(self) -> TaskConfig:
        """Get current task configuration (thread-safe)."""
        with self._task_lock:
            return self._task_config

    def _create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of a configuration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}.yaml"
        backup_path = self._backup_dir / backup_name

        if file_path.exists():
            shutil.copy2(file_path, backup_path)

        return backup_path

    def update_model_config(
        self,
        config_dict: Dict[str, Any],
        create_backup: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Update model configuration with validation and backup.

        Args:
            config_dict: New configuration as dictionary
            create_backup: Whether to create a backup before updating

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        with self._model_lock:
            # Create backup
            if create_backup:
                try:
                    backup_path = self._create_backup(self._model_config_path)
                    print(f"[ConfigManager] Backup created: {backup_path.name}")
                except Exception as e:
                    return False, f"Backup failed: {str(e)}"

            # Validate new configuration
            try:
                new_config = ModelConfig(**config_dict)
            except ValidationError as e:
                return False, f"Validation failed: {str(e)}"

            # Write to file
            try:
                with open(self._model_config_path, 'w') as f:
                    yaml.dump(config_dict, f, sort_keys=False, indent=2)
            except Exception as e:
                return False, f"File write failed: {str(e)}"

            # Update in-memory configuration
            self._model_config = new_config

            # Trigger callbacks
            for callback in self._model_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    print(f"[ConfigManager] Callback error: {e}")

            return True, None

    def update_task_config(
        self,
        config_dict: Dict[str, Any],
        create_backup: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Update task configuration with validation and backup.

        Args:
            config_dict: New configuration as dictionary
            create_backup: Whether to create a backup before updating

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        with self._task_lock:
            # Create backup
            if create_backup:
                try:
                    backup_path = self._create_backup(self._task_config_path)
                    print(f"[ConfigManager] Backup created: {backup_path.name}")
                except Exception as e:
                    return False, f"Backup failed: {str(e)}"

            # Validate new configuration
            try:
                new_config = TaskConfig(**config_dict)
            except ValidationError as e:
                return False, f"Validation failed: {str(e)}"

            # Write to file
            try:
                with open(self._task_config_path, 'w') as f:
                    yaml.dump(config_dict, f, sort_keys=False, indent=2)
            except Exception as e:
                return False, f"File write failed: {str(e)}"

            # Update in-memory configuration
            self._task_config = new_config

            # Trigger callbacks
            for callback in self._task_callbacks:
                try:
                    callback(new_config)
                except Exception as e:
                    print(f"[ConfigManager] Callback error: {e}")

            return True, None

    def add_task_type(
        self,
        task_type_name: str,
        schema_definition: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Add a new task type to the configuration.

        Args:
            task_type_name: Name of the new task type (e.g., "CUSTOM_ANALYSIS")
            schema_definition: Schema definition with input_data, feedback_data, ground_truth_keys

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        with self._task_lock:
            # Get current config as dict
            current_config = self._task_config.model_dump()

            # Check if task type already exists
            if task_type_name in current_config["task_types"]:
                return False, f"Task type '{task_type_name}' already exists"

            # Add new task type
            current_config["task_types"][task_type_name] = schema_definition

            # Update configuration
            return self.update_task_config(current_config)

    def update_task_type(
        self,
        task_type_name: str,
        schema_definition: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Update an existing task type schema.

        Args:
            task_type_name: Name of the task type to update
            schema_definition: New schema definition

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        with self._task_lock:
            # Get current config as dict
            current_config = self._task_config.model_dump()

            # Check if task type exists
            if task_type_name not in current_config["task_types"]:
                return False, f"Task type '{task_type_name}' does not exist"

            # Update task type
            current_config["task_types"][task_type_name] = schema_definition

            # Update configuration
            return self.update_task_config(current_config)

    def delete_task_type(self, task_type_name: str) -> tuple[bool, Optional[str]]:
        """
        Delete a task type from the configuration.

        Args:
            task_type_name: Name of the task type to delete

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        with self._task_lock:
            # Get current config as dict
            current_config = self._task_config.model_dump()

            # Check if task type exists
            if task_type_name not in current_config["task_types"]:
                return False, f"Task type '{task_type_name}' does not exist"

            # Delete task type
            del current_config["task_types"][task_type_name]

            # Update configuration
            return self.update_task_config(current_config)

    def list_backups(self, config_type: str = "all") -> list[Dict[str, Any]]:
        """
        List available configuration backups.

        Args:
            config_type: "model", "task", or "all"

        Returns:
            List of backup info dictionaries
        """
        backups = []

        for backup_file in sorted(self._backup_dir.glob("*.yaml"), reverse=True):
            name = backup_file.stem

            # Filter by config type
            if config_type == "model" and not name.startswith("model_config"):
                continue
            elif config_type == "task" and not name.startswith("task_config"):
                continue

            backups.append({
                "filename": backup_file.name,
                "type": "model" if name.startswith("model_config") else "task",
                "timestamp": backup_file.stat().st_mtime,
                "size_bytes": backup_file.stat().st_size,
            })

        return backups

    def restore_backup(self, backup_filename: str) -> tuple[bool, Optional[str]]:
        """
        Restore a configuration from a backup file.

        Args:
            backup_filename: Name of the backup file to restore

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        backup_path = self._backup_dir / backup_filename

        if not backup_path.exists():
            return False, f"Backup file '{backup_filename}' not found"

        # Determine config type from filename
        is_model_config = backup_filename.startswith("model_config")
        target_path = self._model_config_path if is_model_config else self._task_config_path
        lock = self._model_lock if is_model_config else self._task_lock

        with lock:
            try:
                # Read backup content
                with open(backup_path, 'r') as f:
                    config_dict = yaml.safe_load(f)

                # Validate and update
                if is_model_config:
                    return self.update_model_config(config_dict, create_backup=True)
                else:
                    return self.update_task_config(config_dict, create_backup=True)

            except Exception as e:
                return False, f"Restore failed: {str(e)}"

    def register_model_callback(self, callback: Callable[[ModelConfig], None]):
        """Register a callback to be called when model config changes."""
        self._model_callbacks.append(callback)

    def register_task_callback(self, callback: Callable[[TaskConfig], None]):
        """Register a callback to be called when task config changes."""
        self._task_callbacks.append(callback)


# Global instance
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_manager_instance

    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager.get_instance()
        _config_manager_instance.start_watching()

    return _config_manager_instance
