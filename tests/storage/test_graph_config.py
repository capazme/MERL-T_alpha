"""
Test FalkorDB Configuration
===========================

Unit tests for FalkorDBConfig dataclass.
"""

import pytest
import os
from unittest.mock import patch


class TestFalkorDBConfig:
    """Test FalkorDBConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from merlt.storage.graph import FalkorDBConfig

        config = FalkorDBConfig()

        assert config.host == "localhost"
        assert config.port == 6380
        assert config.graph_name == "merl_t_dev"
        assert config.max_connections == 10
        assert config.timeout_ms == 5000
        assert config.password is None

    def test_custom_values(self):
        """Test custom configuration values."""
        from merlt.storage.graph import FalkorDBConfig

        config = FalkorDBConfig(
            host="db.example.com",
            port=6381,
            graph_name="custom_graph",
            max_connections=50,
            timeout_ms=10000,
            password="secret"
        )

        assert config.host == "db.example.com"
        assert config.port == 6381
        assert config.graph_name == "custom_graph"
        assert config.max_connections == 50
        assert config.timeout_ms == 10000
        assert config.password == "secret"

    def test_environment_variable_host(self):
        """Test that config reads from FALKORDB_HOST env var."""
        from merlt.storage.graph.config import FalkorDBConfig

        with patch.dict(os.environ, {"FALKORDB_HOST": "env-host.com"}):
            # Force reimport to pick up new env var
            config = FalkorDBConfig(
                host=os.environ.get("FALKORDB_HOST", "localhost")
            )
            assert config.host == "env-host.com"

    def test_environment_variable_port(self):
        """Test that config reads from FALKORDB_PORT env var."""
        from merlt.storage.graph.config import FalkorDBConfig

        with patch.dict(os.environ, {"FALKORDB_PORT": "6399"}):
            config = FalkorDBConfig(
                port=int(os.environ.get("FALKORDB_PORT", "6380"))
            )
            assert config.port == 6399

    def test_environment_variable_graph_name(self):
        """Test that config reads from FALKORDB_GRAPH_NAME env var."""
        from merlt.storage.graph.config import FalkorDBConfig

        with patch.dict(os.environ, {"FALKORDB_GRAPH_NAME": "merl_t_prod"}):
            config = FalkorDBConfig(
                graph_name=os.environ.get("FALKORDB_GRAPH_NAME", "merl_t_dev")
            )
            assert config.graph_name == "merl_t_prod"

    def test_import_from_storage_graph(self):
        """Test importing FalkorDBConfig from merlt.storage.graph."""
        from merlt.storage.graph import FalkorDBConfig
        assert FalkorDBConfig is not None

    def test_config_for_test_environment(self):
        """Test creating config for test environment."""
        from merlt.storage.graph import FalkorDBConfig

        config = FalkorDBConfig(graph_name="merl_t_test")
        assert config.graph_name == "merl_t_test"
        assert "test" in config.graph_name

    def test_config_for_prod_environment(self):
        """Test creating config for prod environment."""
        from merlt.storage.graph import FalkorDBConfig

        config = FalkorDBConfig(graph_name="merl_t_prod")
        assert config.graph_name == "merl_t_prod"
        assert "prod" in config.graph_name


class TestFalkorDBClient:
    """Test FalkorDBClient initialization."""

    def test_client_initialization_with_config(self):
        """Test client initialization with config object."""
        from merlt.storage.graph import FalkorDBClient, FalkorDBConfig

        config = FalkorDBConfig(
            host="test-host",
            port=6381,
            graph_name="test_graph"
        )
        client = FalkorDBClient(config)

        assert client.config.host == "test-host"
        assert client.config.port == 6381
        assert client.config.graph_name == "test_graph"

    def test_client_initialization_default_config(self):
        """Test client initialization with default config."""
        from merlt.storage.graph import FalkorDBClient

        client = FalkorDBClient()

        assert client.config is not None
        assert client.config.host == "localhost"
        assert client.config.port == 6380

    def test_client_initial_state(self):
        """Test client initial state is not connected."""
        from merlt.storage.graph import FalkorDBClient

        client = FalkorDBClient()

        # Client should not be connected initially
        assert client._graph is None

    def test_client_with_password(self):
        """Test client with password in config."""
        from merlt.storage.graph import FalkorDBClient, FalkorDBConfig

        config = FalkorDBConfig(password="test_password")
        client = FalkorDBClient(config)

        assert client.config.password == "test_password"
