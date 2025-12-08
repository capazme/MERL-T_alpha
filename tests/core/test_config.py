"""
Test MerltConfig
================

Unit tests for the MerltConfig dataclass.
"""

import pytest


class TestMerltConfig:
    """Test MerltConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from merlt import MerltConfig

        config = MerltConfig()

        # FalkorDB defaults
        assert config.falkordb_host == "localhost"
        assert config.falkordb_port == 6380
        assert config.graph_name == "merl_t_test"  # Default is test environment

        # Qdrant defaults
        assert config.qdrant_host == "localhost"
        assert config.qdrant_port == 6333
        # qdrant_collection defaults to graph_name via __post_init__
        assert config.qdrant_collection == config.graph_name

        # PostgreSQL defaults
        assert config.postgres_host == "localhost"
        assert config.postgres_port == 5433
        assert config.postgres_database == "rlcf_dev"
        assert config.postgres_user == "dev"
        assert config.postgres_password == "devpassword"

    def test_custom_values(self):
        """Test custom configuration values."""
        from merlt import MerltConfig

        config = MerltConfig(
            falkordb_host="falkor.example.com",
            falkordb_port=6381,
            graph_name="custom_graph",
            qdrant_host="qdrant.example.com",
            qdrant_port=6334,
            qdrant_collection="custom_collection",
            postgres_host="pg.example.com",
            postgres_port=5432,
            postgres_database="custom_db",
            postgres_user="custom_user",
            postgres_password="custom_pass"
        )

        assert config.falkordb_host == "falkor.example.com"
        assert config.falkordb_port == 6381
        assert config.graph_name == "custom_graph"
        assert config.qdrant_host == "qdrant.example.com"
        assert config.qdrant_port == 6334
        assert config.qdrant_collection == "custom_collection"
        assert config.postgres_host == "pg.example.com"
        assert config.postgres_port == 5432
        assert config.postgres_database == "custom_db"
        assert config.postgres_user == "custom_user"
        assert config.postgres_password == "custom_pass"

    def test_import_from_merlt(self):
        """Test importing MerltConfig from merlt package."""
        from merlt import MerltConfig
        assert MerltConfig is not None

    def test_import_from_core(self):
        """Test importing MerltConfig from merlt.core."""
        from merlt.core import MerltConfig
        assert MerltConfig is not None

    def test_test_environment_config(self):
        """Test creating config for test environment."""
        from merlt import MerltConfig

        config = MerltConfig(
            graph_name="merl_t_test",
            qdrant_collection="merl_t_test_chunks"
        )

        assert "test" in config.graph_name
        assert "test" in config.qdrant_collection

    def test_prod_environment_config(self):
        """Test creating config for production environment."""
        from merlt import MerltConfig

        config = MerltConfig(
            graph_name="merl_t_prod",
            qdrant_collection="merl_t_prod_chunks",
            postgres_database="rlcf_prod"
        )

        assert "prod" in config.graph_name
        assert "prod" in config.qdrant_collection
        assert "prod" in config.postgres_database


class TestLegalKnowledgeGraphUnit:
    """Unit tests for LegalKnowledgeGraph (no external connections)."""

    def test_initialization_with_default_config(self):
        """Test LegalKnowledgeGraph initialization with default config."""
        from merlt import LegalKnowledgeGraph

        kg = LegalKnowledgeGraph()

        assert kg.config is not None
        assert kg.is_connected is False
        assert kg.falkordb is None
        assert kg.qdrant is None
        assert kg.bridge_table is None

    def test_initialization_with_custom_config(self):
        """Test LegalKnowledgeGraph initialization with custom config."""
        from merlt import LegalKnowledgeGraph, MerltConfig

        config = MerltConfig(
            graph_name="test_graph",
            qdrant_collection="test_collection"
        )
        kg = LegalKnowledgeGraph(config)

        assert kg.config.graph_name == "test_graph"
        assert kg.config.qdrant_collection == "test_collection"
        assert kg.is_connected is False

    def test_import_from_merlt(self):
        """Test importing LegalKnowledgeGraph from merlt."""
        from merlt import LegalKnowledgeGraph
        assert LegalKnowledgeGraph is not None

    def test_import_from_core(self):
        """Test importing LegalKnowledgeGraph from merlt.core."""
        from merlt.core import LegalKnowledgeGraph
        assert LegalKnowledgeGraph is not None

    def test_not_connected_before_connect(self):
        """Test that KG is not connected before calling connect()."""
        from merlt import LegalKnowledgeGraph

        kg = LegalKnowledgeGraph()

        assert kg.is_connected is False

    def test_config_attributes(self):
        """Test that config attributes are properly stored."""
        from merlt import LegalKnowledgeGraph, MerltConfig

        config = MerltConfig(
            falkordb_host="custom-host",
            falkordb_port=1234,
            graph_name="custom-graph"
        )
        kg = LegalKnowledgeGraph(config)

        assert kg.config.falkordb_host == "custom-host"
        assert kg.config.falkordb_port == 1234
        assert kg.config.graph_name == "custom-graph"
