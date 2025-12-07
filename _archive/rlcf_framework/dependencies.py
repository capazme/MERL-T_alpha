"""
Centralized dependency injection for the RLCF framework.

This module provides all dependencies needed across the application,
improving testability and configuration management.

Updated to use ConfigManager for hot-reload support.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from .database import SessionLocal
from .config import ModelConfig, TaskConfig
from .config_manager import get_config_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency that provides database session.

    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_model_settings() -> ModelConfig:
    """
    Dependency that provides model configuration settings.

    Uses ConfigManager for hot-reload support - always returns the latest configuration.

    Returns:
        ModelConfig: Current model configuration
    """
    config_manager = get_config_manager()
    return config_manager.get_model_config()


def get_task_settings() -> TaskConfig:
    """
    Dependency that provides task configuration settings.

    Uses ConfigManager for hot-reload support - always returns the latest configuration.

    Returns:
        TaskConfig: Current task configuration
    """
    config_manager = get_config_manager()
    return config_manager.get_task_config()


def get_ai_config():
    """
    Dependency that provides AI model configuration.

    Uses ConfigManager for hot-reload support.

    Returns:
        AIModelConfig: AI model configuration with API key from environment
    """
    from .ai_service import AIModelConfig
    import os

    config_manager = get_config_manager()
    model_config = config_manager.get_model_config()
    ai_settings = model_config.ai_model
    api_key = os.getenv(ai_settings.api_key_env, "")

    return AIModelConfig(
        name=ai_settings.name,
        api_key=api_key,
        temperature=ai_settings.temperature,
        max_tokens=ai_settings.max_tokens,
        top_p=ai_settings.top_p
    )
