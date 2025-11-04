"""
Dynamic Configuration Management API Endpoints

This module provides REST API endpoints for managing task and model configurations
dynamically, including:
- CRUD operations for task types
- Configuration validation and hot-reload
- Backup management and restoration
- Configuration export/import

All endpoints require admin authentication.

References:
    docs/02-methodology/rlcf/technical/configuration.md
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..config import TaskConfig, ModelConfig, TaskSchemaDefinition
from ..config_manager import get_config_manager
from ..main import get_api_key  # Admin auth dependency


router = APIRouter(prefix="/config", tags=["Configuration Management"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TaskTypeSchema(BaseModel):
    """Schema for defining a task type."""
    input_data: Dict[str, str] = Field(..., description="Input data schema (field_name: type)")
    feedback_data: Dict[str, str] = Field(..., description="Feedback data schema (field_name: type)")
    ground_truth_keys: List[str] = Field(default_factory=list, description="Keys to separate as ground truth")


class TaskTypeCreateRequest(BaseModel):
    """Request body for creating a new task type."""
    task_type_name: str = Field(..., description="Unique name for the task type (e.g., CUSTOM_ANALYSIS)")
    schema: TaskTypeSchema


class TaskTypeUpdateRequest(BaseModel):
    """Request body for updating an existing task type."""
    schema: TaskTypeSchema


class ConfigUpdateResponse(BaseModel):
    """Response for configuration update operations."""
    success: bool
    message: str
    task_type_name: Optional[str] = None


class BackupInfo(BaseModel):
    """Information about a configuration backup."""
    filename: str
    type: str  # "model" or "task"
    timestamp: float
    size_bytes: int
    formatted_date: str


class BackupListResponse(BaseModel):
    """Response for listing backups."""
    backups: List[BackupInfo]
    total_count: int


class RestoreBackupRequest(BaseModel):
    """Request body for restoring a backup."""
    backup_filename: str


# ============================================================================
# Task Configuration Endpoints
# ============================================================================

@router.get("/task", response_model=TaskConfig)
async def get_task_configuration():
    """
    Get the current task configuration.

    Returns the complete task configuration with all defined task types and their schemas.
    This always returns the latest configuration (supports hot-reload).
    """
    config_manager = get_config_manager()
    return config_manager.get_task_config()


@router.put("/task", response_model=ConfigUpdateResponse)
async def update_task_configuration(
    config: TaskConfig,
    api_key: str = Depends(get_api_key)
):
    """
    Update the entire task configuration (admin only).

    Replaces the complete task configuration with validation and automatic backup.
    Use this for bulk updates or when importing a complete configuration.

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.update_task_config(
        config.model_dump(),
        create_backup=True
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration update failed: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message="Task configuration updated successfully"
    )


@router.post("/task/type", response_model=ConfigUpdateResponse, status_code=status.HTTP_201_CREATED)
async def create_task_type(
    request: TaskTypeCreateRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Create a new task type dynamically (admin only).

    Adds a new task type to the configuration with validation. The new task type
    will be immediately available for creating tasks without server restart.

    Example:
    ```json
    {
        "task_type_name": "CONTRACT_REVIEW",
        "schema": {
            "input_data": {
                "contract_text": "str",
                "review_criteria": "List[str]"
            },
            "feedback_data": {
                "review_result": "str",
                "issues_found": "List[str]",
                "severity": "int"
            },
            "ground_truth_keys": ["review_result", "issues_found"]
        }
    }
    ```

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.add_task_type(
        request.task_type_name,
        request.schema.model_dump()
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create task type: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message=f"Task type '{request.task_type_name}' created successfully",
        task_type_name=request.task_type_name
    )


@router.put("/task/type/{task_type_name}", response_model=ConfigUpdateResponse)
async def update_task_type(
    task_type_name: str,
    request: TaskTypeUpdateRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Update an existing task type schema (admin only).

    Modifies the schema of an existing task type. This affects how new tasks
    of this type are validated.

    **Warning:** Changing schemas for task types with existing tasks may cause
    validation issues with old data.

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.update_task_type(
        task_type_name,
        request.schema.model_dump()
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update task type: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message=f"Task type '{task_type_name}' updated successfully",
        task_type_name=task_type_name
    )


@router.delete("/task/type/{task_type_name}", response_model=ConfigUpdateResponse)
async def delete_task_type(
    task_type_name: str,
    api_key: str = Depends(get_api_key)
):
    """
    Delete a task type from configuration (admin only).

    Removes a task type from the configuration. This does NOT delete existing
    tasks of this type from the database, but prevents creating new ones.

    **Warning:** Deleting task types that have existing tasks may cause issues.
    Consider deprecating instead of deleting.

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.delete_task_type(task_type_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete task type: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message=f"Task type '{task_type_name}' deleted successfully",
        task_type_name=task_type_name
    )


@router.get("/task/types", response_model=List[str])
async def list_task_types():
    """
    List all configured task types.

    Returns a list of task type names currently defined in the configuration.
    """
    config_manager = get_config_manager()
    task_config = config_manager.get_task_config()
    return list(task_config.task_types.keys())


@router.get("/task/type/{task_type_name}", response_model=TaskSchemaDefinition)
async def get_task_type_schema(task_type_name: str):
    """
    Get the schema definition for a specific task type.

    Returns the complete schema including input_data, feedback_data, and
    ground_truth_keys for the specified task type.
    """
    config_manager = get_config_manager()
    task_config = config_manager.get_task_config()

    if task_type_name not in task_config.task_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{task_type_name}' not found"
        )

    return task_config.task_types[task_type_name]


# ============================================================================
# Model Configuration Endpoints
# ============================================================================

@router.get("/model", response_model=ModelConfig)
async def get_model_configuration():
    """
    Get the current model configuration.

    Returns the complete model configuration including authority weights,
    track record settings, thresholds, baseline credentials, and AI model settings.
    """
    config_manager = get_config_manager()
    return config_manager.get_model_config()


@router.put("/model", response_model=ConfigUpdateResponse)
async def update_model_configuration(
    config: ModelConfig,
    api_key: str = Depends(get_api_key)
):
    """
    Update the entire model configuration (admin only).

    Replaces the complete model configuration with validation and automatic backup.

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.update_model_config(
        config.model_dump(),
        create_backup=True
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration update failed: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message="Model configuration updated successfully"
    )


# ============================================================================
# Backup Management Endpoints
# ============================================================================

@router.get("/backups", response_model=BackupListResponse)
async def list_configuration_backups(
    config_type: str = "all",
    api_key: str = Depends(get_api_key)
):
    """
    List all configuration backups (admin only).

    Args:
        config_type: Filter by type ("model", "task", or "all")

    Returns a list of available backup files with metadata.

    Requires admin API key authentication.
    """
    if config_type not in ["model", "task", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="config_type must be 'model', 'task', or 'all'"
        )

    config_manager = get_config_manager()
    backups_raw = config_manager.list_backups(config_type)

    # Format timestamps
    backups = [
        BackupInfo(
            **backup,
            formatted_date=datetime.fromtimestamp(backup["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        )
        for backup in backups_raw
    ]

    return BackupListResponse(
        backups=backups,
        total_count=len(backups)
    )


@router.post("/backups/restore", response_model=ConfigUpdateResponse)
async def restore_configuration_backup(
    request: RestoreBackupRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Restore a configuration from a backup file (admin only).

    Replaces the current configuration with the specified backup.
    A new backup of the current configuration is created before restoration.

    **Warning:** This will replace the current configuration. Make sure you have
    a recent backup before restoring.

    Requires admin API key authentication.
    """
    config_manager = get_config_manager()

    success, error = config_manager.restore_backup(request.backup_filename)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backup restoration failed: {error}"
        )

    return ConfigUpdateResponse(
        success=True,
        message=f"Configuration restored from backup '{request.backup_filename}'"
    )


# ============================================================================
# Configuration Status & Health
# ============================================================================

@router.get("/status")
async def get_configuration_status():
    """
    Get configuration system status.

    Returns information about the configuration manager state, including:
    - Whether file watching is active
    - Number of configured task types
    - Configuration file paths
    """
    config_manager = get_config_manager()
    task_config = config_manager.get_task_config()

    return {
        "status": "active",
        "file_watching_enabled": config_manager._watching,
        "task_types_count": len(task_config.task_types),
        "task_types": list(task_config.task_types.keys()),
        "config_files": {
            "model_config": str(config_manager._model_config_path),
            "task_config": str(config_manager._task_config_path)
        },
        "backup_directory": str(config_manager._backup_dir)
    }
