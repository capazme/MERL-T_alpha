"""
Test BridgeMapping Model
========================

Unit tests for the BridgeMapping dataclass.
"""

import pytest
from uuid import uuid4, UUID
from dataclasses import asdict

from merlt.models import BridgeMapping


class TestBridgeMapping:
    """Test BridgeMapping dataclass."""

    def test_create_basic_mapping(self):
        """Test creating a basic mapping with required fields."""
        chunk_id = uuid4()
        mapping = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn="urn:nir:stato:codice.civile:1942~art1453",
            mapping_type="PRIMARY",
            confidence=1.0
        )

        assert mapping.chunk_id == chunk_id
        assert mapping.graph_node_urn == "urn:nir:stato:codice.civile:1942~art1453"
        assert mapping.mapping_type == "PRIMARY"
        assert mapping.confidence == 1.0
        assert mapping.metadata is None

    def test_create_mapping_with_metadata(self):
        """Test creating a mapping with metadata."""
        chunk_id = uuid4()
        metadata = {"source": "brocardi", "level": "article"}
        mapping = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn="urn:test",
            mapping_type="HIERARCHIC",
            confidence=0.95,
            metadata=metadata
        )

        assert mapping.metadata == metadata
        assert mapping.metadata["source"] == "brocardi"

    def test_mapping_types(self):
        """Test all valid mapping types."""
        valid_types = ["PRIMARY", "HIERARCHIC", "CONCEPT", "REFERENCE"]
        chunk_id = uuid4()

        for mapping_type in valid_types:
            mapping = BridgeMapping(
                chunk_id=chunk_id,
                graph_node_urn=f"urn:test:{mapping_type.lower()}",
                mapping_type=mapping_type,
                confidence=0.8
            )
            assert mapping.mapping_type == mapping_type

    def test_confidence_range(self):
        """Test confidence values."""
        chunk_id = uuid4()

        # Valid confidence values
        for conf in [0.0, 0.5, 1.0, 0.95, 0.01]:
            mapping = BridgeMapping(
                chunk_id=chunk_id,
                graph_node_urn="urn:test",
                mapping_type="PRIMARY",
                confidence=conf
            )
            assert mapping.confidence == conf

    def test_uuid_handling(self):
        """Test that chunk_id properly handles UUID objects."""
        # Create from UUID
        chunk_id = uuid4()
        mapping = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn="urn:test",
            mapping_type="PRIMARY",
            confidence=1.0
        )

        assert isinstance(mapping.chunk_id, UUID)
        assert str(mapping.chunk_id) == str(chunk_id)

    def test_asdict_conversion(self):
        """Test conversion to dictionary."""
        chunk_id = uuid4()
        metadata = {"key": "value"}
        mapping = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn="urn:test:dict",
            mapping_type="PRIMARY",
            confidence=0.9,
            metadata=metadata
        )

        as_dict = asdict(mapping)

        assert as_dict["chunk_id"] == chunk_id
        assert as_dict["graph_node_urn"] == "urn:test:dict"
        assert as_dict["mapping_type"] == "PRIMARY"
        assert as_dict["confidence"] == 0.9
        assert as_dict["metadata"] == metadata

    def test_equality(self):
        """Test equality comparison."""
        chunk_id = uuid4()
        urn = "urn:test:equality"

        mapping1 = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn=urn,
            mapping_type="PRIMARY",
            confidence=1.0
        )
        mapping2 = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn=urn,
            mapping_type="PRIMARY",
            confidence=1.0
        )

        assert mapping1 == mapping2

    def test_inequality_different_confidence(self):
        """Test inequality with different confidence."""
        chunk_id = uuid4()
        urn = "urn:test:inequality"

        mapping1 = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn=urn,
            mapping_type="PRIMARY",
            confidence=1.0
        )
        mapping2 = BridgeMapping(
            chunk_id=chunk_id,
            graph_node_urn=urn,
            mapping_type="PRIMARY",
            confidence=0.5
        )

        assert mapping1 != mapping2

    def test_import_from_merlt_models(self):
        """Test that BridgeMapping can be imported from merlt.models."""
        from merlt.models import BridgeMapping as BM
        assert BM is BridgeMapping

    def test_import_from_pipeline_ingestion(self):
        """Test backward compatibility: BridgeMapping available from pipeline."""
        from merlt.pipeline.ingestion import BridgeMapping as BM
        from merlt.models import BridgeMapping

        # Both should be the same class
        assert BM is BridgeMapping

    def test_import_from_bridge_builder(self):
        """Test that bridge_builder uses the centralized BridgeMapping."""
        from merlt.storage.bridge.bridge_builder import BridgeMapping as BM
        from merlt.models import BridgeMapping

        assert BM is BridgeMapping
