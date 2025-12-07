"""
Environment Configuration
=========================

Manages test/prod environment separation for MERL-T storage.

Usage:
    from merlt.config import get_environment_config, TEST_ENV, PROD_ENV

    # Get test environment config
    config = get_environment_config(TEST_ENV)
    print(config.falkordb_graph)  # "merl_t_test"
    print(config.qdrant_collection)  # "merl_t_test_chunks"

    # Switch global environment
    set_current_environment(PROD_ENV)
    config = get_current_environment()
    print(config.name)  # "prod"
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Environment(Enum):
    """Available environments."""
    TEST = "test"
    PROD = "prod"


# Convenience aliases
TEST_ENV = Environment.TEST
PROD_ENV = Environment.PROD


@dataclass(frozen=True)
class EnvironmentConfig:
    """
    Configuration for a specific environment.

    Attributes:
        name: Environment name ("test" or "prod")
        falkordb_graph: FalkorDB graph name
        qdrant_collection: Qdrant collection name
        bridge_table_suffix: Suffix for bridge table (if needed)
        description: Human-readable description
    """
    name: str
    falkordb_graph: str
    qdrant_collection: str
    bridge_table_suffix: str
    description: str

    # Database connection settings (shared across environments)
    falkordb_host: str = "localhost"
    falkordb_port: int = 6380
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    postgres_dsn: str = "postgresql://dev:devpassword@localhost:5433/rlcf_dev"


# Environment configurations
_ENVIRONMENTS = {
    Environment.TEST: EnvironmentConfig(
        name="test",
        falkordb_graph="merl_t_test",
        qdrant_collection="merl_t_test_chunks",
        bridge_table_suffix="_test",
        description="Test environment for experiments (EXP-005, etc.)",
    ),
    Environment.PROD: EnvironmentConfig(
        name="prod",
        falkordb_graph="merl_t_prod",
        qdrant_collection="merl_t_prod_chunks",
        bridge_table_suffix="_prod",
        description="Production environment with validated data",
    ),
}

# Current active environment (default: test for safety)
_current_environment: Environment = Environment.TEST


def get_environment_config(env: Environment) -> EnvironmentConfig:
    """
    Get configuration for a specific environment.

    Args:
        env: Environment enum value

    Returns:
        EnvironmentConfig for the specified environment

    Example:
        config = get_environment_config(TEST_ENV)
        print(config.falkordb_graph)  # "merl_t_test"
    """
    return _ENVIRONMENTS[env]


def get_current_environment() -> EnvironmentConfig:
    """
    Get configuration for the currently active environment.

    The current environment can be set via:
    1. set_current_environment() function
    2. MERL_T_ENV environment variable

    Returns:
        EnvironmentConfig for current environment

    Example:
        config = get_current_environment()
        print(config.name)  # "test" (default)
    """
    global _current_environment

    # Check environment variable override
    env_var = os.environ.get("MERL_T_ENV", "").lower()
    if env_var == "prod":
        return _ENVIRONMENTS[Environment.PROD]
    elif env_var == "test":
        return _ENVIRONMENTS[Environment.TEST]

    return _ENVIRONMENTS[_current_environment]


def set_current_environment(env: Environment) -> None:
    """
    Set the current active environment.

    Args:
        env: Environment to activate

    Example:
        set_current_environment(PROD_ENV)
        config = get_current_environment()
        print(config.name)  # "prod"
    """
    global _current_environment
    _current_environment = env


def get_all_environments() -> dict:
    """
    Get all available environment configurations.

    Returns:
        Dict mapping Environment enum to EnvironmentConfig
    """
    return _ENVIRONMENTS.copy()
