"""
Tests for Proposition Chunker
=============================

Tests for LLM-based proposition extraction from legal texts.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from merlt.pipeline.semantic_chunking.proposition import (
    PropositionChunker,
    LegalProposition,
    PROPOSITION_EXTRACTION_PROMPT,
)


class TestLegalProposition:
    """Test LegalProposition dataclass."""

    def test_creation(self):
        prop = LegalProposition(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Il debitore deve eseguire la prestazione",
            proposition_type="regola",
            source_comma=1,
            source_urn="urn:...~art1218-com1",
            confidence=0.95,
            entities=["debitore", "prestazione"],
        )
        assert prop.text == "Il debitore deve eseguire la prestazione"
        assert prop.proposition_type == "regola"
        assert prop.confidence == 0.95
        assert "debitore" in prop.entities

    def test_to_dict(self):
        prop = LegalProposition(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Test proposizione",
            proposition_type="definizione",
            source_comma=2,
            source_urn="urn:...~art1453-com2",
        )
        d = prop.to_dict()
        assert d["id"] == "12345678-1234-1234-1234-123456789abc"
        assert d["proposition_type"] == "definizione"
        assert d["source_comma"] == 2
        assert "created_at" in d


class TestPropositionChunker:
    """Test PropositionChunker class."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM service."""
        llm = MagicMock()
        llm.generate = AsyncMock()
        return llm

    @pytest.fixture
    def chunker(self, mock_llm):
        """Create chunker with mock LLM."""
        return PropositionChunker(
            llm_service=mock_llm,
            max_propositions_per_comma=5,
            min_confidence=0.7,
        )

    def test_init(self, mock_llm):
        chunker = PropositionChunker(mock_llm)
        assert chunker.llm == mock_llm
        assert chunker.max_propositions == 10  # default
        assert chunker.min_confidence == 0.7  # default

    def test_init_custom_config(self, mock_llm):
        chunker = PropositionChunker(
            mock_llm,
            max_propositions_per_comma=3,
            min_confidence=0.5,
        )
        assert chunker.max_propositions == 3
        assert chunker.min_confidence == 0.5

    @pytest.mark.asyncio
    async def test_extract_single_proposition(self, chunker, mock_llm):
        """Test extraction of a single proposition."""
        mock_llm.generate.return_value = json.dumps([
            {
                "text": "Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento del danno",
                "type": "regola",
                "entities": ["debitore", "prestazione", "risarcimento"],
                "confidence": 0.95
            }
        ])

        text = "Il debitore che non esegue esattamente la prestazione dovuta è tenuto al risarcimento del danno."

        props = await chunker.extract(
            text=text,
            comma_number=1,
            source_urn="urn:...~art1218-com1",
            article_context="Art. 1218 - Responsabilita' del debitore"
        )

        assert len(props) == 1
        assert props[0].proposition_type == "regola"
        assert props[0].confidence == 0.95
        assert "debitore" in props[0].entities

    @pytest.mark.asyncio
    async def test_extract_multiple_propositions(self, chunker, mock_llm):
        """Test extraction of multiple propositions."""
        mock_llm.generate.return_value = json.dumps([
            {
                "text": "Il contratto puo' essere risolto per inadempimento",
                "type": "regola",
                "confidence": 0.9
            },
            {
                "text": "Il risarcimento del danno e' sempre dovuto",
                "type": "effetto",
                "confidence": 0.85
            }
        ])

        text = "Nei contratti, quando uno dei contraenti non adempie, l'altro può chiedere la risoluzione, salvo il risarcimento del danno."

        props = await chunker.extract(
            text=text,
            comma_number=1,
            source_urn="urn:...~art1453-com1",
        )

        assert len(props) == 2
        assert props[0].proposition_type == "regola"
        assert props[1].proposition_type == "effetto"

    @pytest.mark.asyncio
    async def test_extract_filters_low_confidence(self, chunker, mock_llm):
        """Test that low confidence propositions are filtered."""
        mock_llm.generate.return_value = json.dumps([
            {"text": "Prop alta conf", "type": "regola", "confidence": 0.9},
            {"text": "Prop bassa conf", "type": "regola", "confidence": 0.5},  # Below threshold
            {"text": "Prop media conf", "type": "regola", "confidence": 0.75},
        ])

        props = await chunker.extract(
            text="Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento.",
            comma_number=1,
            source_urn="urn:...~com1",
        )

        assert len(props) == 2  # Only 2 above 0.7 threshold

    @pytest.mark.asyncio
    async def test_extract_respects_max_propositions(self, chunker, mock_llm):
        """Test max propositions limit."""
        mock_llm.generate.return_value = json.dumps([
            {"text": f"Proposizione {i}", "type": "regola", "confidence": 0.9}
            for i in range(10)  # 10 propositions
        ])

        props = await chunker.extract(
            text="Long text with many propositions",
            comma_number=1,
            source_urn="urn:...",
        )

        assert len(props) <= 5  # max_propositions_per_comma = 5

    @pytest.mark.asyncio
    async def test_extract_empty_text(self, chunker, mock_llm):
        """Test with empty or very short text."""
        props = await chunker.extract(
            text="",
            comma_number=1,
            source_urn="urn:...",
        )
        assert props == []

        props = await chunker.extract(
            text="Breve",  # Too short
            comma_number=1,
            source_urn="urn:...",
        )
        assert props == []

    @pytest.mark.asyncio
    async def test_extract_llm_error_fallback(self, chunker, mock_llm):
        """Test fallback when LLM fails."""
        mock_llm.generate.side_effect = Exception("LLM API error")

        text = "Il debitore deve eseguire la prestazione dovuta."

        props = await chunker.extract(
            text=text,
            comma_number=1,
            source_urn="urn:...~com1",
        )

        # Should return fallback proposition
        assert len(props) == 1
        assert props[0].text == text.strip()
        assert props[0].confidence == 0.5  # Low confidence for fallback

    @pytest.mark.asyncio
    async def test_extract_invalid_json_response(self, chunker, mock_llm):
        """Test handling of invalid JSON from LLM."""
        mock_llm.generate.return_value = "This is not valid JSON"

        props = await chunker.extract(
            text="Valid input text for testing",
            comma_number=1,
            source_urn="urn:...",
        )

        # Should return empty list (no valid propositions)
        assert props == []

    @pytest.mark.asyncio
    async def test_extract_json_with_extra_text(self, chunker, mock_llm):
        """Test extraction when LLM adds extra text around JSON."""
        mock_llm.generate.return_value = """
        Ecco le proposizioni estratte:
        [
            {"text": "Il debitore deve adempiere", "type": "regola", "confidence": 0.9}
        ]
        Queste sono le proposizioni principali.
        """

        props = await chunker.extract(
            text="Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento del danno.",
            comma_number=1,
            source_urn="urn:...",
        )

        assert len(props) == 1
        assert props[0].text == "Il debitore deve adempiere"


class TestPropositionExtractionPrompt:
    """Test the extraction prompt template."""

    def test_prompt_has_placeholders(self):
        assert "{article_context}" in PROPOSITION_EXTRACTION_PROMPT
        assert "{comma_number}" in PROPOSITION_EXTRACTION_PROMPT
        assert "{text}" in PROPOSITION_EXTRACTION_PROMPT

    def test_prompt_formatting(self):
        formatted = PROPOSITION_EXTRACTION_PROMPT.format(
            article_context="Art. 1218 c.c.",
            comma_number=1,
            text="Il debitore che non esegue..."
        )
        assert "Art. 1218 c.c." in formatted
        assert "Comma 1" in formatted
        assert "Il debitore che non esegue..." in formatted

    def test_prompt_contains_types(self):
        """Verify all proposition types are documented."""
        required_types = ["regola", "definizione", "condizione", "effetto", "eccezione", "procedura"]
        for type_name in required_types:
            assert type_name in PROPOSITION_EXTRACTION_PROMPT
