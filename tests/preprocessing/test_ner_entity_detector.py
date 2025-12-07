"""
Unit Tests for NER EntityDetector Stage
========================================

Tests the Stage 1 of the 5-stage NER pipeline.
Covers BERT-based entity detection and regex fallback.

Test coverage:
- BERT entity detection with offset mapping
- Regex-based fallback detection
- Boundary expansion for complete references
- Spurious entity filtering
- Confidence scoring
"""

import pytest
import logging
from merlt.preprocessing.ner_module import (
    EntityDetector,
    TextSpan
)

log = logging.getLogger(__name__)


# ===================================
# Fixtures
# ===================================

@pytest.fixture
def ner_config():
    """Minimal NER configuration for testing."""
    return {
        "models": {
            "entity_detector": {
                "primary": "DeepMount00/Italian_NER_XXL_v2",
                "fallback": "Babelscape/wikineural-multilingual-ner",
                "max_length": 256
            }
        },
        "normattiva_mapping": {
            "codice_civile": ["c.c.", "c.c", "cc", "codice civile"],
            "decreto_legislativo": ["d.lgs.", "d.lgs", "dlgs"],
            "legge": ["l.", "l", "legge"],
            "costituzione": ["cost.", "cost", "costituzione"],
        },
        "regex_patterns": {
            "articles": [r'\bart\.?\s*\d+[a-z]*(?:-[a-z]+)?\b'],
            "codes": [r'\bc\.\s*c\.\b', r'\bc\.\s*p\.\b'],
            "decrees": [r'\bd\.\s*l\.\b', r'\bd\.\s*p\.\s*r\.\b'],
            "laws": [r'\blegge\s+\d+\b'],
        },
        "context": {
            "left_window": 150,
            "right_window": 150,
            "context_window": 75,
            "extended_context": 120,
            "immediate_context": 50
        },
        "legal_context_words": ["norma", "normativa", "articolo", "legge", "decreto"]
    }


@pytest.fixture
def entity_detector(ner_config):
    """Create EntityDetector instance."""
    try:
        detector = EntityDetector(ner_config)
        return detector
    except Exception as e:
        pytest.skip(f"Could not load EntityDetector models: {e}")


# ===================================
# Test Cases: Regex-Based Detection
# ===================================

def test_detect_article_reference(entity_detector):
    """Test detection of article references."""
    text = "Secondo l'art. 2043 c.c., chiunque cagiona danno è tenuto al risarcimento."

    candidates = entity_detector.detect_candidates(text)

    assert len(candidates) > 0, "Should detect at least one entity"

    # Check for article pattern
    found_article = any("2043" in c.text for c in candidates)
    assert found_article, "Should detect article number"


def test_detect_code_abbreviations(entity_detector):
    """Test detection of code abbreviations."""
    text = "Le disposizioni del c.c. e del c.p. si applicano a tutti."

    candidates = entity_detector.detect_candidates(text)

    # Should detect c.c. and c.p.
    assert len(candidates) >= 2, "Should detect at least 2 code abbreviations"

    detected_texts = [c.text for c in candidates]
    assert any("c.c" in t for t in detected_texts), "Should detect codice civile"
    assert any("c.p" in t for t in detected_texts), "Should detect codice penale"


def test_detect_decree_reference(entity_detector):
    """Test detection of decree references."""
    text = "Si veda il d.lgs. 196/2003 sulla privacy."

    candidates = entity_detector.detect_candidates(text)

    assert len(candidates) > 0, "Should detect decree"

    found_decree = any("d.lgs" in c.text.lower() for c in candidates)
    assert found_decree, "Should detect d.lgs."


def test_detect_law_reference(entity_detector):
    """Test detection of law references."""
    text = "La legge 123 del 2020 disciplina la materia."

    candidates = entity_detector.detect_candidates(text)

    assert len(candidates) > 0, "Should detect law reference"

    found_law = any("legge" in c.text.lower() for c in candidates)
    assert found_law, "Should detect legge reference"


def test_detect_constitution_reference(entity_detector):
    """Test detection of constitution references."""
    text = "L'articolo 3 della Costituzione sancisce l'uguaglianza."

    candidates = entity_detector.detect_candidates(text)

    assert len(candidates) > 0, "Should detect constitution reference"


# ===================================
# Test Cases: Offset Mapping & Positions
# ===================================

def test_entity_positions_accuracy(entity_detector):
    """Test that extracted positions are accurate."""
    text = "Secondo l'art. 2043 c.c., chiunque cagiona danno."

    candidates = entity_detector.detect_candidates(text)

    for candidate in candidates:
        # Verify that the span is correct
        extracted_text = text[candidate.start_char:candidate.end_char]

        # Allow for some fuzzy matching (stripped text)
        assert extracted_text.strip() != "", "Extracted span should not be empty"
        assert candidate.start_char >= 0, "Start position should be non-negative"
        assert candidate.end_char <= len(text), "End position should not exceed text length"
        assert candidate.start_char < candidate.end_char, "Start should be before end"


# ===================================
# Test Cases: Boundary Expansion
# ===================================

def test_boundary_expansion_left(entity_detector):
    """Test left boundary expansion for complete references."""
    text = "decreto legislativo 123/2020"

    candidates = entity_detector.detect_candidates(text)

    # Should capture full reference with decree type
    if candidates:
        candidate = candidates[0]
        assert "decreto" in candidate.text.lower() or "d.l" in candidate.text.lower()


def test_boundary_expansion_right(entity_detector):
    """Test right boundary expansion for dates."""
    text = "art. 25 del 2020 come modificato da legge 2021"

    candidates = entity_detector.detect_candidates(text)

    # Should expand to capture year/date
    if candidates:
        candidate = candidates[0]
        assert "25" in candidate.text or "2020" in candidate.text


# ===================================
# Test Cases: Confidence Scoring
# ===================================

def test_confidence_scoring(entity_detector):
    """Test that confidence scores are assigned."""
    text = "L'art. 2043 c.c. prevede la responsabilità civile."

    candidates = entity_detector.detect_candidates(text)

    assert len(candidates) > 0, "Should detect entities"

    for candidate in candidates:
        assert hasattr(candidate, 'initial_confidence'), "Should have confidence score"
        assert 0 <= candidate.initial_confidence <= 1, "Confidence should be between 0 and 1"


def test_rule_based_fallback_confidence(entity_detector):
    """Test confidence scores from rule-based fallback."""
    text = "art. 10 del codice civile"

    candidates = entity_detector.detect_candidates(text)

    # Rule-based fallback assigns 0.7 confidence
    for candidate in candidates:
        if candidate.initial_confidence < 0.8:
            log.info(f"Rule-based detection with confidence {candidate.initial_confidence}")
            assert candidate.initial_confidence >= 0.5, "Should have reasonable confidence"


# ===================================
# Test Cases: Duplicate & Overlap Removal
# ===================================

def test_remove_overlapping_candidates(entity_detector):
    """Test that overlapping candidates are merged properly."""
    text = "art. 25 comma 1 lettera a"

    candidates = entity_detector.detect_candidates(text)

    # Should not have overlapping candidates
    for i, c1 in enumerate(candidates):
        for j, c2 in enumerate(candidates):
            if i != j:
                # Check no overlap
                if not (c1.end_char <= c2.start_char or c2.end_char <= c1.start_char):
                    pytest.fail(f"Overlapping candidates found: {c1.text} and {c2.text}")


# ===================================
# Test Cases: Edge Cases
# ===================================

def test_empty_text(entity_detector):
    """Test with empty text."""
    text = ""
    candidates = entity_detector.detect_candidates(text)
    assert len(candidates) == 0, "Should handle empty text gracefully"


def test_text_without_entities(entity_detector):
    """Test with text containing no legal references."""
    text = "Questo è un testo ordinario senza riferimenti normativi."
    candidates = entity_detector.detect_candidates(text)
    # May or may not find entities depending on model
    assert isinstance(candidates, list), "Should return a list"


def test_very_long_text(entity_detector):
    """Test with text longer than model max_length."""
    text = "art. 2043 c.c. " * 100  # 1400+ characters

    candidates = entity_detector.detect_candidates(text)

    # Should handle truncation gracefully
    assert isinstance(candidates, list), "Should handle long text"
    assert len(candidates) > 0, "Should detect entities in long text"


def test_text_with_special_characters(entity_detector):
    """Test with special characters and formatting."""
    text = "Art. 2043 c.c. — secondo il quale — chiunque cagiona danno."

    candidates = entity_detector.detect_candidates(text)

    # Should handle special characters
    assert isinstance(candidates, list), "Should handle special characters"


def test_multiple_entities_in_sequence(entity_detector):
    """Test detection of multiple entities in sequence."""
    text = "Il c.c., il c.p., il c.p.c. e il c.p.p. disciplinano la materia."

    candidates = entity_detector.detect_candidates(text)

    # Should detect multiple codes
    assert len(candidates) >= 2, "Should detect multiple entities"


# ===================================
# Test Cases: Text Span Attributes
# ===================================

def test_text_span_attributes(entity_detector):
    """Test that TextSpan objects have all required attributes."""
    text = "art. 2043 c.c."

    candidates = entity_detector.detect_candidates(text)

    for candidate in candidates:
        assert hasattr(candidate, 'text'), "Should have text attribute"
        assert hasattr(candidate, 'start_char'), "Should have start_char attribute"
        assert hasattr(candidate, 'end_char'), "Should have end_char attribute"
        assert hasattr(candidate, 'initial_confidence'), "Should have initial_confidence"
        assert hasattr(candidate, 'context_window'), "Should have context_window"


def test_context_window_extraction(entity_detector):
    """Test that context window is properly extracted."""
    text = "Secondo l'art. 2043 c.c., chiunque cagiona danno è tenuto al risarcimento."

    candidates = entity_detector.detect_candidates(text)

    for candidate in candidates:
        if candidate.context_window:
            # Context window should be larger than the entity itself
            assert len(candidate.context_window) > len(candidate.text)
            # Context window should contain the entity
            assert candidate.text.lower() in candidate.context_window.lower()


# ===================================
# Integration Tests within EntityDetector
# ===================================

def test_detection_consistency(entity_detector):
    """Test that detecting the same text twice gives consistent results."""
    text = "art. 2043 c.c. e art. 25 d.lgs. 196/2003"

    candidates1 = entity_detector.detect_candidates(text)
    candidates2 = entity_detector.detect_candidates(text)

    assert len(candidates1) == len(candidates2), "Should detect same number of entities consistently"

    for c1, c2 in zip(candidates1, candidates2):
        assert c1.text == c2.text, "Should detect same text"
        assert c1.start_char == c2.start_char, "Should have same positions"


def test_normattiva_mapping_usage(entity_detector):
    """Test that NORMATTIVA mapping is used for entity validation."""
    # Test with abbreviations in the mapping
    text = "Secondo il c.c. (codice civile)"

    candidates = entity_detector.detect_candidates(text)

    # Should recognize c.c. as a valid legal reference
    detected_texts = [c.text.lower() for c in candidates]
    assert any("c.c" in t for t in detected_texts), "Should recognize c.c. from NORMATTIVA mapping"
