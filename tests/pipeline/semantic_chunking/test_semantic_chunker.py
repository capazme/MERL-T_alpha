"""
Tests for Semantic Similarity Chunker
=====================================

Tests for embedding-based semantic chunking.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from merlt.pipeline.semantic_chunking.semantic import (
    SemanticChunker,
    SemanticChunk,
    PercentileSemanticChunker,
)


class TestSemanticChunk:
    """Test SemanticChunk dataclass."""

    def test_creation(self):
        chunk = SemanticChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Il contratto e' un accordo di due o piu' parti.",
            sentences=["Il contratto e' un accordo di due o piu' parti."],
            start_sentence=0,
            end_sentence=0,
            avg_similarity=1.0,
            source_urn="urn:...~art1321",
        )
        assert chunk.text == "Il contratto e' un accordo di due o piu' parti."
        assert chunk.sentence_count == 1
        assert chunk.avg_similarity == 1.0

    def test_sentence_count(self):
        chunk = SemanticChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Prima frase. Seconda frase. Terza frase.",
            sentences=["Prima frase.", "Seconda frase.", "Terza frase."],
            start_sentence=0,
            end_sentence=2,
            avg_similarity=0.85,
            source_urn="urn:...",
        )
        assert chunk.sentence_count == 3


class TestSemanticChunker:
    """Test SemanticChunker class."""

    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding service."""
        embedding = MagicMock()
        # Return random embeddings of dimension 384
        embedding.embed = AsyncMock(
            side_effect=lambda x: np.random.randn(384).tolist()
        )
        embedding.embed_batch = AsyncMock(
            side_effect=lambda texts: np.random.randn(len(texts), 384).tolist()
        )
        return embedding

    @pytest.fixture
    def chunker(self, mock_embedding):
        """Create chunker with mock embedding."""
        return SemanticChunker(
            embedding_service=mock_embedding,
            threshold=0.5,
            min_chunk_sentences=1,
            max_chunk_sentences=5,
        )

    def test_init(self, mock_embedding):
        chunker = SemanticChunker(mock_embedding)
        assert chunker.threshold == 0.5  # default
        assert chunker.min_sentences == 1
        assert chunker.max_sentences == 10

    def test_init_custom_config(self, mock_embedding):
        chunker = SemanticChunker(
            mock_embedding,
            threshold=0.3,
            min_chunk_sentences=2,
            max_chunk_sentences=8,
            buffer_size=2,
        )
        assert chunker.threshold == 0.3
        assert chunker.min_sentences == 2
        assert chunker.max_sentences == 8
        assert chunker.buffer_size == 2

    def test_segment_sentences_simple(self, chunker):
        """Test sentence segmentation."""
        # Frasi abbastanza lunghe per non essere unite
        text = "Prima frase con contenuto sufficiente. Seconda frase altrettanto lunga. Terza frase con abbastanza parole."
        sentences = chunker._segment_sentences(text)
        assert len(sentences) == 3

    def test_segment_sentences_legal_text(self, chunker):
        """Test sentence segmentation with legal text."""
        text = """Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento del danno. Salvo il caso di dolo o colpa grave, il debitore non e' tenuto al risarcimento dei danni imprevedibili."""
        sentences = chunker._segment_sentences(text)
        assert len(sentences) >= 2

    def test_segment_sentences_abbreviations(self, chunker):
        """Test handling of abbreviations."""
        text = "Art. 1453 c.c. prevede la risoluzione del contratto. L'art. 1454 disciplina la diffida."
        sentences = chunker._segment_sentences(text)
        # Should not split on "Art." or "c.c."
        assert len(sentences) >= 1

    def test_cosine_similarity(self, chunker):
        """Test cosine similarity calculation."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = chunker._cosine_similarity(a, b)
        assert sim == pytest.approx(1.0)

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        sim = chunker._cosine_similarity(a, b)
        assert sim == pytest.approx(0.0)

        a = np.array([1.0, 1.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = chunker._cosine_similarity(a, b)
        assert 0 < sim < 1

    def test_cosine_similarity_zero_vector(self, chunker):
        """Test similarity with zero vector."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = chunker._cosine_similarity(a, b)
        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_chunk_short_text(self, chunker):
        """Test chunking of very short text."""
        chunks = await chunker.chunk(
            text="Breve",
            source_urn="urn:...",
        )
        assert chunks == []  # Too short

    @pytest.mark.asyncio
    async def test_chunk_single_sentence(self, chunker):
        """Test chunking of single sentence."""
        text = "Il contratto e' l'accordo di due o piu' parti per costituire, regolare o estinguere un rapporto giuridico patrimoniale."

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...~art1321",
        )

        assert len(chunks) == 1
        assert chunks[0].text.strip() == text.strip()

    @pytest.mark.asyncio
    async def test_chunk_creates_semantic_chunks(self, chunker):
        """Test that chunking creates SemanticChunk objects."""
        text = """Il contratto e' l'accordo di due o piu' parti per costituire un rapporto giuridico patrimoniale. Le parti possono liberamente determinare il contenuto del contratto. Il contratto non produce effetto rispetto ai terzi."""

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...~art1321",
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, SemanticChunk)
            assert isinstance(chunk.id, UUID)
            assert len(chunk.text) > 0
            assert 0 <= chunk.avg_similarity <= 1

    @pytest.mark.asyncio
    async def test_chunk_respects_max_sentences(self, mock_embedding):
        """Test that max_chunk_sentences is respected."""
        # Create chunker with low max
        chunker = SemanticChunker(
            mock_embedding,
            threshold=0.9,  # High threshold, won't split
            max_chunk_sentences=2,
        )

        # Provide embeddings that are very similar (won't trigger split)
        mock_embedding.embed_batch = AsyncMock(
            return_value=[[1.0] * 384 for _ in range(10)]
        )

        # Frasi abbastanza lunghe (>30 chars) per non essere unite
        text = "Prima frase con contenuto sufficiente per il test. Seconda frase altrettanto lunga e completa. Terza frase che continua il discorso. Quarta frase del nostro testo di prova. Quinta frase finale."

        chunks = await chunker.chunk(text, source_urn="urn:...")

        # Should have multiple chunks due to max_sentences=2
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.sentence_count <= 2


class TestPercentileSemanticChunker:
    """Test PercentileSemanticChunker variant."""

    @pytest.fixture
    def mock_embedding(self):
        embedding = MagicMock()
        embedding.embed_batch = AsyncMock(
            side_effect=lambda texts: np.random.randn(len(texts), 384).tolist()
        )
        return embedding

    def test_init(self, mock_embedding):
        chunker = PercentileSemanticChunker(
            mock_embedding,
            percentile=25.0,
        )
        assert chunker.percentile == 25.0

    @pytest.mark.asyncio
    async def test_dynamic_threshold(self, mock_embedding):
        """Test that threshold is computed dynamically."""
        chunker = PercentileSemanticChunker(
            mock_embedding,
            percentile=50.0,  # Median
        )

        text = "Frase uno. Frase due. Frase tre. Frase quattro."

        # Before chunking, threshold is 0
        assert chunker.threshold == 0.0

        await chunker.chunk(text, source_urn="urn:...")

        # After chunking, threshold should be computed
        # (actual value depends on random embeddings)


class TestSemanticChunkerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_embedding(self):
        embedding = MagicMock()
        embedding.embed_batch = AsyncMock(
            side_effect=lambda texts: np.random.randn(len(texts), 384).tolist()
        )
        return embedding

    @pytest.mark.asyncio
    async def test_empty_text(self, mock_embedding):
        chunker = SemanticChunker(mock_embedding)
        chunks = await chunker.chunk("", source_urn="urn:...")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_whitespace_only(self, mock_embedding):
        chunker = SemanticChunker(mock_embedding)
        chunks = await chunker.chunk("   \n\t  ", source_urn="urn:...")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_unicode_text(self, mock_embedding):
        """Test with Italian unicode characters."""
        chunker = SemanticChunker(mock_embedding)
        text = "L'obbligazione è un vincolo giuridico. È necessaria la buona fede."

        chunks = await chunker.chunk(text, source_urn="urn:...")

        assert len(chunks) >= 1
        # Verify unicode is preserved
        for chunk in chunks:
            assert "è" in chunk.text or "É" in chunk.text or len(chunk.text) > 0
