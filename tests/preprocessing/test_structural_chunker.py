"""
Tests for Structural Chunker
============================

Tests the structural_chunker module for creating comma-level chunks
from parsed articles.
"""

import pytest
from uuid import UUID

from merlt.pipeline.parsing import ArticleStructure, Comma, parse_article
from merlt.pipeline.chunking import (
    StructuralChunker,
    Chunk,
    ChunkMetadata,
    chunk_article,
)


class TestChunkMetadata:
    """Test ChunkMetadata dataclass."""

    def test_default_values(self):
        meta = ChunkMetadata()
        assert meta.libro is None
        assert meta.fonte == "VisualexAPI"
        assert meta.comma_numero == 1

    def test_full_metadata(self):
        meta = ChunkMetadata(
            libro="IV",
            titolo="II",
            capo="XIV",
            articolo="1453",
            rubrica="Risoluzione per inadempimento",
            comma_numero=2,
        )
        assert meta.libro == "IV"
        assert meta.comma_numero == 2


class TestChunk:
    """Test Chunk dataclass."""

    def test_chunk_creation(self):
        meta = ChunkMetadata(articolo="1453", comma_numero=1)
        chunk = Chunk(
            chunk_id=UUID("12345678-1234-1234-1234-123456789abc"),
            urn="urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453-com1",
            url="https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453",
            text="Nei contratti con prestazioni corrispettive...",
            token_count=45,
            article_urn="urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453",
            metadata=meta,
        )
        assert chunk.chunk_id == UUID("12345678-1234-1234-1234-123456789abc")
        assert "-com1" in chunk.urn
        assert "-com" not in chunk.url  # URL should be article-level

    def test_to_dict(self):
        meta = ChunkMetadata(articolo="1453", comma_numero=1, libro="IV")
        chunk = Chunk(
            chunk_id=UUID("12345678-1234-1234-1234-123456789abc"),
            urn="urn:...~art1453-com1",
            url="https://normattiva.it/...",
            text="Test text",
            token_count=5,
            article_urn="urn:...~art1453",
            metadata=meta,
        )
        d = chunk.to_dict()
        assert d["chunk_id"] == "12345678-1234-1234-1234-123456789abc"
        assert d["metadata"]["libro"] == "IV"
        assert d["metadata"]["comma_numero"] == 1
        assert "created_at" in d


class TestStructuralChunkerParsePosition:
    """Test Brocardi position parsing."""

    def test_full_position(self):
        chunker = StructuralChunker()
        position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale, Capo XIV - Della risoluzione del contratto"
        libro, titolo, capo, sezione = chunker._parse_position(position)
        assert libro == "IV"
        assert titolo == "II"
        assert capo == "XIV"
        assert sezione is None

    def test_partial_position(self):
        chunker = StructuralChunker()
        position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti"
        libro, titolo, capo, sezione = chunker._parse_position(position)
        assert libro == "IV"
        assert titolo == "II"
        assert capo is None

    def test_libro_only(self):
        chunker = StructuralChunker()
        position = "Libro IV - Delle obbligazioni"
        libro, titolo, capo, sezione = chunker._parse_position(position)
        assert libro == "IV"
        assert titolo is None

    def test_none_position(self):
        chunker = StructuralChunker()
        libro, titolo, capo, sezione = chunker._parse_position(None)
        assert libro is None
        assert titolo is None

    def test_empty_position(self):
        chunker = StructuralChunker()
        libro, titolo, capo, sezione = chunker._parse_position("")
        assert libro is None


class TestStructuralChunkerGenerateURN:
    """Test chunk URN generation."""

    def test_comma_extension(self):
        chunker = StructuralChunker()
        article_urn = "urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"
        chunk_urn = chunker._generate_chunk_urn(article_urn, 1)
        assert chunk_urn == "urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453-com1"

    def test_multiple_commas(self):
        chunker = StructuralChunker()
        base = "urn:nir:stato:regio.decreto:1942-03-16;262:2~art1454"
        assert chunker._generate_chunk_urn(base, 1).endswith("-com1")
        assert chunker._generate_chunk_urn(base, 2).endswith("-com2")
        assert chunker._generate_chunk_urn(base, 3).endswith("-com3")


class TestStructuralChunkerChunkArticle:
    """Test full article chunking."""

    def test_art_1453_two_commas(self):
        """Test chunking of Art. 1453 with 2 commas."""
        text = """Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione."""

        article_structure = parse_article(text)
        article_urn = "urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"
        article_url = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"
        brocardi_position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale, Capo XIV - Della risoluzione del contratto"

        chunks = chunk_article(
            article_structure=article_structure,
            article_urn=article_urn,
            article_url=article_url,
            brocardi_position=brocardi_position,
        )

        assert len(chunks) == 2

        # Check first chunk
        chunk1 = chunks[0]
        assert isinstance(chunk1.chunk_id, UUID)
        assert chunk1.urn == f"{article_urn}-com1"
        assert chunk1.url == article_url  # URL is article-level
        assert "contratti con prestazioni corrispettive" in chunk1.text
        assert chunk1.article_urn == article_urn
        assert chunk1.metadata.libro == "IV"
        assert chunk1.metadata.titolo == "II"
        assert chunk1.metadata.capo == "XIV"
        assert chunk1.metadata.comma_numero == 1
        assert chunk1.metadata.articolo == "1453"
        assert chunk1.metadata.rubrica == "Risoluzione per inadempimento"

        # Check second chunk
        chunk2 = chunks[1]
        assert chunk2.urn == f"{article_urn}-com2"
        assert chunk2.metadata.comma_numero == 2
        assert "risoluzione può essere domandata" in chunk2.text

    def test_art_1454_three_commas(self):
        """Test with Art. 1454 (3 commas)."""
        text = """Articolo 1454
Diffida ad adempiere

Alla parte inadempiente l'altra può intimare per iscritto di adempiere in un congruo termine, con dichiarazione che, decorso inutilmente detto termine, il contratto s'intenderà senz'altro risoluto.

Il termine non può essere inferiore a quindici giorni, salvo diversa pattuizione delle parti o salvo che, per la natura del contratto o secondo gli usi, risulti congruo un termine minore.

Decorso il termine senza che il contratto sia stato adempiuto, questo è risoluto di diritto."""

        article_structure = parse_article(text)
        chunks = chunk_article(
            article_structure=article_structure,
            article_urn="urn:nir:...~art1454",
            article_url="https://normattiva.it/...",
        )

        assert len(chunks) == 3
        assert chunks[0].metadata.comma_numero == 1
        assert chunks[1].metadata.comma_numero == 2
        assert chunks[2].metadata.comma_numero == 3

    def test_without_brocardi_position(self):
        """Test chunking without Brocardi position."""
        text = """Articolo 1455
Importanza dell'inadempimento

Il contratto non si può risolvere se l'inadempimento di una delle parti ha scarsa importanza, avuto riguardo all'interesse dell'altra."""

        article_structure = parse_article(text)
        chunks = chunk_article(
            article_structure=article_structure,
            article_urn="urn:nir:...~art1455",
            article_url="https://normattiva.it/...",
            brocardi_position=None,
        )

        assert len(chunks) == 1
        assert chunks[0].metadata.libro is None
        assert chunks[0].metadata.articolo == "1455"

    def test_unique_chunk_ids(self):
        """Test that each chunk gets a unique UUID."""
        text = """Articolo 1456
Clausola risolutiva espressa

I contraenti possono convenire espressamente che il contratto si risolva nel caso che una determinata obbligazione non sia adempiuta secondo le modalità stabilite.

In questo caso, la risoluzione si verifica di diritto quando la parte interessata dichiara all'altra che intende valersi della clausola risolutiva."""

        article_structure = parse_article(text)
        chunks = chunk_article(
            article_structure=article_structure,
            article_urn="urn:nir:...~art1456",
            article_url="https://normattiva.it/...",
        )

        chunk_ids = [c.chunk_id for c in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))  # All unique


class TestStructuralChunkerBatch:
    """Test batch chunking."""

    def test_batch_chunking(self):
        """Test processing multiple articles."""
        # Prepare test data
        text1 = """Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento."""

        text2 = """Articolo 1454
Diffida ad adempiere

Alla parte inadempiente l'altra può intimare per iscritto di adempiere in un congruo termine."""

        articles = [
            {
                "article_structure": parse_article(text1),
                "article_urn": "urn:...~art1453",
                "article_url": "https://normattiva.it/art1453",
                "brocardi_position": "Libro IV - Obbligazioni",
            },
            {
                "article_structure": parse_article(text2),
                "article_urn": "urn:...~art1454",
                "article_url": "https://normattiva.it/art1454",
                "brocardi_position": "Libro IV - Obbligazioni",
            },
        ]

        chunker = StructuralChunker()
        all_chunks = chunker.chunk_batch(articles)

        assert len(all_chunks) == 3  # 2 commas from art1453 + 1 from art1454

        # Verify chunks from different articles have correct URNs
        art1453_chunks = [c for c in all_chunks if "art1453" in c.article_urn]
        art1454_chunks = [c for c in all_chunks if "art1454" in c.article_urn]

        assert len(art1453_chunks) == 2
        assert len(art1454_chunks) == 1


class TestChunkTokenCounting:
    """Test token counting in chunks."""

    def test_token_count_preserved(self):
        """Test that token count from comma is preserved in chunk."""
        text = """Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno."""

        article_structure = parse_article(text)
        chunks = chunk_article(
            article_structure=article_structure,
            article_urn="urn:...~art1453",
            article_url="https://normattiva.it/...",
        )

        assert len(chunks) == 1
        assert chunks[0].token_count == article_structure.commas[0].token_count
        assert chunks[0].token_count > 0
