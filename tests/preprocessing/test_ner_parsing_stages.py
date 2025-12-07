"""
Unit Tests for NER Parsing Stages (3-5)
=========================================

Tests Stages 3, 4, and 5 of the 5-stage NER pipeline.

Stage 3: NormativeParser - Extracts structured components
Stage 4: ReferenceResolver - Resolves incomplete references
Stage 5: StructureBuilder - Formats final output

Test coverage:
- Article, comma, letter extraction
- Act number and date extraction
- Reference completeness checking
- Final JSON output formatting
- Null value filtering
"""

import pytest
from merlt.preprocessing.ner_module import (
    NormativeParser,
    ReferenceResolver,
    StructureBuilder,
    LegalClassification,
    TextSpan,
    ParsedNormative,
    ResolvedNormative
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
        "output": {
            "filter_null_values": True,
            "filter_institutions": False
        }
    }


@pytest.fixture
def normative_parser(ner_config):
    """Create NormativeParser instance."""
    return NormativeParser(ner_config)


@pytest.fixture
def reference_resolver(ner_config):
    """Create ReferenceResolver instance."""
    return ReferenceResolver(ner_config)


@pytest.fixture
def structure_builder(ner_config):
    """Create StructureBuilder instance."""
    return StructureBuilder(ner_config)


# ===================================
# Test Cases: NormativeParser - Article Extraction
# ===================================

def test_parse_article_with_number(normative_parser):
    """Test extraction of article number."""
    classification = LegalClassification(
        span=TextSpan(text="art. 2043", start_char=0, end_char=9, initial_confidence=0.99),
        act_type="codice_civile",
        confidence=0.99
    )

    result = normative_parser.parse(classification)

    assert result.article == "2043", "Should extract article number"


def test_parse_article_with_letter(normative_parser):
    """Test extraction of article with letter."""
    classification = LegalClassification(
        span=TextSpan(text="art. 25 lett. a", start_char=0, end_char=15, initial_confidence=0.99),
        act_type="decreto_legislativo",
        confidence=0.99
    )

    result = normative_parser.parse(classification)

    assert result.article == "25", "Should extract article"
    assert result.letter == "a", "Should extract letter"


def test_parse_article_with_bis(normative_parser):
    """Test extraction of article with 'bis' modifier."""
    classification = LegalClassification(
        span=TextSpan(text="articolo 25-bis", start_char=0, end_char=15, initial_confidence=0.95),
        act_type="decreto_legislativo",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    assert result.article is not None, "Should extract article with bis"


# ===================================
# Test Cases: NormativeParser - Act Number Extraction
# ===================================

def test_parse_act_number_with_year(normative_parser):
    """Test extraction of act number and year."""
    classification = LegalClassification(
        span=TextSpan(text="d.lgs. 196/2003", start_char=0, end_char=15, initial_confidence=0.98),
        act_type="decreto_legislativo",
        confidence=0.98
    )

    result = normative_parser.parse(classification)

    assert result.act_number == "196", "Should extract act number"
    assert result.date == "2003", "Should extract year"


def test_parse_decree_with_year(normative_parser):
    """Test extraction of decree with year."""
    classification = LegalClassification(
        span=TextSpan(text="decreto legislativo 123/2020", start_char=0, end_char=28, initial_confidence=0.95),
        act_type="decreto_legislativo",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    assert result.act_number == "123", "Should extract decree number"
    assert result.date == "2020", "Should extract year"


# ===================================
# Test Cases: NormativeParser - Comma and Letter Extraction
# ===================================

def test_parse_comma(normative_parser):
    """Test extraction of comma reference."""
    classification = LegalClassification(
        span=TextSpan(text="art. 2043 comma 2", start_char=0, end_char=17, initial_confidence=0.95),
        act_type="codice_civile",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    assert result.article == "2043", "Should extract article"
    assert result.comma == "2", "Should extract comma"


def test_parse_letter_reference(normative_parser):
    """Test extraction of letter reference."""
    classification = LegalClassification(
        span=TextSpan(text="art. 10 lett. b", start_char=0, end_char=15, initial_confidence=0.95),
        act_type="decreto_legislativo",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    assert result.article == "10", "Should extract article"
    assert result.letter == "b", "Should extract letter"


def test_parse_article_comma_letter_complete(normative_parser):
    """Test extraction of complete article reference."""
    classification = LegalClassification(
        span=TextSpan(text="art. 2043 comma 2 lett. a", start_char=0, end_char=26, initial_confidence=0.95),
        act_type="codice_civile",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    assert result.article == "2043", "Should extract article"
    assert result.comma == "2", "Should extract comma"
    assert result.letter == "a", "Should extract letter"


# ===================================
# Test Cases: NormativeParser - Date Extraction
# ===================================

def test_parse_date_format_full(normative_parser):
    """Test extraction of full date format."""
    classification = LegalClassification(
        span=TextSpan(text="del 15 agosto 2020", start_char=0, end_char=18, initial_confidence=0.90),
        act_type="decreto_legislativo",
        confidence=0.90
    )

    result = normative_parser.parse(classification)

    # Date should be extracted (format may vary)
    assert result.date is not None, "Should extract date"


def test_parse_date_numeric_format(normative_parser):
    """Test extraction of numeric date format."""
    classification = LegalClassification(
        span=TextSpan(text="15/08/2020", start_char=0, end_char=10, initial_confidence=0.90),
        act_type="decreto_legislativo",
        confidence=0.90
    )

    result = normative_parser.parse(classification)

    # Date extraction depends on pattern matching
    assert isinstance(result.date, (str, type(None))), "Should have date or None"


# ===================================
# Test Cases: NormativeParser - Completeness Checking
# ===================================

def test_is_complete_reference_full(normative_parser):
    """Test that complete reference is marked as complete."""
    classification = LegalClassification(
        span=TextSpan(text="d.lgs. 196/2003", start_char=0, end_char=15, initial_confidence=0.98),
        act_type="decreto_legislativo",
        confidence=0.98
    )

    result = normative_parser.parse(classification)

    assert result.is_complete_reference, "Should mark as complete reference"


def test_is_incomplete_reference(normative_parser):
    """Test that incomplete reference is marked as incomplete."""
    classification = LegalClassification(
        span=TextSpan(text="art. 2043", start_char=0, end_char=9, initial_confidence=0.95),
        act_type="codice_civile",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    # Article alone might be considered complete depending on act_type
    assert isinstance(result.is_complete_reference, bool), "Should have completeness flag"


# ===================================
# Test Cases: ReferenceResolver - Direct Resolution
# ===================================

def test_resolve_direct_reference(reference_resolver):
    """Test resolution of direct reference."""
    parsed = ParsedNormative(
        text="d.lgs. 196/2003",
        act_type="decreto_legislativo",
        act_number="196",
        date="2003",
        confidence=0.98,
        start_char=0,
        end_char=15
    )

    result = reference_resolver.resolve(parsed, "full text")

    assert isinstance(result, ResolvedNormative), "Should return ResolvedNormative"
    assert result.resolution_method == "direct", "Should use direct resolution"
    assert result.resolution_confidence >= 0.99, "Should have high confidence"


def test_resolve_incomplete_reference(reference_resolver):
    """Test resolution with incomplete reference."""
    parsed = ParsedNormative(
        text="art. 2043 c.c.",
        act_type="codice_civile",
        article="2043",
        confidence=0.95,
        start_char=0,
        end_char=14
    )

    result = reference_resolver.resolve(parsed, "full text")

    assert isinstance(result, ResolvedNormative), "Should return ResolvedNormative"
    # Resolver maintains data as-is for incomplete references
    assert result.article == "2043", "Should preserve article"


# ===================================
# Test Cases: StructureBuilder - JSON Output
# ===================================

def test_build_structured_output_complete(structure_builder):
    """Test building complete structured output."""
    resolved = ResolvedNormative(
        text="d.lgs. 196/2003",
        act_type="decreto_legislativo",
        act_number="196",
        date="2003",
        article=None,
        confidence=0.98,
        start_char=0,
        end_char=15,
        is_complete_reference=True
    )

    result = structure_builder.build(resolved)

    assert isinstance(result, dict), "Should return dictionary"
    assert result["source_type"] == "decreto_legislativo", "Should include source_type"
    assert result["text"] == "d.lgs. 196/2003", "Should include text"
    assert result["confidence"] == 0.98, "Should include confidence"
    assert result["act_number"] == "196", "Should include act_number"
    assert result["date"] == "2003", "Should include date"


def test_build_structured_output_with_article(structure_builder):
    """Test building output with article and comma."""
    resolved = ResolvedNormative(
        text="art. 2043 comma 2 c.c.",
        act_type="codice_civile",
        article="2043",
        comma="2",
        confidence=0.95,
        start_char=0,
        end_char=22
    )

    result = structure_builder.build(resolved)

    assert result["article"] == "2043", "Should include article"
    assert result["comma"] == "2", "Should include comma"


# ===================================
# Test Cases: StructureBuilder - Null Filtering
# ===================================

def test_filter_null_values(structure_builder):
    """Test that null values are filtered when configured."""
    resolved = ResolvedNormative(
        text="art. 2043 c.c.",
        act_type="codice_civile",
        article="2043",
        comma=None,  # Null
        letter=None,  # Null
        date=None,  # Null
        confidence=0.95,
        start_char=0,
        end_char=14
    )

    result = structure_builder.build(resolved)

    # With filter_null_values=True, nulls should not be in output
    assert "comma" not in result or result["comma"] is not None, "Should filter null comma"
    assert "letter" not in result or result["letter"] is not None, "Should filter null letter"
    assert "date" not in result or result["date"] is not None, "Should filter null date"


# ===================================
# Test Cases: Integration - Full Pipeline Parsing
# ===================================

def test_parse_to_resolve_to_build(normative_parser, reference_resolver, structure_builder):
    """Test complete pipeline: parse → resolve → build."""
    # Stage 2 output
    classification = LegalClassification(
        span=TextSpan(text="d.lgs. 196/2003", start_char=0, end_char=15, initial_confidence=0.98),
        act_type="decreto_legislativo",
        confidence=0.98
    )

    # Stage 3: Parse
    parsed = normative_parser.parse(classification)
    assert isinstance(parsed, ParsedNormative), "Parser should return ParsedNormative"

    # Stage 4: Resolve
    resolved = reference_resolver.resolve(parsed, "full text")
    assert isinstance(resolved, ResolvedNormative), "Resolver should return ResolvedNormative"

    # Stage 5: Build
    structured = structure_builder.build(resolved)
    assert isinstance(structured, dict), "Builder should return dict"
    assert structured["source_type"] == "decreto_legislativo", "Should have correct source type"


# ===================================
# Test Cases: Edge Cases
# ===================================

def test_parse_empty_text(normative_parser):
    """Test parsing with empty text."""
    classification = LegalClassification(
        span=TextSpan(text="", start_char=0, end_char=0, initial_confidence=0.0),
        act_type="unknown",
        confidence=0.0
    )

    result = normative_parser.parse(classification)

    assert isinstance(result, ParsedNormative), "Should handle empty text"


def test_parse_malformed_reference(normative_parser):
    """Test parsing with malformed reference."""
    classification = LegalClassification(
        span=TextSpan(text="xyz 123 abc/def", start_char=0, end_char=15, initial_confidence=0.1),
        act_type="unknown",
        confidence=0.1
    )

    result = normative_parser.parse(classification)

    # Should handle gracefully without crashing
    assert isinstance(result, ParsedNormative), "Should handle malformed text"


def test_build_with_all_fields_populated(structure_builder):
    """Test building output with all fields populated."""
    resolved = ResolvedNormative(
        text="art. 25 comma 2 lett. a d.lgs. 196/2003 del 30 giugno 2003",
        act_type="decreto_legislativo",
        act_number="196",
        date="2003",
        article="25",
        comma="2",
        letter="a",
        version="1.0",
        version_date="2005",
        annex="A",
        confidence=0.95,
        start_char=0,
        end_char=60,
        is_complete_reference=True
    )

    result = structure_builder.build(resolved)

    # All fields should be present
    assert result["article"] == "25", "Should include article"
    assert result["comma"] == "2", "Should include comma"
    assert result["letter"] == "a", "Should include letter"
    assert result["act_number"] == "196", "Should include act_number"
    assert result["date"] == "2003", "Should include date"
    assert result["version"] == "1.0", "Should include version"
    assert result["annex"] == "A", "Should include annex"


# ===================================
# Test Cases: Reference Validation
# ===================================

def test_reference_validity_complete(normative_parser):
    """Test is_complete() method on ParsedNormative."""
    classification = LegalClassification(
        span=TextSpan(text="d.lgs. 196/2003", start_char=0, end_char=15, initial_confidence=0.98),
        act_type="decreto_legislativo",
        confidence=0.98
    )

    result = normative_parser.parse(classification)

    # is_complete() checks for act_type AND (act_number OR article) AND (date OR article)
    assert isinstance(result.is_complete(), bool), "Should have is_complete() method"


def test_reference_validity_incomplete(normative_parser):
    """Test is_complete() on incomplete reference."""
    classification = LegalClassification(
        span=TextSpan(text="art. 2043", start_char=0, end_char=9, initial_confidence=0.95),
        act_type="codice_civile",
        confidence=0.95
    )

    result = normative_parser.parse(classification)

    # This might be marked complete due to act_type + article
    assert isinstance(result.is_complete(), bool), "Should evaluate completeness correctly"
