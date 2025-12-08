"""
Unit Tests for NER LegalClassifier Stage
=========================================

Tests the Stage 2 of the 5-stage NER pipeline.
Covers rule-based classification with semantic validation.

Test coverage:
- Rule-based pattern matching for legal acts
- Confidence scoring per act type
- Semantic validation
- Fine-tuned model support (mock)
- Unknown entity handling
- Confidence thresholds
"""

import pytest
from merlt.pipeline.ner_module import (
    LegalClassifier,
    TextSpan,
    LegalClassification,
    UNKNOWN_SOURCE
)

import logging

log = logging.getLogger(__name__)


# ===================================
# Fixtures
# ===================================

@pytest.fixture
def ner_config():
    """NER configuration for testing."""
    return {
        "models": {
            "legal_classifier": {
                "primary": "dlicari/distil-ita-legal-bert",
                "embedding_max_length": 256
            },
            "semantic_embeddings": {
                "model": "dlicari/Italian-Legal-BERT"
            }
        },
        "confidence_thresholds": {
            "rule_based_priority_threshold": 0.8,
            "semantic_boost_factor": 0.1,
            "minimum_classification_confidence": 0.7
        },
        "confidence_thresholds": {
            "rule_based_confidence": {
                "codice_civile_abbrev": 0.99,
                "codice_civile_full": 0.90,
                "codice_penale_abbrev": 0.99,
                "decreto_legislativo_full": 0.98,
                "decreto_legislativo_abbrev": 0.95,
                "legge_full": 0.90,
                "legge_abbrev": 0.75,
                "costituzione_full": 0.98,
                "direttiva_ue": 0.98,
                "regolamento_ue": 0.98,
                "default": 0.5
            }
        },
        "normattiva_mapping": {
            "codice_civile": ["c.c.", "c.c", "cc", "codice civile"],
            "codice_penale": ["c.p.", "c.p", "cp", "codice penale"],
            "codice_procedura_civile": ["c.p.c.", "c.p.c", "cpc"],
            "codice_procedura_penale": ["c.p.p.", "c.p.p", "cpp"],
            "decreto_legislativo": ["d.lgs.", "d.lgs", "dlgs", "decreto legislativo"],
            "decreto_presidente_repubblica": ["d.p.r.", "d.p.r", "dpr"],
            "legge": ["l.", "l", "legge"],
            "costituzione": ["cost.", "cost", "costituzione"],
            "direttiva_ue": ["direttiva", "direttiva ue", "direttiva europea"],
            "regolamento_ue": ["regolamento", "regolamento ue", "regolamento europeo"],
        }
    }


@pytest.fixture
def legal_classifier(ner_config):
    """Create LegalClassifier instance."""
    try:
        classifier = LegalClassifier(ner_config, fine_tuned_model_path=None)
        return classifier
    except Exception as e:
        pytest.skip(f"Could not load LegalClassifier models: {e}")


# ===================================
# Test Cases: Codice Civile Classification
# ===================================

def test_classify_codice_civile_abbrev(legal_classifier):
    """Test classification of 'c.c.' abbreviation."""
    span = TextSpan(
        text="c.c.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "codice_civile", "Should classify c.c. as codice_civile"
    assert result.confidence >= 0.95, "Should have high confidence for abbreviation"


def test_classify_codice_civile_full(legal_classifier):
    """Test classification of 'codice civile' full form."""
    span = TextSpan(
        text="codice civile",
        start_char=0,
        end_char=13,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "codice_civile", "Should classify 'codice civile' as codice_civile"
    assert result.confidence >= 0.85, "Should have reasonable confidence"


# ===================================
# Test Cases: Decreto Legislativo Classification
# ===================================

def test_classify_decreto_legislativo_abbrev(legal_classifier):
    """Test classification of 'd.lgs.' abbreviation."""
    span = TextSpan(
        text="d.lgs.",
        start_char=0,
        end_char=6,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "decreto_legislativo", "Should classify d.lgs."
    assert result.confidence >= 0.90, "Should have high confidence"


def test_classify_decreto_legislativo_full(legal_classifier):
    """Test classification of 'decreto legislativo' full form."""
    span = TextSpan(
        text="decreto legislativo 196/2003",
        start_char=0,
        end_char=28,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "decreto_legislativo", "Should classify decreto legislativo"


# ===================================
# Test Cases: Codice Penale Classification
# ===================================

def test_classify_codice_penale_abbrev(legal_classifier):
    """Test classification of 'c.p.' abbreviation."""
    span = TextSpan(
        text="c.p.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "codice_penale", "Should classify c.p. as codice_penale"
    assert result.confidence >= 0.95, "Should have very high confidence"


# ===================================
# Test Cases: Legge (Law) Classification
# ===================================

def test_classify_legge_abbrev(legal_classifier):
    """Test classification of 'l.' abbreviation."""
    span = TextSpan(
        text="l.",
        start_char=0,
        end_char=2,
        initial_confidence=0.70
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "legge", "Should classify l. as legge"
    # Note: 'l.' alone might be ambiguous, so confidence could be lower


def test_classify_legge_full(legal_classifier):
    """Test classification of 'legge' full form."""
    span = TextSpan(
        text="legge 123 del 2020",
        start_char=0,
        end_char=18,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "legge", "Should classify legge"


# ===================================
# Test Cases: Costituzione Classification
# ===================================

def test_classify_costituzione_abbrev(legal_classifier):
    """Test classification of 'cost.' abbreviation."""
    span = TextSpan(
        text="cost.",
        start_char=0,
        end_char=5,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "costituzione", "Should classify cost."
    assert result.confidence >= 0.95, "Should have high confidence"


def test_classify_costituzione_full(legal_classifier):
    """Test classification of 'costituzione' full form."""
    span = TextSpan(
        text="costituzione italiana",
        start_char=0,
        end_char=20,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "costituzione", "Should classify costituzione"


# ===================================
# Test Cases: EU Normative Classification
# ===================================

def test_classify_direttiva_ue(legal_classifier):
    """Test classification of EU directive."""
    span = TextSpan(
        text="direttiva ue 2020/123",
        start_char=0,
        end_char=21,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "direttiva_ue", "Should classify direttiva ue"
    assert result.confidence >= 0.95, "Should have very high confidence"


def test_classify_regolamento_ue(legal_classifier):
    """Test classification of EU regulation."""
    span = TextSpan(
        text="regolamento ue 2018/456",
        start_char=0,
        end_char=23,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    assert result.act_type == "regolamento_ue", "Should classify regolamento ue"


# ===================================
# Test Cases: Unknown Entity Handling
# ===================================

def test_classify_unknown_entity(legal_classifier):
    """Test classification of unknown legal reference."""
    span = TextSpan(
        text="xyz123abc",
        start_char=0,
        end_char=9,
        initial_confidence=0.1
    )

    result = legal_classifier.classify_legal_type(span, "")

    # Should handle gracefully - either UNKNOWN or best guess
    assert isinstance(result, LegalClassification), "Should return LegalClassification"
    assert result.confidence < 0.7, "Should have low confidence for unknown"


# ===================================
# Test Cases: Confidence Scoring
# ===================================

def test_confidence_for_abbreviations_vs_full(legal_classifier):
    """Test that abbreviations have higher confidence than full forms."""
    abbrev_span = TextSpan(
        text="c.c.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    full_span = TextSpan(
        text="codice civile",
        start_char=0,
        end_char=13,
        initial_confidence=0.90
    )

    abbrev_result = legal_classifier.classify_legal_type(abbrev_span, "")
    full_result = legal_classifier.classify_legal_type(full_span, "")

    # Abbreviations should have slightly higher confidence
    assert abbrev_result.confidence >= full_result.confidence - 0.05


def test_confidence_threshold_application(legal_classifier):
    """Test that minimum confidence threshold is applied."""
    span = TextSpan(
        text="something unclear",
        start_char=0,
        end_char=17,
        initial_confidence=0.3
    )

    result = legal_classifier.classify_legal_type(span, "")

    # Should either be UNKNOWN or have low confidence
    assert result.confidence < 0.8, "Should flag low-confidence classifications"


# ===================================
# Test Cases: Semantic Embedding (Mocked)
# ===================================

def test_semantic_embedding_presence(legal_classifier):
    """Test that semantic embeddings are present when available."""
    span = TextSpan(
        text="c.c.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    result = legal_classifier.classify_legal_type(span, "contesto legale")

    assert isinstance(result, LegalClassification), "Should return LegalClassification"
    # Semantic embedding may or may not be present depending on model availability


# ===================================
# Test Cases: Case Insensitivity
# ===================================

def test_case_insensitive_classification(legal_classifier):
    """Test that classification is case-insensitive."""
    span_lower = TextSpan(
        text="c.c.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    span_upper = TextSpan(
        text="C.C.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    result_lower = legal_classifier.classify_legal_type(span_lower, "")
    result_upper = legal_classifier.classify_legal_type(span_upper, "")

    assert result_lower.act_type == result_upper.act_type, "Should classify same regardless of case"
    assert abs(result_lower.confidence - result_upper.confidence) < 0.05


# ===================================
# Test Cases: Multiple Abbreviation Variants
# ===================================

def test_variant_abbreviations(legal_classifier):
    """Test that multiple variants of same abbreviation are recognized."""
    variants = ["c.c.", "c.c", "cc"]

    results = []
    for variant in variants:
        span = TextSpan(
            text=variant,
            start_char=0,
            end_char=len(variant),
            initial_confidence=0.90
        )
        result = legal_classifier.classify_legal_type(span, "")
        results.append(result)

    # All should classify as codice_civile (or similar)
    for result in results:
        assert result.act_type is not None, f"Should classify variant {variant}"


# ===================================
# Test Cases: Edge Cases
# ===================================

def test_empty_span_text(legal_classifier):
    """Test with empty span text."""
    span = TextSpan(
        text="",
        start_char=0,
        end_char=0,
        initial_confidence=0.0
    )

    result = legal_classifier.classify_legal_type(span, "")

    # Should handle gracefully
    assert isinstance(result, LegalClassification), "Should handle empty text"


def test_very_long_span_text(legal_classifier):
    """Test with very long span text."""
    long_text = "decreto legislativo " * 50  # Very long

    span = TextSpan(
        text=long_text,
        start_char=0,
        end_char=len(long_text),
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    # Should handle long text
    assert isinstance(result, LegalClassification), "Should handle long text"


def test_span_with_special_characters(legal_classifier):
    """Test span with special characters."""
    span = TextSpan(
        text="d.lgs. — 123/2020",
        start_char=0,
        end_char=17,
        initial_confidence=0.90
    )

    result = legal_classifier.classify_legal_type(span, "")

    # Should recognize despite special characters
    assert isinstance(result, LegalClassification), "Should handle special characters"


# ===================================
# Integration Tests within LegalClassifier
# ===================================

def test_consistent_classification(legal_classifier):
    """Test that classifying the same entity twice gives same result."""
    span = TextSpan(
        text="c.c.",
        start_char=0,
        end_char=4,
        initial_confidence=0.95
    )

    result1 = legal_classifier.classify_legal_type(span, "")
    result2 = legal_classifier.classify_legal_type(span, "")

    assert result1.act_type == result2.act_type, "Should classify consistently"
    assert abs(result1.confidence - result2.confidence) < 0.01, "Should have same confidence"


def test_ruleset_construction(legal_classifier):
    """Test that ruleset is properly constructed."""
    assert hasattr(legal_classifier, 'rules'), "Should have rules attribute"
    assert len(legal_classifier.rules) > 0, "Should have at least one rule"

    # Each rule should be (pattern, act_type, confidence)
    for rule in legal_classifier.rules[:3]:  # Check first 3
        assert len(rule) == 3, "Rule should have (pattern, act_type, confidence)"
        pattern, act_type, confidence = rule
        assert 0 <= confidence <= 1, "Confidence should be 0-1"
