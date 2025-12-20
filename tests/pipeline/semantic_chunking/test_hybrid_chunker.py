"""
Tests for Hybrid Chunker
========================

Tests for the combined proposition + semantic + late chunking approach.
"""

import pytest
import json
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from merlt.pipeline.semantic_chunking.hybrid import (
    HybridChunker,
    HybridChunk,
    ChunkingStrategy,
)
from merlt.pipeline.semantic_chunking.proposition import LegalProposition
from merlt.pipeline.semantic_chunking.semantic import SemanticChunk


class TestHybridChunk:
    """Test HybridChunk dataclass."""

    def test_creation(self):
        chunk = HybridChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Il debitore deve adempiere",
            chunk_type="proposition",
            source_urn="urn:...~com1",
            confidence=0.95,
            proposition_type="regola",
            entities=["debitore"],
        )
        assert chunk.chunk_type == "proposition"
        assert chunk.confidence == 0.95
        assert "debitore" in chunk.entities

    def test_token_count_estimate(self):
        chunk = HybridChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Il debitore deve eseguire la prestazione dovuta",
            chunk_type="semantic",
            source_urn="urn:...",
        )
        # Italian factor ~1.3
        assert chunk.token_count > 0
        assert chunk.token_count > len(chunk.text.split())

    def test_to_dict(self):
        chunk = HybridChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Test",
            chunk_type="proposition",
            source_urn="urn:...",
            proposition_type="regola",
        )
        d = chunk.to_dict()
        assert d["chunk_type"] == "proposition"
        assert d["proposition_type"] == "regola"
        assert "created_at" in d

    def test_from_proposition(self):
        prop = LegalProposition(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Proposizione test",
            proposition_type="definizione",
            source_comma=1,
            source_urn="urn:...~com1",
            confidence=0.9,
            entities=["entita1"],
        )
        chunk = HybridChunk.from_proposition(prop)
        assert chunk.chunk_type == "proposition"
        assert chunk.proposition_type == "definizione"
        assert chunk.confidence == 0.9
        assert chunk.entities == ["entita1"]

    def test_from_semantic(self):
        sem = SemanticChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Chunk semantico",
            sentences=["Chunk semantico"],
            start_sentence=0,
            end_sentence=0,
            avg_similarity=0.85,
            source_urn="urn:...",
        )
        chunk = HybridChunk.from_semantic(sem)
        assert chunk.chunk_type == "semantic"
        assert chunk.confidence == 0.85
        assert chunk.metadata["sentence_count"] == 1


class TestChunkingStrategy:
    """Test ChunkingStrategy enum."""

    def test_strategies_exist(self):
        assert ChunkingStrategy.PROPOSITION_ONLY.value == "proposition_only"
        assert ChunkingStrategy.SEMANTIC_ONLY.value == "semantic_only"
        assert ChunkingStrategy.PROPOSITION_FIRST.value == "proposition_first"
        assert ChunkingStrategy.SEMANTIC_FIRST.value == "semantic_first"
        assert ChunkingStrategy.ADAPTIVE.value == "adaptive"


class TestHybridChunker:
    """Test HybridChunker class."""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.generate = AsyncMock(return_value=json.dumps([
            {"text": "Proposizione estratta", "type": "regola", "confidence": 0.9}
        ]))
        return llm

    @pytest.fixture
    def mock_embedding(self):
        embedding = MagicMock()
        embedding.embed = AsyncMock(
            side_effect=lambda x: np.random.randn(384).tolist()
        )
        embedding.embed_batch = AsyncMock(
            side_effect=lambda texts: np.random.randn(len(texts), 384).tolist()
        )
        return embedding

    @pytest.fixture
    def full_chunker(self, mock_llm, mock_embedding):
        """Chunker with both LLM and embedding."""
        return HybridChunker(
            llm_service=mock_llm,
            embedding_service=mock_embedding,
            strategy=ChunkingStrategy.ADAPTIVE,
        )

    @pytest.fixture
    def proposition_only_chunker(self, mock_llm):
        """Chunker with only LLM."""
        return HybridChunker(
            llm_service=mock_llm,
            embedding_service=None,
            strategy=ChunkingStrategy.PROPOSITION_ONLY,
        )

    @pytest.fixture
    def semantic_only_chunker(self, mock_embedding):
        """Chunker with only embedding."""
        return HybridChunker(
            llm_service=None,
            embedding_service=mock_embedding,
            strategy=ChunkingStrategy.SEMANTIC_ONLY,
        )

    def test_init_full(self, mock_llm, mock_embedding):
        chunker = HybridChunker(mock_llm, mock_embedding)
        assert chunker.proposition_chunker is not None
        assert chunker.semantic_chunker is not None

    def test_init_proposition_only(self, mock_llm):
        chunker = HybridChunker(llm_service=mock_llm)
        assert chunker.proposition_chunker is not None
        assert chunker.semantic_chunker is None

    def test_init_semantic_only(self, mock_embedding):
        chunker = HybridChunker(embedding_service=mock_embedding)
        assert chunker.proposition_chunker is None
        assert chunker.semantic_chunker is not None

    @pytest.mark.asyncio
    async def test_chunk_proposition_only(self, proposition_only_chunker):
        text = "Il debitore che non esegue la prestazione e' tenuto al risarcimento."

        chunks = await proposition_only_chunker.chunk(
            text=text,
            source_urn="urn:...~com1",
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.chunk_type == "proposition"

    @pytest.mark.asyncio
    async def test_chunk_semantic_only(self, semantic_only_chunker):
        text = "Prima frase del testo. Seconda frase del testo. Terza frase con contenuto diverso."

        chunks = await semantic_only_chunker.chunk(
            text=text,
            source_urn="urn:...",
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.chunk_type == "semantic"

    @pytest.mark.asyncio
    async def test_chunk_adaptive_short_text(self, full_chunker):
        """Short text should use propositions."""
        short_text = "Breve testo giuridico."  # < 200 chars

        # Strategy should choose proposition for short text
        strategy = full_chunker._determine_strategy(short_text)
        assert strategy == ChunkingStrategy.PROPOSITION_ONLY

    @pytest.mark.asyncio
    async def test_chunk_adaptive_long_text(self, full_chunker):
        """Long text should use semantic first."""
        long_text = "A" * 3000  # > 2000 chars

        strategy = full_chunker._determine_strategy(long_text)
        assert strategy == ChunkingStrategy.SEMANTIC_FIRST

    @pytest.mark.asyncio
    async def test_chunk_adaptive_medium_text(self, full_chunker):
        """Medium text should use proposition first."""
        medium_text = "A" * 500  # Between 200 and 2000

        strategy = full_chunker._determine_strategy(medium_text)
        assert strategy == ChunkingStrategy.PROPOSITION_FIRST

    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, full_chunker):
        chunks = await full_chunker.chunk("", source_urn="urn:...")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_article(self, full_chunker, mock_llm):
        """Test chunking full article with multiple commas."""
        mock_llm.generate.return_value = json.dumps([
            {"text": "Prop 1", "type": "regola", "confidence": 0.9}
        ])

        commas = [
            {"numero": 1, "testo": "Primo comma del testo giuridico."},
            {"numero": 2, "testo": "Secondo comma con contenuto diverso."},
        ]

        chunks = await full_chunker.chunk_article(
            commas=commas,
            article_urn="urn:...~art1453",
            article_context="Art. 1453 c.c.",
        )

        # Should have at least one chunk per comma
        assert len(chunks) >= 2

    @pytest.mark.asyncio
    async def test_fallback_when_chunker_missing(self, mock_embedding):
        """Test fallback when required chunker is missing."""
        # Request proposition-only but only have embedding
        chunker = HybridChunker(
            llm_service=None,
            embedding_service=mock_embedding,
            strategy=ChunkingStrategy.PROPOSITION_ONLY,
        )

        # Should fall back to semantic
        strategy = chunker._determine_strategy("Some text to chunk")
        assert strategy == ChunkingStrategy.SEMANTIC_ONLY


class TestHybridChunkerIntegration:
    """Integration-style tests for HybridChunker."""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.generate = AsyncMock()
        return llm

    @pytest.fixture
    def mock_embedding(self):
        embedding = MagicMock()
        embedding.embed_batch = AsyncMock(
            side_effect=lambda texts: np.random.randn(len(texts), 384).tolist()
        )
        return embedding

    @pytest.mark.asyncio
    async def test_legal_article_chunking(self, mock_llm, mock_embedding):
        """Test chunking of a realistic legal article."""
        mock_llm.generate.return_value = json.dumps([
            {
                "text": "Nei contratti con prestazioni corrispettive, la parte non inadempiente puo' chiedere l'adempimento",
                "type": "regola",
                "confidence": 0.95,
                "entities": ["contratto", "prestazioni corrispettive", "adempimento"]
            },
            {
                "text": "La parte non inadempiente puo' alternativamente chiedere la risoluzione del contratto",
                "type": "regola",
                "confidence": 0.92,
                "entities": ["risoluzione", "contratto"]
            },
            {
                "text": "Il risarcimento del danno e' sempre dovuto in caso di inadempimento",
                "type": "effetto",
                "confidence": 0.88,
                "entities": ["risarcimento", "danno", "inadempimento"]
            }
        ])

        chunker = HybridChunker(
            mock_llm,
            mock_embedding,
            strategy=ChunkingStrategy.PROPOSITION_FIRST,
        )

        text = """Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno."""

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...~art1453-com1",
            context="Art. 1453 c.c. - Risoluzione per inadempimento",
        )

        assert len(chunks) == 3
        assert all(c.chunk_type == "proposition" for c in chunks)

        # Verify entities were extracted
        all_entities = []
        for c in chunks:
            all_entities.extend(c.entities)
        assert "contratto" in all_entities
        assert "risarcimento" in all_entities
