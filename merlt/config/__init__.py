"""
Configuration module for MERL-T.
"""

from .environments import (
    EnvironmentConfig,
    Environment,
    get_environment_config,
    get_current_environment,
    set_current_environment,
    TEST_ENV,
    PROD_ENV,
)

__all__ = [
    "EnvironmentConfig",
    "Environment",
    "get_environment_config",
    "get_current_environment",
    "set_current_environment",
    "TEST_ENV",
    "PROD_ENV",
]
