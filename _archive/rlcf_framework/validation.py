"""
Data Validation Module for RLCF Framework.

Provides comprehensive validation utilities for task input data,
feedback data, and ground truth data based on task type configurations.

Ensures data integrity and consistency across the system.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
from .config import task_settings
from .models import TaskType


class ValidationResult(BaseModel):
    """Result of data validation."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


def validate_task_input_data(task_type: str, input_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate task input data against task type schema.

    Args:
        task_type: Type of task (QA, CLASSIFICATION, etc.)
        input_data: Input data dictionary to validate

    Returns:
        ValidationResult with validation status and any errors/warnings
    """
    errors = []
    warnings = []

    # Check if task type exists
    if task_type not in task_settings.task_types:
        errors.append(f"Unknown task type: {task_type}")
        return ValidationResult(is_valid=False, errors=errors)

    task_config = task_settings.task_types[task_type]

    # Check required fields
    required_fields = set(task_config.input_data.keys())
    provided_fields = set(input_data.keys())

    missing_fields = required_fields - provided_fields
    if missing_fields:
        errors.append(f"Missing required input fields: {list(missing_fields)}")

    extra_fields = provided_fields - required_fields
    if extra_fields:
        warnings.append(f"Extra input fields (will be stored): {list(extra_fields)}")

    # Type validation (basic)
    for field, expected_type in task_config.input_data.items():
        if field in input_data:
            value = input_data[field]
            # Basic type checking
            if expected_type == "str" and not isinstance(value, str):
                errors.append(f"Field '{field}' should be string, got {type(value).__name__}")
            elif expected_type == "int" and not isinstance(value, int):
                errors.append(f"Field '{field}' should be integer, got {type(value).__name__}")
            elif "List" in str(expected_type) and not isinstance(value, list):
                errors.append(f"Field '{field}' should be list, got {type(value).__name__}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def validate_feedback_data(task_type: str, feedback_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate feedback data against task type schema.

    Args:
        task_type: Type of task
        feedback_data: Feedback data dictionary to validate

    Returns:
        ValidationResult with validation status and any errors/warnings
    """
    errors = []
    warnings = []

    if task_type not in task_settings.task_types:
        errors.append(f"Unknown task type: {task_type}")
        return ValidationResult(is_valid=False, errors=errors)

    task_config = task_settings.task_types[task_type]

    # Check required feedback fields
    required_fields = set(task_config.feedback_data.keys())
    provided_fields = set(feedback_data.keys())

    missing_fields = required_fields - provided_fields
    if missing_fields:
        errors.append(f"Missing required feedback fields: {list(missing_fields)}")

    extra_fields = provided_fields - required_fields
    if extra_fields:
        warnings.append(f"Extra feedback fields (will be stored): {list(extra_fields)}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def validate_ground_truth_data(task_type: str, ground_truth_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate ground truth data contains expected keys.

    Args:
        task_type: Type of task
        ground_truth_data: Ground truth data dictionary

    Returns:
        ValidationResult with validation status and any errors/warnings
    """
    errors = []
    warnings = []

    if task_type not in task_settings.task_types:
        errors.append(f"Unknown task type: {task_type}")
        return ValidationResult(is_valid=False, errors=errors)

    task_config = task_settings.task_types[task_type]

    # Check ground truth keys
    expected_keys = set(task_config.ground_truth_keys)
    provided_keys = set(ground_truth_data.keys())

    missing_keys = expected_keys - provided_keys
    if missing_keys:
        errors.append(f"Missing ground truth keys: {list(missing_keys)}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


async def check_data_integrity(db) -> Dict[str, Any]:
    """
    Check database for data integrity issues.

    Args:
        db: Database session

    Returns:
        Dictionary with integrity check results
    """
    from sqlalchemy import select, func
    from . import models

    issues = {
        "orphaned_responses": [],
        "orphaned_feedback": [],
        "tasks_without_responses": [],
        "responses_without_feedback": [],
        "missing_ground_truth": []
    }

    # Check for orphaned responses (task deleted but response exists)
    result = await db.execute(
        select(models.Response)
        .outerjoin(models.LegalTask, models.Response.task_id == models.LegalTask.id)
        .where(models.LegalTask.id == None)
    )
    orphaned_responses = result.scalars().all()
    issues["orphaned_responses"] = [r.id for r in orphaned_responses]

    # Check for orphaned feedback (response deleted but feedback exists)
    result = await db.execute(
        select(models.Feedback)
        .outerjoin(models.Response, models.Feedback.response_id == models.Response.id)
        .where(models.Response.id == None)
    )
    orphaned_feedback = result.scalars().all()
    issues["orphaned_feedback"] = [f.id for f in orphaned_feedback]

    # Check tasks without responses
    result = await db.execute(
        select(models.LegalTask)
        .outerjoin(models.Response)
        .where(models.Response.id == None)
        .where(models.LegalTask.status != "OPEN")  # Expected to have responses if not OPEN
    )
    tasks_no_responses = result.scalars().all()
    issues["tasks_without_responses"] = [t.id for t in tasks_no_responses]

    # Check responses without feedback (in BLIND_EVALUATION status)
    result = await db.execute(
        select(models.Response)
        .join(models.LegalTask)
        .outerjoin(models.Feedback)
        .where(models.LegalTask.status == "BLIND_EVALUATION")
        .where(models.Feedback.id == None)
    )
    responses_no_feedback = result.scalars().all()
    issues["responses_without_feedback"] = [r.id for r in responses_no_feedback]

    # Check tasks missing ground truth in AGGREGATED status
    result = await db.execute(
        select(models.LegalTask)
        .where(models.LegalTask.status == "AGGREGATED")
        .where(models.LegalTask.ground_truth_data == None)
    )
    tasks_no_ground_truth = result.scalars().all()
    issues["missing_ground_truth"] = [t.id for t in tasks_no_ground_truth]

    # Calculate summary
    total_issues = sum(len(v) for v in issues.values())

    return {
        "total_issues": total_issues,
        "issues": issues,
        "is_healthy": total_issues == 0
    }


def validate_consistency_scores(feedback_list: List[Any]) -> Dict[str, Any]:
    """
    Validate consistency of feedback scores.

    Args:
        feedback_list: List of Feedback objects

    Returns:
        Dictionary with consistency analysis
    """
    if not feedback_list:
        return {"is_consistent": True, "reason": "No feedback to validate"}

    # Check score ranges
    invalid_scores = []
    for feedback in feedback_list:
        if not (0.0 <= feedback.accuracy_score <= 1.0):
            invalid_scores.append(f"Feedback {feedback.id}: accuracy_score out of range")
        if not (0.0 <= feedback.utility_score <= 1.0):
            invalid_scores.append(f"Feedback {feedback.id}: utility_score out of range")
        if not (0.0 <= feedback.transparency_score <= 1.0):
            invalid_scores.append(f"Feedback {feedback.id}: transparency_score out of range")

    # Check for suspicious patterns (all perfect scores)
    perfect_scores = [
        f for f in feedback_list
        if f.accuracy_score == 1.0 and f.utility_score == 1.0 and f.transparency_score == 1.0
    ]

    warnings = []
    if len(perfect_scores) > len(feedback_list) * 0.8:
        warnings.append("Suspiciously high number of perfect scores")

    return {
        "is_consistent": len(invalid_scores) == 0,
        "invalid_scores": invalid_scores,
        "warnings": warnings,
        "total_feedback": len(feedback_list),
        "perfect_scores_count": len(perfect_scores)
    }
