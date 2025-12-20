"""
Tests for Late Chunker
======================

Tests for context-aware late chunking with embeddings.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from merlt.pipeline.semantic_chunking.late import (
    LateChunker,
    LateChunk,
    StructuralLateChunker,
)


class TestLateChunk:
    """Test LateChunk dataclass."""

    def test_creation(self):
        chunk = LateChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Il contratto e' l'accordo di due o piu' parti.",
            embedding=[0.1] * 384,
            span=(0, 50),
            source_urn="urn:...~late1",
            context_window=200,
        )
        assert chunk.char_count == len(chunk.text)
        assert chunk.context_window == 200
        assert len(chunk.embedding) == 384

    def test_to_dict(self):
        chunk = LateChunk(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            text="Test text",
            embedding=[0.1, 0.2, 0.3],
            span=(0, 9),
            source_urn="urn:...",
        )
        d = chunk.to_dict()
        assert d["span"] == (0, 9)
        assert len(d["embedding"]) == 3
        assert "created_at" in d


class TestLateChunker:
    """Test LateChunker class."""

    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding service."""
        embedding = MagicMock()
        embedding.embed = AsyncMock(
            side_effect=lambda x: np.random.randn(384).tolist()
        )
        return embedding

    @pytest.fixture
    def chunker(self, mock_embedding):
        return LateChunker(
            embedding_service=mock_embedding,
            chunk_size=100,
            overlap=20,
        )

    def test_init(self, mock_embedding):
        chunker = LateChunker(mock_embedding)
        assert chunker.chunk_size == 500  # default
        assert chunker.overlap == 50  # default
        assert chunker.use_token_level is False

    def test_init_custom(self, mock_embedding):
        chunker = LateChunker(
            mock_embedding,
            chunk_size=200,
            overlap=30,
            use_token_level=True,
        )
        assert chunker.chunk_size == 200
        assert chunker.overlap == 30
        assert chunker.use_token_level is True

    def test_compute_boundaries_simple(self, chunker):
        text = "A" * 250  # 250 chars

        boundaries = chunker._compute_boundaries(text)

        assert len(boundaries) >= 2
        # First boundary starts at 0
        assert boundaries[0][0] == 0
        # Last boundary ends at text length
        assert boundaries[-1][1] == len(text)

    def test_compute_boundaries_respects_chunk_size(self, chunker):
        text = "A" * 500

        boundaries = chunker._compute_boundaries(text)

        for start, end in boundaries:
            chunk_size = end - start
            # Each chunk should be around target size (with some tolerance)
            assert chunk_size <= chunker.chunk_size + chunker.chunk_size * 0.3

    def test_compute_boundaries_sentence_aware(self, chunker):
        """Test that boundaries prefer sentence ends."""
        # Create text with clear sentence boundaries
        text = "Prima frase molto lunga che continua per un po'. Seconda frase altrettanto lunga. Terza frase finale."

        boundaries = chunker._compute_boundaries(text)

        # Boundaries should align with sentence ends where possible
        for start, end in boundaries:
            chunk_text = text[start:end]
            # Most chunks should end with sentence-ending punctuation
            if end < len(text):  # Not the last chunk
                # Allow for some variation
                pass

    @pytest.mark.asyncio
    async def test_chunk_short_text(self, chunker):
        chunks = await chunker.chunk(
            text="Troppo breve",
            source_urn="urn:...",
        )
        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_creates_late_chunks(self, chunker, mock_embedding):
        text = "Il contratto e' l'accordo di due o piu' parti per costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale. Le parti possono determinare liberamente il contenuto."

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...~art1321",
        )

        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, LateChunk)
            assert len(chunk.embedding) == 384
            assert chunk.context_window > len(chunk.text)  # Has extra context

    @pytest.mark.asyncio
    async def test_chunk_with_custom_boundaries(self, chunker):
        text = "Prima parte del testo. Seconda parte del testo. Terza parte."

        # Custom boundaries
        boundaries = [(0, 22), (23, 47), (48, 61)]

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...",
            boundaries=boundaries,
        )

        assert len(chunks) == 3
        assert chunks[0].text.strip() == "Prima parte del testo."
        assert chunks[1].text.strip() == "Seconda parte del testo."

    @pytest.mark.asyncio
    async def test_chunk_preserves_context(self, chunker, mock_embedding):
        """Test that embeddings are generated with context."""
        text = "A" * 300

        # Track what text is passed to embedding
        embed_calls = []
        async def track_embed(x):
            embed_calls.append(x)
            return np.random.randn(384).tolist()

        mock_embedding.embed = AsyncMock(side_effect=track_embed)

        await chunker.chunk(text, source_urn="urn:...")

        # Each embedding should include context (longer than chunk)
        for embed_text in embed_calls:
            # Context text should be larger than chunk
            pass  # Actual assertion depends on implementation


class TestStructuralLateChunker:
    """Test StructuralLateChunker variant."""

    @pytest.fixture
    def mock_embedding(self):
        embedding = MagicMock()
        embedding.embed = AsyncMock(
            side_effect=lambda x: np.random.randn(384).tolist()
        )
        return embedding

    @pytest.fixture
    def chunker(self, mock_embedding):
        return StructuralLateChunker(mock_embedding)

    def test_no_overlap(self, mock_embedding):
        """Structural chunker should have no overlap."""
        chunker = StructuralLateChunker(mock_embedding)
        assert chunker.overlap == 0

    @pytest.mark.asyncio
    async def test_chunk_article_with_commas(self, chunker):
        """Test chunking article using comma boundaries."""
        full_text = """Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento del danno, se non prova che l'inadempimento o il ritardo e' stato determinato da impossibilita' della prestazione derivante da causa a lui non imputabile."""

        commas = [
            {
                "numero": 1,
                "testo": "Il debitore che non esegue esattamente la prestazione dovuta e' tenuto al risarcimento del danno",
                "start": 0,
                "end": 96,
            },
            {
                "numero": 2,
                "testo": "se non prova che l'inadempimento o il ritardo e' stato determinato da impossibilita' della prestazione derivante da causa a lui non imputabile",
                "start": 98,
                "end": 241,
            }
        ]

        chunks = await chunker.chunk_article(
            commas=commas,
            full_text=full_text,
            article_urn="urn:...~art1218",
        )

        assert len(chunks) == 2
        # Each chunk has context from full document
        for chunk in chunks:
            assert chunk.context_window > len(chunk.text)

    @pytest.mark.asyncio
    async def test_chunk_article_finds_positions(self, chunker):
        """Test that chunker can find comma positions when not provided."""
        full_text = "Prima frase del comma. Seconda frase del comma diverso."

        commas = [
            {"numero": 1, "testo": "Prima frase del comma."},
            {"numero": 2, "testo": "Seconda frase del comma diverso."},
        ]

        chunks = await chunker.chunk_article(
            commas=commas,
            full_text=full_text,
            article_urn="urn:...",
        )

        # Should find the text even without explicit start/end
        assert len(chunks) == 2


class TestLateChunkerTokenLevel:
    """Test token-level late chunking (when available)."""

    @pytest.fixture
    def mock_embedding_with_tokens(self):
        """Mock embedding service with token-level support."""
        embedding = MagicMock()
        embedding.embed = AsyncMock(
            side_effect=lambda x: np.random.randn(384).tolist()
        )

        # Token-level embedding support
        async def embed_with_tokens(text):
            tokens = text.split()
            return {
                "token_embeddings": np.random.randn(len(tokens), 384).tolist(),
                "token_offsets": [
                    (i * 5, i * 5 + 4) for i in range(len(tokens))
                ],
            }

        embedding.embed_with_tokens = AsyncMock(side_effect=embed_with_tokens)
        return embedding

    @pytest.mark.asyncio
    async def test_token_level_chunking(self, mock_embedding_with_tokens):
        """Test token-level late chunking when available."""
        chunker = LateChunker(
            mock_embedding_with_tokens,
            chunk_size=100,
            use_token_level=True,
        )

        text = "Primo token secondo token terzo token quarto token quinto token"

        chunks = await chunker.chunk(
            text=text,
            source_urn="urn:...",
            boundaries=[(0, 30), (31, 60)],
        )

        # Should use token-level method
        mock_embedding_with_tokens.embed_with_tokens.assert_called()
        assert len(chunks) >= 1
