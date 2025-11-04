"""
Integration Tests for Complete NER Pipeline
=============================================

Tests the complete 5-stage NER pipeline end-to-end with alignment
to MERL-T query-understanding.md specifications.

Verifies:
1. Full pipeline execution (Stage 1-5)
2. Norm reference extraction (decreto, legge, codice, etc.)
3. Proper output formatting for orchestration layer
4. Alignment with query-understanding.md entity types
5. Real-world legal text scenarios

Reference: docs/02-methodology/query-understanding.md
"""

import pytest
import asyncio
from backend.preprocessing.ner_module import (
    LegalSourceExtractionPipeline,
    EntityDetector,
    LegalClassifier,
    NormativeParser,
    ReferenceResolver,
    StructureBuilder
)
from backend.preprocessing.label_mapping import get_label_manager

import logging

log = logging.getLogger(__name__)


# ===================================
# Fixtures
# ===================================

@pytest.fixture
def ner_config():
    """Complete NER configuration for integration testing."""
    return {
        "models": {
            "entity_detector": {
                "primary": "DeepMount00/Italian_NER_XXL_v2",
                "fallback": "Babelscape/wikineural-multilingual-ner",
                "max_length": 256
            },
            "legal_classifier": {
                "primary": "dlicari/distil-ita-legal-bert",
                "embedding_max_length": 256
            }
        },
        "normattiva_mapping": {
            "codice_civile": ["c.c.", "c.c", "cc", "codice civile"],
            "codice_penale": ["c.p.", "c.p", "cp", "codice penale"],
            "decreto_legislativo": ["d.lgs.", "d.lgs", "dlgs"],
            "decreto_presidente_repubblica": ["d.p.r.", "d.p.r", "dpr"],
            "legge": ["l.", "l", "legge"],
            "costituzione": ["cost.", "cost", "costituzione"],
            "direttiva_ue": ["direttiva ue", "dir. ue"],
            "regolamento_ue": ["regolamento ue", "reg. ue"],
        },
        "parsing_patterns": {
            "article": r"(?:art\.?|articolo)\s+(\d+[a-z]*)",
            "comma": r"(?:comma|co\.?)\s+(\d+)",
            "letter": r"(?:lett\.?|lettera)\s+([a-z])",
            "act_number": r"(\d+)\s*(?:/|del)\s*(\d{4})",
            "date_patterns": {
                "primary": r"del\s+(\d{1,2})\s+([a-z]+)\s+(\d{4})",
                "secondary": r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
                "tertiary": r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"
            },
            "eu_directive": r"direttiva\s+(?:\(ue\))?\s+(\d{4})/(\d+)"
        },
        "context": {
            "left_window": 150,
            "right_window": 150,
            "context_window": 75,
            "extended_context": 120,
            "immediate_context": 50
        },
        "output": {
            "filter_null_values": True,
            "filter_institutions": False
        }
    }


@pytest.fixture
def pipeline(ner_config):
    """Create NER pipeline for testing."""
    try:
        return LegalSourceExtractionPipeline(config=ner_config)
    except Exception as e:
        pytest.skip(f"Could not initialize pipeline: {e}")


# ===================================
# Test Cases: Real-World Legal Texts
# ===================================

@pytest.mark.asyncio
async def test_pipeline_codice_civile_example(pipeline):
    """Test extraction from Codice Civile example."""
    text = "Secondo l'articolo 2043 del codice civile, chiunque cagiona ad altri un danno ingiusto è tenuto al risarcimento."

    results = await pipeline.extract_legal_sources(text)

    assert len(results) > 0, "Should extract at least one entity"

    # Check for codice civile reference
    found_cc = any("codice civile" in r.get("text", "").lower() or "2043" in r.get("article", "") for r in results)
    assert found_cc, "Should find codice civile reference"


@pytest.mark.asyncio
async def test_pipeline_decreto_legislativo_example(pipeline):
    """Test extraction from Decreto Legislativo reference."""
    text = "Il d.lgs. 196/2003 sulla privacy disciplina il trattamento dei dati personali."

    results = await pipeline.extract_legal_sources(text)

    assert len(results) > 0, "Should extract decree reference"

    found_decree = any("196" in r.get("act_number", "") and "2003" in r.get("date", "") for r in results)
    assert found_decree, "Should extract act number and date"


@pytest.mark.asyncio
async def test_pipeline_article_with_comma(pipeline):
    """Test extraction with article and comma reference."""
    text = "L'articolo 1414 comma 2 c.c. riguarda l'annullabilità dei contratti."

    results = await pipeline.extract_legal_sources(text)

    assert len(results) > 0, "Should extract reference"

    # Check for structured components
    found_structured = any(
        r.get("article") == "1414" and r.get("comma") == "2"
        for r in results
    )
    assert found_structured, "Should extract article and comma"


@pytest.mark.asyncio
async def test_pipeline_multiple_entities_in_text(pipeline):
    """Test extraction of multiple entities from single text."""
    text = (
        "Nel contratto, così come disciplinato dall'articolo 1321 c.c., "
        "si applicano le norme del d.lgs. 33/2013 sulla trasparenza amministrativa. "
        "Si veda inoltre l'articolo 10 della costituzione."
    )

    results = await pipeline.extract_legal_sources(text)

    assert len(results) >= 3, "Should extract at least 3 different references"

    # Verify variety of references
    codes_found = [r.get("act_type", "") for r in results]
    assert "codice_civile" in codes_found, "Should find codice civile"
    assert "decreto_legislativo" in codes_found, "Should find decreto legislativo"


@pytest.mark.asyncio
async def test_pipeline_eu_normative_reference(pipeline):
    """Test extraction of EU directive/regulation references."""
    text = "La direttiva ue 2020/123 stabilisce le linee guida sulla sicurezza dei dati."

    results = await pipeline.extract_legal_sources(text)

    assert len(results) > 0, "Should extract EU directive"

    found_eu = any("direttiva" in r.get("act_type", "").lower() for r in results)
    assert found_eu, "Should recognize EU directive"


# ===================================
# Test Cases: Output Format Validation
# ===================================

@pytest.mark.asyncio
async def test_pipeline_output_schema_validation(pipeline):
    """Verify output matches expected JSON schema."""
    text = "art. 2043 c.c."

    results = await pipeline.extract_legal_sources(text)

    assert isinstance(results, list), "Should return list of results"

    for result in results:
        assert isinstance(result, dict), "Each result should be dict"

        # Check required fields
        required_fields = ["text", "confidence", "act_type", "source_type"]
        for field in required_fields:
            assert field in result, f"Result should have {field}"

        # Validate field types
        assert isinstance(result["text"], str), "text should be string"
        assert isinstance(result["confidence"], (int, float)), "confidence should be numeric"
        assert 0 <= result["confidence"] <= 1, "confidence should be 0-1"


@pytest.mark.asyncio
async def test_pipeline_position_accuracy(pipeline):
    """Verify that character positions are accurate."""
    text = "Secondo l'art. 2043 c.c., tutto è disciplinato."

    results = await pipeline.extract_legal_sources(text)

    for result in results:
        # Verify position coordinates are in the text
        if "start_char" in result and "end_char" in result:
            start = result["start_char"]
            end = result["end_char"]

            assert 0 <= start < len(text), "start_char should be valid"
            assert 0 < end <= len(text), "end_char should be valid"
            assert start < end, "start should be before end"

            # Reconstruct text from positions
            reconstructed = text[start:end].strip()
            assert len(reconstructed) > 0, "Position should extract non-empty text"


# ===================================
# Test Cases: Confidence & Review Flags
# ===================================

@pytest.mark.asyncio
async def test_pipeline_confidence_scoring_consistency(pipeline):
    """Test that confidence scores are consistent."""
    text = "c.c. è il codice civile"

    results = await pipeline.extract_legal_sources(text)

    # c.c. abbreviation should have high confidence
    cc_results = [r for r in results if "c.c" in r.get("text", "").lower()]

    if cc_results:
        confidences = [r["confidence"] for r in cc_results]
        avg_confidence = sum(confidences) / len(confidences)

        assert avg_confidence > 0.7, "Abbreviation should have high confidence"


@pytest.mark.asyncio
async def test_pipeline_handles_ambiguous_references(pipeline):
    """Test handling of ambiguous or unclear references."""
    text = "art. x y z something unclear"

    results = await pipeline.extract_legal_sources(text)

    # Should either return empty or low-confidence results
    if results:
        for result in results:
            # Ambiguous references should have lower confidence
            if "unclear" in text:
                assert result["confidence"] < 0.9, "Ambiguous should have lower confidence"


# ===================================
# Test Cases: Stage-by-Stage Validation
# ===================================

def test_entity_detector_stage_output(ner_config):
    """Verify EntityDetector stage produces correct output."""
    try:
        detector = EntityDetector(ner_config)
    except:
        pytest.skip("EntityDetector not available")

    text = "art. 2043 c.c."
    candidates = detector.detect_candidates(text)

    assert isinstance(candidates, list), "Should return list of candidates"

    for candidate in candidates:
        assert hasattr(candidate, 'text'), "Candidate should have text"
        assert hasattr(candidate, 'start_char'), "Candidate should have start_char"
        assert hasattr(candidate, 'end_char'), "Candidate should have end_char"
        assert hasattr(candidate, 'initial_confidence'), "Candidate should have confidence"


def test_legal_classifier_stage_output(ner_config):
    """Verify LegalClassifier stage produces correct output."""
    try:
        from backend.preprocessing.ner_module import TextSpan, LegalClassifier
        classifier = LegalClassifier(ner_config)
    except:
        pytest.skip("LegalClassifier not available")

    span = TextSpan(text="c.c.", start_char=0, end_char=4, initial_confidence=0.95)
    result = classifier.classify_legal_type(span, "")

    assert hasattr(result, 'act_type'), "Should have act_type"
    assert hasattr(result, 'confidence'), "Should have confidence"
    assert result.act_type is not None, "act_type should not be None"


# ===================================
# Test Cases: Query Understanding Alignment
# ===================================

@pytest.mark.asyncio
async def test_alignment_with_query_understanding_norm_extraction(pipeline):
    """
    Verify NER aligns with query-understanding.md Stage 2.

    From query-understanding.md:
    - LEGAL_OBJECT: "contratto", "testamento", "sentenza"
    - PERSON: "minorenne", "sedicenne", "maggiorenne"
    - ACTION: "firma_contratto"

    This test focuses on NORM REFERENCES which our NER extracts.
    """
    text = "È valido un contratto firmato da un minorenne di 16 anni secondo il c.c.?"

    results = await pipeline.extract_legal_sources(text)

    # Our NER should extract the norm reference (c.c.)
    assert len(results) > 0, "Should extract norm references"

    found_cc = any("c.c" in r.get("text", "").lower() for r in results)
    assert found_cc, "Should extract Codice Civile reference for query-understanding context"


@pytest.mark.asyncio
async def test_output_compatible_with_query_understanding_schema(pipeline):
    """
    Verify output can be integrated into query-understanding structured query object.

    From query-understanding.md output schema:
    {
      "entities": {
        "norm_references": [{"law_name": "codice civile", "code": "cc"}],
        ...
      }
    }
    """
    text = "Secondo il d.lgs. 196/2003 sulla privacy..."

    results = await pipeline.extract_legal_sources(text)

    # Each result should be convertible to norm_reference format
    norm_references = []
    for result in results:
        norm_ref = {
            "law_name": result.get("act_type"),
            "code": result.get("text"),
            "confidence": result.get("confidence"),
            "article": result.get("article"),
            "act_number": result.get("act_number"),
            "date": result.get("date")
        }
        norm_references.append(norm_ref)

    assert len(norm_references) > 0, "Should produce norm references for query understanding"


# ===================================
# Test Cases: Edge Cases & Robustness
# ===================================

@pytest.mark.asyncio
async def test_pipeline_handles_empty_text(pipeline):
    """Test pipeline with empty input."""
    results = await pipeline.extract_legal_sources("")

    assert isinstance(results, list), "Should handle empty text gracefully"
    assert len(results) == 0, "Should return empty list for empty text"


@pytest.mark.asyncio
async def test_pipeline_handles_very_long_text(pipeline):
    """Test pipeline with very long document."""
    # Create text longer than model max_length
    base_text = "art. 2043 c.c. "
    text = base_text * 500  # ~7000 characters

    results = await pipeline.extract_legal_sources(text)

    assert isinstance(results, list), "Should handle long text"
    # Should extract multiple instances
    assert len(results) > 0, "Should find repeated patterns in long text"


@pytest.mark.asyncio
async def test_pipeline_handles_special_characters(pipeline):
    """Test with special characters and formatting."""
    text = "Art. 2043 c.c. — secondo il quale — ogni danno deve essere risarcito (art. 25, comma 2)."

    results = await pipeline.extract_legal_sources(text)

    assert isinstance(results, list), "Should handle special characters"
    # Should extract despite special characters
    assert len(results) > 0, "Should extract references with special characters"


# ===================================
# Test Cases: Performance & Consistency
# ===================================

@pytest.mark.asyncio
async def test_pipeline_consistency_on_repeated_input(pipeline):
    """Test that extracting same text twice gives same results."""
    text = "art. 2043 c.c."

    results1 = await pipeline.extract_legal_sources(text)
    results2 = await pipeline.extract_legal_sources(text)

    assert len(results1) == len(results2), "Should extract same number of entities"

    if results1:
        texts1 = [r["text"] for r in results1]
        texts2 = [r["text"] for r in results2]
        assert texts1 == texts2, "Should extract same text consistently"


@pytest.mark.asyncio
async def test_pipeline_execution_completes(pipeline):
    """Test that pipeline execution completes without errors."""
    test_cases = [
        "art. 2043 c.c.",
        "d.lgs. 196/2003",
        "legge 123 del 2020",
        "direttiva ue 2020/123",
        "È valido il contratto secondo il c.c.?",
        "art. 25 comma 2 lett. a d.lgs. 123/2020"
    ]

    for text in test_cases:
        try:
            results = await pipeline.extract_legal_sources(text)
            assert isinstance(results, list), f"Should return list for: {text}"
        except Exception as e:
            pytest.fail(f"Pipeline failed on '{text}': {str(e)}")


# ===================================
# Async Test Helpers
# ===================================

@pytest.fixture
def event_loop():
    """Provide event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
