"""
Test di Integrazione per merlt Core
====================================

Test end-to-end SENZA MOCK per verificare l'integrazione
completa di tutti i componenti del sistema.

Requisiti:
- Docker containers attivi (FalkorDB, Qdrant, PostgreSQL)
- docker-compose -f docker-compose.dev.yml up -d

Esecuzione:
    pytest tests/integration/test_core_integration.py -v
"""

import pytest
import asyncio
from typing import Dict, Any


# ============================================================================
# Test Import Components
# ============================================================================

class TestImports:
    """Verifica che tutti gli import funzionino correttamente."""

    def test_import_core(self):
        """Test import LegalKnowledgeGraph e MerltConfig."""
        from merlt import LegalKnowledgeGraph, MerltConfig
        assert LegalKnowledgeGraph is not None
        assert MerltConfig is not None

    def test_import_sources(self):
        """Test import scrapers."""
        from merlt.sources import NormattivaScraper, BrocardiScraper
        assert NormattivaScraper is not None
        assert BrocardiScraper is not None

    def test_import_storage(self):
        """Test import storage components."""
        from merlt.storage.graph import FalkorDBClient, FalkorDBConfig
        from merlt.storage import BridgeTable, EmbeddingService
        assert FalkorDBClient is not None
        assert FalkorDBConfig is not None
        assert BridgeTable is not None
        assert EmbeddingService is not None

    def test_import_pipeline(self):
        """Test import pipeline components."""
        from merlt.pipeline import IngestionPipelineV2, MultivigenzaPipeline
        from merlt.pipeline.parsing import CommaParser
        from merlt.pipeline.chunking import StructuralChunker
        assert IngestionPipelineV2 is not None
        assert MultivigenzaPipeline is not None
        assert CommaParser is not None
        assert StructuralChunker is not None

    def test_import_config(self):
        """Test import config."""
        from merlt.config import get_environment_config, TEST_ENV, PROD_ENV
        config = get_environment_config(TEST_ENV)
        assert config.name == "test"
        assert config.falkordb_graph == "merl_t_test"


# ============================================================================
# Test FalkorDB Integration
# ============================================================================

class TestFalkorDBIntegration:
    """Test integrazione con FalkorDB reale."""

    @pytest.fixture
    def falkordb_client(self):
        """Crea client FalkorDB per test."""
        from merlt.storage.graph import FalkorDBClient, FalkorDBConfig
        config = FalkorDBConfig(
            host="localhost",
            port=6380,
            graph_name="merl_t_integration_test"
        )
        return FalkorDBClient(config)

    @pytest.mark.asyncio
    async def test_falkordb_connect(self, falkordb_client):
        """Test connessione a FalkorDB."""
        await falkordb_client.connect()
        health = await falkordb_client.health_check()
        assert health is True
        await falkordb_client.close()

    @pytest.mark.asyncio
    async def test_falkordb_create_node(self, falkordb_client):
        """Test creazione nodo in FalkorDB."""
        await falkordb_client.connect()

        # Crea un nodo di test
        result = await falkordb_client.query(
            "CREATE (n:TestNode {id: $id, name: $name}) RETURN n",
            {"id": "test_123", "name": "Test Node"}
        )
        assert result is not None

        # Verifica che esista
        check = await falkordb_client.query(
            "MATCH (n:TestNode {id: $id}) RETURN n.name as name",
            {"id": "test_123"}
        )
        assert len(check) > 0
        assert check[0]["name"] == "Test Node"

        # Cleanup
        await falkordb_client.query(
            "MATCH (n:TestNode {id: $id}) DELETE n",
            {"id": "test_123"}
        )
        await falkordb_client.close()


# ============================================================================
# Test Bridge Table Integration
# ============================================================================

class TestBridgeTableIntegration:
    """Test integrazione con Bridge Table (PostgreSQL) reale."""

    @pytest.fixture
    def bridge_config(self):
        """Config per Bridge Table test."""
        from merlt.storage.bridge import BridgeTableConfig
        return BridgeTableConfig(
            host="localhost",
            port=5433,
            database="rlcf_dev",
            user="dev",
            password="devpassword"
        )

    @pytest.mark.asyncio
    async def test_bridge_table_health(self, bridge_config):
        """Test health check Bridge Table."""
        from merlt.storage.bridge import BridgeTable

        bridge = BridgeTable(bridge_config)
        await bridge.connect()

        health = await bridge.health_check()
        assert health is True

        await bridge.close()

    @pytest.mark.asyncio
    async def test_bridge_table_crud(self, bridge_config):
        """Test CRUD operations su Bridge Table."""
        from merlt.storage.bridge import BridgeTable
        from uuid import uuid4

        bridge = BridgeTable(bridge_config)
        await bridge.connect()

        # Create
        test_chunk_id = uuid4()
        test_urn = f"urn:test:integration:{test_chunk_id}"

        await bridge.add_mapping(
            chunk_id=test_chunk_id,
            graph_node_urn=test_urn,
            node_type="TestNorma",
            relation_type="test_relation",
            confidence=0.95,
            chunk_text="Testo di test per integrazione",
            metadata={"test": True}
        )

        # Read
        nodes = await bridge.get_nodes_for_chunk(test_chunk_id)
        assert len(nodes) > 0
        assert nodes[0]["graph_node_urn"] == test_urn

        # Delete (cleanup)
        await bridge.delete_mappings_for_chunk(test_chunk_id)

        # Verify deleted
        nodes_after = await bridge.get_nodes_for_chunk(test_chunk_id)
        assert len(nodes_after) == 0

        await bridge.close()


# ============================================================================
# Test Scraper Integration
# ============================================================================

class TestScraperIntegration:
    """Test integrazione scrapers con siti reali."""

    @pytest.mark.asyncio
    async def test_normattiva_scraper_fetch(self):
        """Test fetch da Normattiva reale."""
        from merlt.sources import NormattivaScraper
        from merlt.sources.utils.norma import NormaVisitata, Norma

        scraper = NormattivaScraper()
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        # API: get_document(normavisitata) -> Tuple[str, str]
        text, urn = await scraper.get_document(nv)

        # Deve contenere testo dell'art. 1 CC
        assert text is not None
        assert len(text) > 0
        # Art. 1 CC parla di "capacità giuridica"
        assert "capacità" in text.lower() or "persona" in text.lower()

    @pytest.mark.asyncio
    async def test_brocardi_scraper_fetch(self):
        """Test fetch da Brocardi reale."""
        from merlt.sources import BrocardiScraper
        from merlt.sources.utils.norma import NormaVisitata, Norma

        scraper = BrocardiScraper()
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1453")

        # API: get_info(norma_visitata) -> Tuple[Optional[str], Dict, Optional[str]]
        position, info, brocardi_url = await scraper.get_info(nv)

        # Deve avere almeno position o info
        assert info is not None
        # Art. 1453 è sulla risoluzione del contratto
        spiegazione = info.get("Spiegazione", "")
        if spiegazione:
            assert "risoluzione" in spiegazione.lower() or \
                   "contratto" in spiegazione.lower() or \
                   "inadempimento" in spiegazione.lower()


# ============================================================================
# Test Pipeline Integration
# ============================================================================

class TestPipelineIntegration:
    """Test integrazione pipeline di processing."""

    def test_comma_parser(self):
        """Test CommaParser con testo reale."""
        from merlt.pipeline.parsing import CommaParser

        # Testo Art. 52 CP (legittima difesa) - formato Normattiva
        article_text = """Art. 52
        Difesa legittima

        Non è punibile chi ha commesso il fatto per esservi stato costretto
        dalla necessità di difendere un diritto proprio od altrui contro
        il pericolo attuale di un'offesa ingiusta, sempre che la difesa
        sia proporzionata all'offesa.
        """

        parser = CommaParser()
        result = parser.parse(article_text)

        assert result is not None
        assert result.numero_articolo == "52"
        assert len(result.commas) >= 1  # API usa "commas" non "commi"

    def test_structural_chunker(self):
        """Test StructuralChunker."""
        from merlt.pipeline.parsing import CommaParser
        from merlt.pipeline.chunking import StructuralChunker

        # Formato corretto con "Art. X"
        article_text = """Art. 1218
        Responsabilità del debitore

        Il debitore che non esegue esattamente la prestazione dovuta
        è tenuto al risarcimento del danno.
        """

        parser = CommaParser()
        structure = parser.parse(article_text)

        chunker = StructuralChunker()
        # API: chunk_article(article_structure, article_urn, article_url, brocardi_position=None)
        chunks = chunker.chunk_article(
            article_structure=structure,
            article_urn="urn:nir:stato:codice.civile:1942-03-16;262~art1218",
            article_url="https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:codice.civile:1942-03-16;262~art1218"
        )

        assert len(chunks) >= 1
        assert chunks[0].urn is not None


# ============================================================================
# Test Embedding Service Integration
# ============================================================================

class TestEmbeddingIntegration:
    """Test integrazione EmbeddingService."""

    def test_embedding_service_singleton(self):
        """Test che EmbeddingService sia singleton."""
        from merlt.storage.vectors.embeddings import EmbeddingService

        service1 = EmbeddingService.get_instance()
        service2 = EmbeddingService.get_instance()

        assert service1 is service2

    def test_embedding_generation(self):
        """Test generazione embedding."""
        from merlt.storage.vectors.embeddings import EmbeddingService

        service = EmbeddingService.get_instance()

        # Query embedding
        query = "Cos'è la legittima difesa?"
        query_embedding = service.encode_query(query)

        assert query_embedding is not None
        assert len(query_embedding) == 1024  # E5-large dimension

        # Document embedding
        doc = "La legittima difesa è una causa di esclusione della punibilità."
        doc_embedding = service.encode_document(doc)

        assert doc_embedding is not None
        assert len(doc_embedding) == 1024


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
