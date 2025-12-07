"""
Base classes for Retrieval Agents - Week 6 Day 2
=================================================

Abstract base class for all retrieval agents (KG, API, VectorDB).

All agents follow the same interface:
- execute(tasks: List[AgentTask]) -> AgentResult
- Async execution
- Error handling with partial results
- Metrics tracking (latency, success rate)

Usage:
    class MyAgent(RetrievalAgent):
        async def execute(self, tasks: List[AgentTask]) -> AgentResult:
            # Implementation
            pass
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel


logger = logging.getLogger(__name__)


# ==============================================
# Data Models
# ==============================================

class AgentTask(BaseModel):
    """
    Task for a retrieval agent.

    Generic task structure that each agent interprets differently.
    """
    task_type: str
    params: Dict[str, Any] = {}
    priority: str = "medium"  # high, medium, low

    class Config:
        extra = "allow"  # Allow extra fields for agent-specific params


@dataclass
class AgentResult:
    """
    Result from agent execution.

    Contains:
    - Retrieved data
    - Metadata (latency, source, confidence)
    - Errors (if any)
    """
    agent_name: str
    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Metadata
    execution_time_ms: float = 0.0
    tasks_executed: int = 0
    tasks_successful: int = 0
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "execution_time_ms": self.execution_time_ms,
            "tasks_executed": self.tasks_executed,
            "tasks_successful": self.tasks_successful,
            "source": self.source,
            "timestamp": self.timestamp
        }


# ==============================================
# Base Agent Class
# ==============================================

class RetrievalAgent(ABC):
    """
    Abstract base class for all retrieval agents.

    All agents must implement:
    - execute(tasks) -> AgentResult

    Agents should:
    - Handle errors gracefully (return partial results)
    - Track execution time
    - Log operations
    - Validate task types
    """

    def __init__(self, agent_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent.

        Args:
            agent_name: Name of the agent (e.g., "KGAgent", "APIAgent")
            config: Agent-specific configuration
        """
        self.agent_name = agent_name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_name}")

    @abstractmethod
    async def execute(self, tasks: List[AgentTask]) -> AgentResult:
        """
        Execute retrieval tasks.

        Args:
            tasks: List of tasks to execute

        Returns:
            AgentResult with retrieved data and metadata

        Raises:
            Should NOT raise exceptions - handle errors and return AgentResult
            with success=False and errors populated
        """
        pass

    def _validate_tasks(
        self,
        tasks: List[AgentTask],
        supported_task_types: List[str]
    ) -> List[AgentTask]:
        """
        Validate tasks and filter unsupported types.

        Args:
            tasks: Tasks to validate
            supported_task_types: List of task types this agent supports

        Returns:
            List of valid tasks

        Side effects:
            Logs warnings for unsupported tasks
        """
        valid_tasks = []

        for task in tasks:
            if task.task_type in supported_task_types:
                valid_tasks.append(task)
            else:
                self.logger.warning(
                    f"{self.agent_name} received unsupported task type: {task.task_type}"
                )

        return valid_tasks

    def _create_error_result(
        self,
        error_message: str,
        tasks_count: int = 0
    ) -> AgentResult:
        """
        Create AgentResult for error case.

        Args:
            error_message: Error description
            tasks_count: Number of tasks attempted

        Returns:
            AgentResult with success=False
        """
        return AgentResult(
            agent_name=self.agent_name,
            success=False,
            data=[],
            errors=[error_message],
            tasks_executed=tasks_count,
            tasks_successful=0
        )

    async def _track_execution(
        self,
        task_name: str,
        execute_fn
    ) -> Any:
        """
        Track execution time for a task.

        Args:
            task_name: Name of task (for logging)
            execute_fn: Async function to execute

        Returns:
            Result from execute_fn
        """
        start_time = time.time()

        try:
            result = await execute_fn()
            elapsed_ms = (time.time() - start_time) * 1000

            self.logger.info(
                f"{self.agent_name}.{task_name} completed in {elapsed_ms:.2f}ms"
            )

            return result

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"{self.agent_name}.{task_name} failed after {elapsed_ms:.2f}ms: {str(e)}"
            )

            raise


# ==============================================
# Utility Functions
# ==============================================

def merge_agent_results(results: List[AgentResult]) -> Dict[str, Any]:
    """
    Merge results from multiple agents into single dict.

    Args:
        results: List of AgentResult from different agents

    Returns:
        Merged dictionary:
        {
            "agents": {
                "kg_agent": {...},
                "api_agent": {...},
                ...
            },
            "total_data_count": int,
            "successful_agents": int,
            "failed_agents": int,
            "total_execution_time_ms": float
        }
    """
    merged = {
        "agents": {},
        "total_data_count": 0,
        "successful_agents": 0,
        "failed_agents": 0,
        "total_execution_time_ms": 0.0,
        "errors": []
    }

    for result in results:
        # Add agent result
        merged["agents"][result.agent_name] = result.to_dict()

        # Aggregate counts
        merged["total_data_count"] += len(result.data)
        if result.success:
            merged["successful_agents"] += 1
        else:
            merged["failed_agents"] += 1

        # Aggregate time
        merged["total_execution_time_ms"] += result.execution_time_ms

        # Collect errors
        if result.errors:
            merged["errors"].extend([
                f"{result.agent_name}: {err}" for err in result.errors
            ])

    return merged


# ==============================================
# Exports
# ==============================================

__all__ = [
    "AgentTask",
    "AgentResult",
    "RetrievalAgent",
    "merge_agent_results",
]
