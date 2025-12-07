"""
Tests for Ingestion Pipeline v2
===============================

Tests the ingestion_pipeline_v2 module for comma-level chunking
and Bridge Table mapping preparation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from merlt.preprocessing.ingestion_pipeline_v2 import (
    IngestionPipelineV2,
    IngestionResult,
    BridgeMapping,
    ingest_article_v2,
)
from merlt.preprocessing.visualex_ingestion import VisualexArticle, NormaMetadata


# Test fixtures
@pytest.fixture
def sample_metadata():
    """Create sample NormaMetadata."""
    return NormaMetadata(
        tipo_atto="codice civile",
        data="1942-03-16",
        numero_atto="262",
        numero_articolo="1453",
    )


@pytest.fixture
def sample_article(sample_metadata):
    """Create sample VisualexArticle."""
    return VisualexArticle(
        metadata=sample_metadata,
        article_text="""Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione.""",
        url="https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453",
        brocardi_info={
            "Position": "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale, Capo XIV - Della risoluzione del contratto",
            "Ratio": "Fondamento normativo del rimedio risolutorio nei contratti sinallagmatici.",
            "Spiegazione": "L'articolo disciplina la risoluzione per inadempimento...",
            "Massime": [
                {
                    "corte": "Cassazione",
                    "numero": "15353/2020",
                    "estratto": "La domanda di risoluzione e quella di adempimento sono alternative."
                },
                {
                    "corte": "Cassazione",
                    "numero": "8524/2019",
                    "estratto": "Il passaggio dalla domanda di adempimento a quella di risoluzione è sempre possibile."
                }
            ]
        }
    )


@pytest.fixture
def sample_article_no_brocardi(sample_metadata):
    """Create sample article without Brocardi info."""
    return VisualexArticle(
        metadata=sample_metadata,
        article_text="""Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie.""",
        url="https://www.normattiva.it/...",
        brocardi_info=None,
    )


class TestBridgeMapping:
    """Test BridgeMapping dataclass."""

    def test_creation(self):
        mapping = BridgeMapping(
            chunk_id=UUID("12345678-1234-1234-1234-123456789abc"),
            graph_node_urn="urn:nir:...~art1453",
            mapping_type="PRIMARY",
            confidence=1.0,
        )
        assert mapping.mapping_type == "PRIMARY"
        assert mapping.confidence == 1.0


class TestIngestionResult:
    """Test IngestionResult dataclass."""

    def test_summary(self):
        result = IngestionResult(
            article_urn="urn:...~art1453",
            article_url="https://normattiva.it/...",
            chunks=[],
            bridge_mappings=[],
            nodes_created=["node1", "node2"],
            relations_created=["rel1"],
            brocardi_enriched=True,
        )
        summary = result.summary()
        assert summary["nodes"] == 2
        assert summary["relations"] == 1
        assert summary["brocardi"] is True


class TestIngestionPipelineV2Init:
    """Test pipeline initialization."""

    def test_init_without_clients(self):
        pipeline = IngestionPipelineV2()
        assert pipeline.falkordb is None
        assert pipeline.parser is not None
        assert pipeline.chunker is not None

    def test_init_with_mock_client(self):
        mock_falkordb = MagicMock()
        pipeline = IngestionPipelineV2(falkordb_client=mock_falkordb)
        assert pipeline.falkordb is mock_falkordb


class TestRomanToArabic:
    """Test Roman numeral conversion."""

    def test_simple_numerals(self):
        pipeline = IngestionPipelineV2()
        assert pipeline._roman_to_arabic("I") == 1
        assert pipeline._roman_to_arabic("V") == 5
        assert pipeline._roman_to_arabic("X") == 10

    def test_compound_numerals(self):
        pipeline = IngestionPipelineV2()
        assert pipeline._roman_to_arabic("IV") == 4
        assert pipeline._roman_to_arabic("IX") == 9
        assert pipeline._roman_to_arabic("XIV") == 14

    def test_libro_iv(self):
        pipeline = IngestionPipelineV2()
        assert pipeline._roman_to_arabic("IV") == 4


class TestExtractHierarchyURNs:
    """Test hierarchy URN extraction."""

    def test_full_position(self):
        pipeline = IngestionPipelineV2()
        codice_urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2"
        position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale, Capo XIV - Della risoluzione"

        hierarchy = pipeline._extract_hierarchy_urns(codice_urn, position)

        assert hierarchy.libro == f"{codice_urn}~libro4"
        assert hierarchy.titolo == f"{codice_urn}~libro4~tit2"
        assert hierarchy.capo == f"{codice_urn}~libro4~tit2~capo14"
        assert hierarchy.sezione is None  # Not in position

    def test_libro_only(self):
        pipeline = IngestionPipelineV2()
        codice_urn = "urn:...;262:2"
        position = "Libro IV - Delle obbligazioni"

        hierarchy = pipeline._extract_hierarchy_urns(codice_urn, position)

        assert hierarchy.libro == f"{codice_urn}~libro4"
        assert hierarchy.titolo is None
        assert hierarchy.capo is None
        assert hierarchy.sezione is None

    def test_no_position(self):
        pipeline = IngestionPipelineV2()
        hierarchy = pipeline._extract_hierarchy_urns("urn:...", None)
        assert hierarchy.libro is None
        assert hierarchy.titolo is None
        assert hierarchy.capo is None
        assert hierarchy.sezione is None

    def test_closest_parent(self):
        """Test closest_parent returns the most specific level available."""
        pipeline = IngestionPipelineV2()
        codice_urn = "urn:codice"
        position = "Libro IV - Obbligazioni, Titolo II - Contratti, Capo XIV - Risoluzione"

        hierarchy = pipeline._extract_hierarchy_urns(codice_urn, position)
        # Should return capo (most specific available)
        assert hierarchy.closest_parent(codice_urn) == hierarchy.capo


class TestExtractTitles:
    """Test title extraction from Brocardi position."""

    def test_extract_hierarchy_title_libro(self):
        pipeline = IngestionPipelineV2()
        position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti"
        assert pipeline._extract_hierarchy_title(position, 'libro') == "Delle obbligazioni"

    def test_extract_hierarchy_title_titolo(self):
        pipeline = IngestionPipelineV2()
        position = "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale"
        assert pipeline._extract_hierarchy_title(position, 'titolo') == "Dei contratti in generale"

    def test_extract_hierarchy_title_capo(self):
        pipeline = IngestionPipelineV2()
        position = "Libro IV - Obbligazioni, Titolo II - Contratti, Capo XIV - Della risoluzione del contratto"
        assert pipeline._extract_hierarchy_title(position, 'capo') == "Della risoluzione del contratto"

    def test_extract_hierarchy_title_sezione(self):
        pipeline = IngestionPipelineV2()
        position = "Libro I - Persone, Titolo V - Famiglia, Capo I - Matrimonio, Sezione II - Dei diritti e doveri"
        assert pipeline._extract_hierarchy_title(position, 'sezione') == "Dei diritti e doveri"


class TestPrepareBridgeMappings:
    """Test Bridge Table mapping preparation."""

    def test_primary_mappings(self, sample_article):
        pipeline = IngestionPipelineV2()

        # Parse and chunk
        from merlt.preprocessing.comma_parser import parse_article
        from merlt.preprocessing.structural_chunker import chunk_article

        article_structure = parse_article(sample_article.article_text)
        chunks = chunk_article(
            article_structure=article_structure,
            article_urn="urn:...~art1453",
            article_url="https://normattiva.it/...",
        )

        mappings = pipeline._prepare_bridge_mappings(
            chunks=chunks,
            article_urn="urn:...~art1453",
            codice_urn="urn:...;262:2",
            brocardi_position="Libro IV - Obbligazioni, Titolo II - Contratti",
        )

        # Should have mappings for each chunk
        assert len(mappings) > 0

        # Check PRIMARY mappings exist
        primary_mappings = [m for m in mappings if m.mapping_type == "PRIMARY"]
        assert len(primary_mappings) == len(chunks)
        assert all(m.confidence == 1.0 for m in primary_mappings)

        # Check HIERARCHIC mappings exist
        # Confidence varies by level: libro=0.90, titolo=0.92, capo=0.94, sezione=0.96
        hierarchic_mappings = [m for m in mappings if m.mapping_type == "HIERARCHIC"]
        assert len(hierarchic_mappings) > 0
        assert all(0.90 <= m.confidence <= 0.96 for m in hierarchic_mappings)


@pytest.mark.asyncio
class TestIngestArticleWithoutGraph:
    """Test article ingestion without graph creation."""

    async def test_ingest_creates_chunks(self, sample_article):
        pipeline = IngestionPipelineV2()

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=False,
        )

        # Should have created chunks
        assert len(result.chunks) == 2  # Art. 1453 has 2 commas
        assert result.chunks[0].urn.endswith("~comma1")
        assert result.chunks[1].urn.endswith("~comma2")

    async def test_ingest_creates_bridge_mappings(self, sample_article):
        pipeline = IngestionPipelineV2()

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=False,
        )

        # Should have bridge mappings
        assert len(result.bridge_mappings) > 0

        # Each chunk should have PRIMARY mapping
        primary = [m for m in result.bridge_mappings if m.mapping_type == "PRIMARY"]
        assert len(primary) == len(result.chunks)

    async def test_ingest_without_brocardi(self, sample_article_no_brocardi):
        pipeline = IngestionPipelineV2()

        result = await pipeline.ingest_article(
            article=sample_article_no_brocardi,
            create_graph_nodes=False,
        )

        assert len(result.chunks) == 1
        assert result.brocardi_enriched is False
        # Should still have PRIMARY mappings
        assert len(result.bridge_mappings) >= 1

    async def test_ingest_with_treextractor_fallback(self, sample_article_no_brocardi):
        """Test that treextractor fallback provides hierarchy when Brocardi not available."""
        from merlt.external_sources.visualex.tools.treextractor import (
            NormTree, NormNode, NormLevel
        )

        # Create mock NormTree with hierarchy for art. 1453
        mock_tree = NormTree(
            base_urn="urn:test",
            children=[
                NormNode(
                    level=NormLevel.LIBRO,
                    number="IV",
                    title="Delle obbligazioni",
                    children=[
                        NormNode(
                            level=NormLevel.TITOLO,
                            number="II",
                            title="Dei contratti in generale",
                            children=[
                                NormNode(
                                    level=NormLevel.CAPO,
                                    number="XIV",
                                    title="Della risoluzione del contratto",
                                    children=[
                                        NormNode(
                                            level=NormLevel.ARTICOLO,
                                            number="1453",
                                            url="https://test/art1453"
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        pipeline = IngestionPipelineV2()
        result = await pipeline.ingest_article(
            article=sample_article_no_brocardi,
            create_graph_nodes=False,
            norm_tree=mock_tree,
        )

        # Should have HIERARCHIC mappings from treextractor
        hierarchic = [m for m in result.bridge_mappings if m.mapping_type == "HIERARCHIC"]
        assert len(hierarchic) > 0, "Treextractor fallback should provide HIERARCHIC mappings"

        # Check that libro, titolo, capo are in the mappings
        hierarchic_urns = [m.graph_node_urn for m in hierarchic]
        assert any("libro4" in urn for urn in hierarchic_urns), "Should have libro mapping"
        assert any("tit2" in urn for urn in hierarchic_urns), "Should have titolo mapping"
        assert any("capo14" in urn for urn in hierarchic_urns), "Should have capo mapping"


@pytest.mark.asyncio
class TestIngestArticleWithGraph:
    """Test article ingestion with graph creation."""

    async def test_ingest_calls_falkordb(self, sample_article):
        mock_falkordb = AsyncMock()
        pipeline = IngestionPipelineV2(falkordb_client=mock_falkordb)

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=True,
        )

        # Should have called falkordb.query multiple times
        assert mock_falkordb.query.called
        call_count = mock_falkordb.query.call_count

        # Expected: codice + libro + titolo + articolo + 2 dottrina + 2 atto_giud
        # + relations for each
        assert call_count > 10

    async def test_ingest_creates_nodes(self, sample_article):
        mock_falkordb = AsyncMock()
        pipeline = IngestionPipelineV2(falkordb_client=mock_falkordb)

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=True,
        )

        # Should have node creation records
        assert len(result.nodes_created) > 0
        # Should include codice, libro, titolo, articolo
        node_types = [n.split(":")[0] for n in result.nodes_created]
        assert "Norma(codice)" in node_types
        assert "Norma(articolo)" in node_types

    async def test_ingest_creates_relations(self, sample_article):
        mock_falkordb = AsyncMock()
        pipeline = IngestionPipelineV2(falkordb_client=mock_falkordb)

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=True,
        )

        # Should have relation creation records
        assert len(result.relations_created) > 0
        # Should include contiene, commenta, interpreta
        rel_types = [r.split(":")[0] for r in result.relations_created]
        assert "contiene" in rel_types

    async def test_ingest_creates_brocardi_nodes(self, sample_article):
        mock_falkordb = AsyncMock()
        pipeline = IngestionPipelineV2(falkordb_client=mock_falkordb)

        result = await pipeline.ingest_article(
            article=sample_article,
            create_graph_nodes=True,
        )

        # Should have Dottrina and AttoGiudiziario nodes
        node_types = result.nodes_created
        dottrina_nodes = [n for n in node_types if n.startswith("Dottrina")]
        atto_nodes = [n for n in node_types if n.startswith("AttoGiudiziario")]

        # 2 Dottrina (ratio + spiegazione), 2 AttoGiudiziario (2 massime)
        assert len(dottrina_nodes) == 2
        assert len(atto_nodes) == 2


@pytest.mark.asyncio
class TestConvenienceFunction:
    """Test ingest_article_v2 convenience function."""

    async def test_ingest_article_v2(self, sample_article):
        result = await ingest_article_v2(
            article=sample_article,
            falkordb_client=None,
            create_graph=False,
        )

        assert isinstance(result, IngestionResult)
        assert len(result.chunks) == 2
