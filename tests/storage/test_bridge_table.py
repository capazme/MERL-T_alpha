"""
Test Bridge Table
==================

Test CRUD operations on the Bridge Table.
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from merlt.storage.bridge import BridgeTable, BridgeTableConfig


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

    # Cleanup: delete test data
    await bridge.close()


@pytest.mark.asyncio
async def test_health_check(bridge_table):
    """Test PostgreSQL connection health check."""
    healthy = await bridge_table.health_check()
    assert healthy is True


@pytest.mark.asyncio
async def test_add_single_mapping(bridge_table):
    """Test adding a single chunk-to-node mapping."""
    chunk_id = uuid4()
    node_urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"

    entry_id = await bridge_table.add_mapping(
        chunk_id=chunk_id,
        graph_node_urn=node_urn,
        node_type="Norma",
        relation_type="contained_in",
        confidence=1.0,
        source="test"
    )

    assert entry_id > 0

    # Verify retrieval
    nodes = await bridge_table.get_nodes_for_chunk(chunk_id)
    assert len(nodes) == 1
    assert nodes[0]["graph_node_urn"] == node_urn
    assert nodes[0]["node_type"] == "Norma"
    assert nodes[0]["confidence"] == 1.0

    # Cleanup
    deleted = await bridge_table.delete_mappings_for_chunk(chunk_id)
    assert deleted == 1


@pytest.mark.asyncio
async def test_batch_insert(bridge_table):
    """Test batch insertion of multiple mappings."""
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    mappings = [
        {
            "chunk_id": chunk_id_1,
            "graph_node_urn": "urn:test:norma:1",
            "node_type": "Norma",
            "confidence": 1.0,
            "source": "test"
        },
        {
            "chunk_id": chunk_id_1,
            "graph_node_urn": "urn:test:concetto:1",
            "node_type": "ConcettoGiuridico",
            "relation_type": "references",
            "confidence": 0.8,
            "source": "test"
        },
        {
            "chunk_id": chunk_id_2,
            "graph_node_urn": "urn:test:norma:2",
            "node_type": "Norma",
            "confidence": 1.0,
            "source": "test"
        },
    ]

    count = await bridge_table.add_mappings_batch(mappings)
    assert count == 3

    # Verify chunk 1 has 2 nodes
    nodes = await bridge_table.get_nodes_for_chunk(chunk_id_1)
    assert len(nodes) == 2

    # Verify chunk 2 has 1 node
    nodes = await bridge_table.get_nodes_for_chunk(chunk_id_2)
    assert len(nodes) == 1

    # Cleanup
    await bridge_table.delete_mappings_for_chunk(chunk_id_1)
    await bridge_table.delete_mappings_for_chunk(chunk_id_2)


@pytest.mark.asyncio
async def test_get_chunks_for_node(bridge_table):
    """Test retrieving all chunks that reference a node."""
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()
    node_urn = "urn:test:norma:shared"

    # Add two chunks referencing same node
    await bridge_table.add_mapping(
        chunk_id=chunk_id_1,
        graph_node_urn=node_urn,
        node_type="Norma",
        chunk_text="First chunk text",
        source="test"
    )

    await bridge_table.add_mapping(
        chunk_id=chunk_id_2,
        graph_node_urn=node_urn,
        node_type="Norma",
        chunk_text="Second chunk text",
        source="test"
    )

    # Get all chunks for node
    chunks = await bridge_table.get_chunks_for_node(node_urn)
    assert len(chunks) == 2

    chunk_ids = [c["chunk_id"] for c in chunks]
    assert str(chunk_id_1) in chunk_ids
    assert str(chunk_id_2) in chunk_ids

    # Cleanup
    await bridge_table.delete_mappings_for_chunk(chunk_id_1)
    await bridge_table.delete_mappings_for_chunk(chunk_id_2)


@pytest.mark.asyncio
async def test_filter_by_node_type(bridge_table):
    """Test filtering nodes by type."""
    chunk_id = uuid4()

    mappings = [
        {
            "chunk_id": chunk_id,
            "graph_node_urn": "urn:test:norma:1",
            "node_type": "Norma",
            "source": "test"
        },
        {
            "chunk_id": chunk_id,
            "graph_node_urn": "urn:test:concetto:1",
            "node_type": "ConcettoGiuridico",
            "source": "test"
        },
    ]

    await bridge_table.add_mappings_batch(mappings)

    # Get only Norma nodes
    norma_nodes = await bridge_table.get_nodes_for_chunk(chunk_id, node_type="Norma")
    assert len(norma_nodes) == 1
    assert norma_nodes[0]["node_type"] == "Norma"

    # Get only ConcettoGiuridico nodes
    concetto_nodes = await bridge_table.get_nodes_for_chunk(chunk_id, node_type="ConcettoGiuridico")
    assert len(concetto_nodes) == 1
    assert concetto_nodes[0]["node_type"] == "ConcettoGiuridico"

    # Cleanup
    await bridge_table.delete_mappings_for_chunk(chunk_id)
