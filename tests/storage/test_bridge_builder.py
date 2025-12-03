"""
Test Bridge Builder
====================

Integration tests for BridgeBuilder that converts
IngestionPipelineV2 mappings to Bridge Table format.

Uses real PostgreSQL connection (no mocks).
"""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID

from backend.storage.bridge import BridgeTable, BridgeTableConfig
from backend.storage.bridge.bridge_builder import BridgeBuilder, insert_ingestion_result
from backend.preprocessing.ingestion_pipeline_v2 import BridgeMapping


@pytest_asyncio.fixture(scope="function")
async def bridge_table():
    """Initialize BridgeTable for testing."""
    config = BridgeTableConfig(
        host="localhost",
        port=5433,  # Dev container port
        database="rlcf_dev",
        user="dev",
        password="devpassword"
    )

    bridge = BridgeTable(config)
    await bridge.connect()

    yield bridge

    await bridge.close()


@pytest.fixture
def sample_mappings():
    """Create sample BridgeMapping objects from ingestion pipeline."""
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    return [
        # PRIMARY mapping - chunk to article
        BridgeMapping(
            chunk_id=chunk_id_1,
            graph_node_urn="urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453",
            mapping_type="PRIMARY",
            confidence=1.0,
            metadata={"comma": 1}
        ),
        # HIERARCHIC mapping - chunk to libro
        BridgeMapping(
            chunk_id=chunk_id_1,
            graph_node_urn="urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4",
            mapping_type="HIERARCHIC",
            confidence=0.95,
            metadata={"level": "libro"}
        ),
        # PRIMARY mapping - second chunk
        BridgeMapping(
            chunk_id=chunk_id_2,
            graph_node_urn="urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453",
            mapping_type="PRIMARY",
            confidence=1.0,
            metadata={"comma": 2}
        ),
        # CONCEPT mapping
        BridgeMapping(
            chunk_id=chunk_id_1,
            graph_node_urn="urn:concept:risoluzione_contratto",
            mapping_type="CONCEPT",
            confidence=0.85,
            metadata={"extracted_from": "rubrica"}
        ),
        # DOCTRINE mapping
        BridgeMapping(
            chunk_id=chunk_id_1,
            graph_node_urn="urn:dottrina:brocardi:art1453:ratio",
            mapping_type="DOCTRINE",
            confidence=0.9,
            metadata={"source": "brocardi"}
        ),
        # JURISPRUDENCE mapping
        BridgeMapping(
            chunk_id=chunk_id_2,
            graph_node_urn="urn:giurisprudenza:cassazione:15353/2020",
            mapping_type="JURISPRUDENCE",
            confidence=0.88,
            metadata={"corte": "Cassazione", "numero": "15353/2020"}
        ),
    ], chunk_id_1, chunk_id_2


class TestBridgeBuilderConversion:
    """Test BridgeMapping to Bridge Table format conversion (no DB)."""

    def test_convert_primary_mapping(self, bridge_table):
        """Test conversion of PRIMARY mapping type."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:nir:...~art1453",
            mapping_type="PRIMARY",
            confidence=1.0,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["chunk_id"] == mapping.chunk_id
        assert converted["graph_node_urn"] == mapping.graph_node_urn
        assert converted["node_type"] == "Norma"
        assert converted["relation_type"] == "contained_in"
        assert converted["confidence"] == 1.0
        assert converted["source"] == "ingestion_v2"

    def test_convert_hierarchic_mapping(self, bridge_table):
        """Test conversion of HIERARCHIC mapping type."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:nir:...~libro4",
            mapping_type="HIERARCHIC",
            confidence=0.95,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["node_type"] == "Norma"
        assert converted["relation_type"] == "part_of"
        assert converted["confidence"] == 0.95

    def test_convert_concept_mapping(self, bridge_table):
        """Test conversion of CONCEPT mapping type."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:concept:risoluzione",
            mapping_type="CONCEPT",
            confidence=0.85,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["node_type"] == "ConcettoGiuridico"
        assert converted["relation_type"] == "relates_to"

    def test_convert_doctrine_mapping(self, bridge_table):
        """Test conversion of DOCTRINE mapping type."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:dottrina:...",
            mapping_type="DOCTRINE",
            confidence=0.9,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["node_type"] == "Dottrina"
        assert converted["relation_type"] == "commented_by"

    def test_convert_jurisprudence_mapping(self, bridge_table):
        """Test conversion of JURISPRUDENCE mapping type."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:giurisprudenza:...",
            mapping_type="JURISPRUDENCE",
            confidence=0.88,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["node_type"] == "AttoGiudiziario"
        assert converted["relation_type"] == "interpreted_by"

    def test_convert_unknown_mapping_type(self, bridge_table):
        """Test conversion of unknown mapping type defaults to Unknown."""
        builder = BridgeBuilder(bridge_table)

        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:unknown:...",
            mapping_type="UNKNOWN_TYPE",
            confidence=0.5,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["node_type"] == "Unknown"
        assert converted["relation_type"] == "unknown"

    def test_convert_preserves_metadata(self, bridge_table):
        """Test that metadata is preserved in conversion."""
        builder = BridgeBuilder(bridge_table)

        metadata = {"comma": 1, "source": "test", "extra": "data"}
        mapping = BridgeMapping(
            chunk_id=uuid4(),
            graph_node_urn="urn:nir:...~art1453",
            mapping_type="PRIMARY",
            confidence=1.0,
            metadata=metadata,
        )

        converted = builder.convert_mapping(mapping)

        assert converted["metadata"] == metadata

    def test_convert_batch(self, bridge_table):
        """Test batch conversion of multiple mappings."""
        builder = BridgeBuilder(bridge_table)

        mappings = [
            BridgeMapping(
                chunk_id=uuid4(),
                graph_node_urn="urn:1",
                mapping_type="PRIMARY",
                confidence=1.0,
            ),
            BridgeMapping(
                chunk_id=uuid4(),
                graph_node_urn="urn:2",
                mapping_type="CONCEPT",
                confidence=0.8,
            ),
        ]

        converted = builder.convert_batch(mappings)

        assert len(converted) == 2
        assert converted[0]["node_type"] == "Norma"
        assert converted[1]["node_type"] == "ConcettoGiuridico"


@pytest.mark.asyncio
class TestBridgeBuilderInsert:
    """Integration tests for Bridge Table insertion."""

    async def test_insert_single_mapping(self, bridge_table, sample_mappings):
        """Test inserting a single mapping into Bridge Table."""
        mappings, chunk_id_1, chunk_id_2 = sample_mappings
        builder = BridgeBuilder(bridge_table)

        # Insert first mapping
        entry_id = await builder.insert_mapping(mappings[0])

        assert entry_id > 0

        # Verify in database
        nodes = await bridge_table.get_nodes_for_chunk(chunk_id_1)
        assert len(nodes) >= 1

        # Cleanup
        await bridge_table.delete_mappings_for_chunk(chunk_id_1)

    async def test_insert_multiple_mappings(self, bridge_table, sample_mappings):
        """Test batch insertion of multiple mappings."""
        mappings, chunk_id_1, chunk_id_2 = sample_mappings
        builder = BridgeBuilder(bridge_table)

        # Insert all mappings
        total = await builder.insert_mappings(mappings)

        assert total == 6

        # Verify chunk 1 has 4 mappings (PRIMARY, HIERARCHIC, CONCEPT, DOCTRINE)
        nodes_1 = await bridge_table.get_nodes_for_chunk(chunk_id_1)
        assert len(nodes_1) == 4

        # Verify chunk 2 has 2 mappings (PRIMARY, JURISPRUDENCE)
        nodes_2 = await bridge_table.get_nodes_for_chunk(chunk_id_2)
        assert len(nodes_2) == 2

        # Cleanup
        await bridge_table.delete_mappings_for_chunk(chunk_id_1)
        await bridge_table.delete_mappings_for_chunk(chunk_id_2)

    async def test_insert_empty_list(self, bridge_table):
        """Test inserting empty list returns 0."""
        builder = BridgeBuilder(bridge_table)

        total = await builder.insert_mappings([])

        assert total == 0

    async def test_insert_with_custom_batch_size(self, bridge_table):
        """Test insertion with custom batch size."""
        builder = BridgeBuilder(bridge_table)
        chunk_ids = []

        # Create 5 mappings
        mappings = []
        for i in range(5):
            chunk_id = uuid4()
            chunk_ids.append(chunk_id)
            mappings.append(BridgeMapping(
                chunk_id=chunk_id,
                graph_node_urn=f"urn:test:norma:{i}",
                mapping_type="PRIMARY",
                confidence=1.0,
            ))

        # Insert with batch size of 2 (should create 3 batches)
        total = await builder.insert_mappings(mappings, batch_size=2)

        assert total == 5

        # Cleanup
        for chunk_id in chunk_ids:
            await bridge_table.delete_mappings_for_chunk(chunk_id)

    async def test_insert_verifies_node_types(self, bridge_table, sample_mappings):
        """Test that different node types are correctly stored."""
        mappings, chunk_id_1, chunk_id_2 = sample_mappings
        builder = BridgeBuilder(bridge_table)

        await builder.insert_mappings(mappings)

        # Check Norma nodes for chunk 1 (PRIMARY + HIERARCHIC)
        norma_nodes = await bridge_table.get_nodes_for_chunk(
            chunk_id_1, node_type="Norma"
        )
        assert len(norma_nodes) == 2

        # Check ConcettoGiuridico nodes for chunk 1
        concetto_nodes = await bridge_table.get_nodes_for_chunk(
            chunk_id_1, node_type="ConcettoGiuridico"
        )
        assert len(concetto_nodes) == 1

        # Check Dottrina nodes for chunk 1
        dottrina_nodes = await bridge_table.get_nodes_for_chunk(
            chunk_id_1, node_type="Dottrina"
        )
        assert len(dottrina_nodes) == 1

        # Check AttoGiudiziario nodes for chunk 2
        atto_nodes = await bridge_table.get_nodes_for_chunk(
            chunk_id_2, node_type="AttoGiudiziario"
        )
        assert len(atto_nodes) == 1

        # Cleanup
        await bridge_table.delete_mappings_for_chunk(chunk_id_1)
        await bridge_table.delete_mappings_for_chunk(chunk_id_2)


@pytest.mark.asyncio
class TestConvenienceFunction:
    """Test insert_ingestion_result convenience function."""

    async def test_insert_ingestion_result(self, bridge_table):
        """Test convenience function for inserting ingestion results."""
        chunk_id = uuid4()

        mappings = [
            BridgeMapping(
                chunk_id=chunk_id,
                graph_node_urn="urn:nir:...~art1453",
                mapping_type="PRIMARY",
                confidence=1.0,
            ),
            BridgeMapping(
                chunk_id=chunk_id,
                graph_node_urn="urn:nir:...~libro4",
                mapping_type="HIERARCHIC",
                confidence=0.95,
            ),
        ]

        count = await insert_ingestion_result(bridge_table, mappings)

        assert count == 2

        # Verify
        nodes = await bridge_table.get_nodes_for_chunk(chunk_id)
        assert len(nodes) == 2

        # Cleanup
        await bridge_table.delete_mappings_for_chunk(chunk_id)
