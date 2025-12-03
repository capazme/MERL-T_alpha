"""
Test GraphAwareRetriever
==========================

Test hybrid retrieval combining vector similarity and graph structure.
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, MagicMock

from backend.storage.retriever import (
    GraphAwareRetriever,
    RetrievalResult,
    RetrieverConfig,
    VectorSearchResult,
    GraphPath
)
from backend.storage.bridge import BridgeTable, BridgeTableConfig
from backend.storage.falkordb import FalkorDBClient, FalkorDBConfig


@pytest.fixture
def retriever_config():
    """Test configuration with default values."""
    return RetrieverConfig(
        alpha=0.7,
        over_retrieve_factor=3,
        max_graph_hops=3,
        default_graph_score=0.5
    )


@pytest.fixture
def mock_vector_db():
    """Mock Qdrant client for vector search."""
    mock_db = Mock()
    mock_db.search = AsyncMock()
    return mock_db


@pytest_asyncio.fixture
async def bridge_table():
    """Real BridgeTable for integration tests."""
    config = BridgeTableConfig(
        host="localhost",
        port=5433,
        database="rlcf_dev",
        user="dev",
        password="devpassword"
    )

    bridge = BridgeTable(config)
    await bridge.connect()

    yield bridge

    await bridge.close()


@pytest_asyncio.fixture
async def falkordb_client():
    """Real FalkorDB client for integration tests."""
    config = FalkorDBConfig(
        host="localhost",
        port=6380,
        graph_name="merl_t_legal"
    )

    client = FalkorDBClient(config)
    await client.connect()

    yield client

    await client.close()


class TestRetrieverConfig:
    """Test RetrieverConfig validation."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = RetrieverConfig(
            alpha=0.7,
            over_retrieve_factor=3,
            max_graph_hops=3
        )
        assert config.alpha == 0.7
        assert config.over_retrieve_factor == 3
        assert config.max_graph_hops == 3

    def test_invalid_alpha(self):
        """Test alpha validation (must be in [0, 1])."""
        with pytest.raises(ValueError, match="alpha must be in"):
            RetrieverConfig(alpha=1.5)

        with pytest.raises(ValueError, match="alpha must be in"):
            RetrieverConfig(alpha=-0.1)

    def test_invalid_over_retrieve_factor(self):
        """Test over_retrieve_factor validation (must be >= 1)."""
        with pytest.raises(ValueError, match="over_retrieve_factor must be"):
            RetrieverConfig(over_retrieve_factor=0)

    def test_invalid_max_hops(self):
        """Test max_graph_hops validation (must be >= 1)."""
        with pytest.raises(ValueError, match="max_graph_hops must be"):
            RetrieverConfig(max_graph_hops=0)


class TestGraphAwareRetriever:
    """Test GraphAwareRetriever core logic."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_vector_db, bridge_table, falkordb_client, retriever_config):
        """Test retriever initialization."""
        retriever = GraphAwareRetriever(
            vector_db=mock_vector_db,
            graph_db=falkordb_client,
            bridge_table=bridge_table,
            config=retriever_config
        )

        assert retriever.vector_db == mock_vector_db
        assert retriever.graph_db == falkordb_client
        assert retriever.bridge == bridge_table
        assert retriever.config.alpha == 0.7

    @pytest.mark.asyncio
    async def test_retrieve_empty_vector_results(
        self,
        mock_vector_db,
        bridge_table,
        falkordb_client,
        retriever_config
    ):
        """Test retrieve with no vector results."""
        # Mock empty vector search
        mock_vector_db.search = AsyncMock(return_value=[])

        retriever = GraphAwareRetriever(
            vector_db=mock_vector_db,
            graph_db=falkordb_client,
            bridge_table=bridge_table,
            config=retriever_config
        )

        query_embedding = [0.1] * 1024
        results = await retriever.retrieve(
            query_embedding=query_embedding,
            context_nodes=[],
            top_k=10
        )

        assert results == []
        mock_vector_db.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_combine_scores(self, retriever_config):
        """Test score combination formula."""
        retriever = GraphAwareRetriever(
            vector_db=None,
            graph_db=None,
            bridge_table=None,
            config=retriever_config
        )

        # Test with alpha=0.7
        similarity_score = 0.9
        graph_score = 0.6
        final_score = retriever._combine_scores(similarity_score, graph_score)

        expected = 0.7 * 0.9 + 0.3 * 0.6  # 0.63 + 0.18 = 0.81
        assert abs(final_score - expected) < 0.001

    @pytest.mark.asyncio
    async def test_score_path_with_expert_weights(self, retriever_config):
        """Test path scoring with expert-specific weights."""
        retriever = GraphAwareRetriever(
            vector_db=None,
            graph_db=None,
            bridge_table=None,
            config=retriever_config
        )

        # Create a path: Art. 1453 -[disciplina]-> risoluzione_contratto
        path = GraphPath(
            source_node="urn:norma:cc:art1453",
            target_node="urn:concetto:risoluzione",
            edges=[{"type": "disciplina"}],
            length=1
        )

        # Score for LiteralExpert (disciplina weight = 0.95)
        score = retriever._score_path(path, expert_type="LiteralExpert")

        # Expected: (1 / (1 + 1)) * 0.95 = 0.5 * 0.95 = 0.475
        assert abs(score - 0.475) < 0.001

    @pytest.mark.asyncio
    async def test_score_path_no_expert(self, retriever_config):
        """Test path scoring without expert type (default weights)."""
        retriever = GraphAwareRetriever(
            vector_db=None,
            graph_db=None,
            bridge_table=None,
            config=retriever_config
        )

        path = GraphPath(
            source_node="node1",
            target_node="node2",
            edges=[{"type": "some_relation"}],
            length=2
        )

        # Score without expert: (1 / (2 + 1)) * 1.0 = 0.333
        score = retriever._score_path(path, expert_type=None)

        assert abs(score - 0.333) < 0.01

    @pytest.mark.asyncio
    async def test_update_alpha(self, retriever_config):
        """Test alpha parameter learning from feedback."""
        retriever = GraphAwareRetriever(
            vector_db=None,
            graph_db=None,
            bridge_table=None,
            config=retriever_config
        )

        initial_alpha = retriever.config.alpha  # 0.7

        # Positive feedback ’ decrease alpha (more graph weight)
        retriever.update_alpha(feedback_correlation=0.8, authority=1.0)
        assert retriever.config.alpha < initial_alpha

        # Negative feedback ’ increase alpha (more similarity weight)
        retriever.update_alpha(feedback_correlation=0.2, authority=1.0)
        assert retriever.config.alpha > (initial_alpha - 0.01)

        # Alpha should stay within bounds [0.3, 0.9]
        for _ in range(100):
            retriever.update_alpha(feedback_correlation=0.9, authority=1.0)
        assert 0.3 <= retriever.config.alpha <= 0.9


@pytest.mark.integration
class TestRetrieverIntegration:
    """
    Integration tests with real FalkorDB and BridgeTable.

    Requires:
    - FalkorDB running on port 6380
    - PostgreSQL running on port 5433
    - Test data: Art. 1453-1456 ingested
    """

    @pytest.mark.asyncio
    async def test_retrieve_with_mock_vector(
        self,
        mock_vector_db,
        bridge_table,
        falkordb_client,
        retriever_config
    ):
        """Test retrieve with mocked vector results and real graph/bridge."""
        # Setup: Add test mapping to bridge table
        test_chunk_id = uuid4()
        test_node_urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"

        await bridge_table.add_mapping(
            chunk_id=test_chunk_id,
            graph_node_urn=test_node_urn,
            node_type="Norma",
            relation_type="contained_in",
            confidence=1.0,
            source="test"
        )

        # Mock vector search to return our test chunk
        mock_result = MagicMock()
        mock_result.id = str(test_chunk_id)
        mock_result.score = 0.95
        mock_result.payload = {
            "text": "Art. 1453 c.c. - Risoluzione per inadempimento"
        }
        mock_vector_db.search = AsyncMock(return_value=[mock_result])

        # Create retriever
        retriever = GraphAwareRetriever(
            vector_db=mock_vector_db,
            graph_db=falkordb_client,
            bridge_table=bridge_table,
            config=retriever_config
        )

        # Retrieve with context node
        query_embedding = [0.1] * 1024
        results = await retriever.retrieve(
            query_embedding=query_embedding,
            context_nodes=[test_node_urn],
            expert_type="LiteralExpert",
            top_k=5
        )

        # Assertions
        assert len(results) == 1
        assert results[0].chunk_id == test_chunk_id
        assert results[0].similarity_score == 0.95
        assert results[0].final_score > 0.7  # Should have high score

        # Cleanup
        await bridge_table.delete_mappings_for_chunk(test_chunk_id)

    @pytest.mark.asyncio
    async def test_graph_score_with_real_data(
        self,
        bridge_table,
        falkordb_client,
        retriever_config
    ):
        """Test graph score calculation with real ingested data."""
        # This test requires Art. 1453-1456 to be ingested
        # Check if data exists
        result = await falkordb_client.query(
            "MATCH (n:Norma {estremi: 'art1453'}) RETURN count(n) as count"
        )

        if not result or result[0].get("count", 0) == 0:
            pytest.skip("Test data not ingested (run scripts/ingest_art_1453_1456.py first)")

        retriever = GraphAwareRetriever(
            vector_db=None,
            graph_db=falkordb_client,
            bridge_table=bridge_table,
            config=retriever_config
        )

        # Test graph score between Art. 1453 and risoluzione_contratto concept
        art1453_urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"
        concept_urn = "urn:concetto:risoluzione_contratto"

        graph_score = await retriever._compute_graph_score(
            chunk_nodes=[art1453_urn],
            context_nodes=[concept_urn],
            expert_type="LiteralExpert"
        )

        # Should find path: Art. 1453 -[disciplina]-> risoluzione_contratto
        assert graph_score > 0.5  # Should be higher than default


# Run tests with: pytest tests/storage/test_retriever.py -v
# Run integration tests only: pytest tests/storage/test_retriever.py -v -m integration
