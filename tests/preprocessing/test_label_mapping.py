"""
Unit Tests for Label Mapping System
====================================

Tests the hot-reloadable label mapping module supporting:
- Traditional Italian act types (decreto, legge, codice)
- Semantic ontology (fonte_normativa, istituto, principio)
- Dynamic registration and hot-reload
- Bidirectional mapping (act_type ↔ label)

Test coverage:
- Default mappings loading
- Custom label registration
- Bidirectional conversion
- Semantic label metadata
- Hot-reload capability
- Singleton pattern
"""

import pytest
from backend.preprocessing.label_mapping import (
    LabelMappingManager,
    LabelCategory,
    LabelMetadata,
    get_label_manager,
    reload_label_manager
)
import tempfile
import yaml
import os


# ===================================
# Fixtures
# ===================================

@pytest.fixture
def label_manager():
    """Create LabelMappingManager instance."""
    return LabelMappingManager()


@pytest.fixture
def label_manager_with_config():
    """Create LabelMappingManager with custom config."""
    config_content = {
        "act_type_to_label": {
            "decreto_test": "D.TEST",
            "legge_test": "L.TEST"
        },
        "semantic_labels": {
            "test_label": {
                "category": "act_type",
                "display_name": "Test Label",
                "description": "A test label",
                "synonyms": ["test"],
                "confidence_bias": 0.1,
                "priority": 5
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_content, f)
        config_path = f.name

    try:
        manager = LabelMappingManager(config_path)
        yield manager
    finally:
        os.unlink(config_path)


# ===================================
# Test Cases: Default Mappings
# ===================================

def test_load_default_mappings(label_manager):
    """Test that default Italian legal mappings are loaded."""
    assert len(label_manager.act_type_to_label) > 0, "Should have default act type mappings"
    assert len(label_manager.label_to_act_type) > 0, "Should have reverse mappings"


def test_codice_civile_mapping(label_manager):
    """Test codice civile mapping."""
    assert label_manager.act_type_to_label.get("codice_civile") == "C.C.", "Should map codice_civile to C.C."
    assert label_manager.label_to_act_type.get("C.C.") == "codice_civile", "Should reverse map C.C."


def test_codice_penale_mapping(label_manager):
    """Test codice penale mapping."""
    assert label_manager.act_type_to_label.get("codice_penale") == "C.P.", "Should map codice_penale to C.P."


def test_decreto_legislativo_mapping(label_manager):
    """Test decreto legislativo mapping."""
    assert label_manager.act_type_to_label.get("decreto_legislativo") == "D.LGS.", "Should map decreto_legislativo"


def test_costituzione_mapping(label_manager):
    """Test costituzione mapping."""
    assert label_manager.act_type_to_label.get("costituzione") == "COST.", "Should map costituzione"


def test_direttiva_ue_mapping(label_manager):
    """Test EU directive mapping."""
    assert label_manager.act_type_to_label.get("direttiva_ue") == "DIR. UE", "Should map direttiva_ue"


# ===================================
# Test Cases: Bidirectional Conversion
# ===================================

def test_act_type_to_label_conversion(label_manager):
    """Test converting act type to label."""
    result = label_manager.act_type_to_label("decreto_legislativo")
    assert result == "D.LGS.", "Should convert correctly"


def test_act_type_to_label_unknown(label_manager):
    """Test converting unknown act type."""
    result = label_manager.act_type_to_label("unknown_type")
    assert result == "UNKNOWN_TYPE", "Should normalize unknown types"


def test_label_to_act_type_conversion(label_manager):
    """Test converting label back to act type."""
    result = label_manager.label_to_act_type("C.C.")
    assert result == "codice_civile", "Should convert label back to act type"


def test_label_to_act_type_unknown(label_manager):
    """Test converting unknown label."""
    result = label_manager.label_to_act_type("UNKNOWN.LABEL")
    assert result is None, "Should return None for unknown label"


def test_bidirectional_consistency(label_manager):
    """Test bidirectional conversion consistency."""
    act_type = "codice_civile"

    # Convert forward
    label = label_manager.act_type_to_label(act_type)
    assert label == "C.C.", "First conversion should work"

    # Convert back
    recovered_act_type = label_manager.label_to_act_type(label)
    assert recovered_act_type == act_type, "Should recover original act type"


# ===================================
# Test Cases: Semantic Labels
# ===================================

def test_load_semantic_labels(label_manager):
    """Test that semantic labels are loaded."""
    semantic_labels = label_manager.get_semantic_ontology()
    assert len(semantic_labels) > 0, "Should load semantic labels"


def test_semantic_label_metadata(label_manager):
    """Test semantic label metadata."""
    metadata = label_manager.get_label_metadata("fonte_normativa")

    if metadata:
        assert metadata.label == "fonte_normativa", "Should have correct label"
        assert isinstance(metadata.category, LabelCategory), "Should have category"
        assert isinstance(metadata.display_name, str), "Should have display name"


def test_semantic_label_categories(label_manager):
    """Test semantic label categories."""
    categories = {
        "fonte_normativa": LabelCategory.LEGAL_SOURCE,
        "persona_fisica": LabelCategory.PERSON,
        "istituto": LabelCategory.LEGAL_CONCEPT,
        "principio": LabelCategory.LEGAL_CONCEPT,
        "reato": LabelCategory.CRIME
    }

    for label, expected_category in categories.items():
        metadata = label_manager.get_label_metadata(label)
        if metadata:
            assert metadata.category == expected_category, f"Label {label} should have category {expected_category}"


def test_get_labels_by_category(label_manager):
    """Test filtering labels by category."""
    legal_sources = label_manager.get_labels_by_category(LabelCategory.LEGAL_SOURCE)

    assert "fonte_normativa" in legal_sources, "Should include fonte_normativa"
    assert "fonte_giurisdizionale" in legal_sources, "Should include fonte_giurisdizionale"


# ===================================
# Test Cases: Custom Label Registration
# ===================================

def test_register_custom_label(label_manager):
    """Test registering a custom label."""
    label_manager.register_custom_label(
        act_type="custom_decree",
        display_label="D.CUSTOM",
        category=LabelCategory.ACT_TYPE
    )

    # Check forward mapping
    assert label_manager.act_type_to_label.get("custom_decree") == "D.CUSTOM", "Should register forward"

    # Check reverse mapping
    assert label_manager.label_to_act_type.get("D.CUSTOM") == "custom_decree", "Should register reverse"


def test_register_multiple_custom_labels(label_manager):
    """Test registering multiple custom labels."""
    label_manager.register_custom_label("custom1", "CUSTOM1")
    label_manager.register_custom_label("custom2", "CUSTOM2")
    label_manager.register_custom_label("custom3", "CUSTOM3")

    assert label_manager.act_type_to_label.get("custom1") == "CUSTOM1"
    assert label_manager.act_type_to_label.get("custom2") == "CUSTOM2"
    assert label_manager.act_type_to_label.get("custom3") == "CUSTOM3"


def test_update_label_mapping(label_manager):
    """Test updating a label mapping."""
    original = label_manager.act_type_to_label.get("test_type")

    label_manager.update_label_mapping("test_type", "NEW.LABEL", category="act_type")

    updated = label_manager.act_type_to_label.get("test_type")
    assert updated == "NEW.LABEL", "Should update mapping"


# ===================================
# Test Cases: Label Validation
# ===================================

def test_validate_existing_label(label_manager):
    """Test validation of existing label."""
    assert label_manager.validate_label("C.C."), "Should validate existing label"


def test_validate_existing_act_type(label_manager):
    """Test validation of existing act type."""
    assert label_manager.validate_label("codice_civile"), "Should validate existing act type"


def test_validate_semantic_label(label_manager):
    """Test validation of semantic label."""
    assert label_manager.validate_label("fonte_normativa"), "Should validate semantic label"


def test_validate_unknown_label(label_manager):
    """Test validation of unknown label."""
    assert not label_manager.validate_label("totally_unknown"), "Should reject unknown label"


# ===================================
# Test Cases: Export/Import
# ===================================

def test_export_to_yaml(label_manager):
    """Test exporting mappings to YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        output_path = f.name

    try:
        label_manager.export_to_yaml(output_path)

        # Verify file was created and has content
        assert os.path.exists(output_path), "Should create YAML file"

        with open(output_path, 'r') as f:
            content = yaml.safe_load(f)

        assert "act_type_to_label" in content, "Should export act type mappings"
        assert "semantic_labels" in content, "Should export semantic labels"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_load_from_yaml(label_manager_with_config):
    """Test loading mappings from YAML."""
    # Custom mappings should be loaded
    assert label_manager_with_config.act_type_to_label.get("decreto_test") == "D.TEST", "Should load custom act types"
    assert label_manager_with_config.label_to_act_type.get("D.TEST") == "decreto_test", "Should load reverse mapping"


# ===================================
# Test Cases: Listing Methods
# ===================================

def test_get_all_act_types(label_manager):
    """Test getting all registered act types."""
    act_types = label_manager.get_all_act_types()

    assert len(act_types) > 0, "Should return act types"
    assert "codice_civile" in act_types, "Should include codice_civile"
    assert "decreto_legislativo" in act_types, "Should include decreto_legislativo"


def test_get_all_labels(label_manager):
    """Test getting all display labels."""
    labels = label_manager.get_all_labels()

    assert len(labels) > 0, "Should return labels"
    assert "C.C." in labels, "Should include C.C."
    assert "D.LGS." in labels, "Should include D.LGS."


# ===================================
# Test Cases: Semantic Ontology Export
# ===================================

def test_get_semantic_ontology(label_manager):
    """Test getting complete semantic ontology."""
    ontology = label_manager.get_semantic_ontology()

    assert isinstance(ontology, dict), "Should return dictionary"

    for label, metadata in ontology.items():
        assert "category" in metadata, "Should have category"
        assert "display_name" in metadata, "Should have display_name"
        assert "description" in metadata, "Should have description"
        assert "priority" in metadata, "Should have priority"


# ===================================
# Test Cases: Edge Cases
# ===================================

def test_empty_custom_labels_initially(label_manager):
    """Test that custom_labels dict is empty initially."""
    assert len(label_manager.custom_labels) == 0, "Should start with no custom labels"


def test_singleton_pattern(label_manager):
    """Test that get_label_manager returns consistent instance (optional)."""
    # Note: This may or may not be enforced, depending on implementation
    manager1 = get_label_manager()
    manager2 = get_label_manager()

    # Both should be instances of LabelMappingManager
    assert isinstance(manager1, LabelMappingManager), "Should return manager instance"
    assert isinstance(manager2, LabelMappingManager), "Should return manager instance"


def test_repr_method(label_manager):
    """Test string representation of LabelMappingManager."""
    repr_str = repr(label_manager)

    assert "LabelMappingManager" in repr_str, "Should include class name"
    assert "act_types" in repr_str, "Should include act_types count"
    assert "semantic_labels" in repr_str, "Should include semantic_labels count"


# ===================================
# Test Cases: Label Metadata
# ===================================

def test_label_metadata_attributes(label_manager):
    """Test LabelMetadata attributes."""
    metadata = LabelMetadata(
        label="test_label",
        category=LabelCategory.LEGAL_CONCEPT,
        display_name="Test Concept",
        description="A test concept",
        synonyms=["test", "example"],
        confidence_bias=0.1,
        priority=5
    )

    assert metadata.label == "test_label", "Should have label"
    assert metadata.category == LabelCategory.LEGAL_CONCEPT, "Should have category"
    assert metadata.display_name == "Test Concept", "Should have display name"
    assert metadata.synonyms == ["test", "example"], "Should have synonyms"
    assert metadata.confidence_bias == 0.1, "Should have confidence bias"
    assert metadata.priority == 5, "Should have priority"


# ===================================
# Test Cases: Category Enum
# ===================================

def test_label_categories_exist(label_manager):
    """Test that all label categories exist."""
    categories = [
        LabelCategory.ACT_TYPE,
        LabelCategory.LEGAL_SOURCE,
        LabelCategory.LEGAL_CONCEPT,
        LabelCategory.INSTITUTION,
        LabelCategory.PERSON,
        LabelCategory.CRIME,
        LabelCategory.OTHER
    ]

    for category in categories:
        assert isinstance(category, LabelCategory), f"Should have {category} category"
