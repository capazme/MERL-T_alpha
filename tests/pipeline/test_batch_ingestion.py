"""
Tests for Batch Ingestion Pipeline
==================================

Test suite robusto per verificare:
1. Nessuna perdita di dati durante batch processing
2. Embedding generation corretta (batch vs sequential equivalence)
3. Bridge table entries complete
4. Graph nodes creati correttamente
5. Parallel fetch funziona correttamente

Questi test sono CRITICI per garantire che l'ottimizzazione
non comprometta l'integrità dei dati.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from merlt.pipeline.batch_ingestion import (
    BatchIngestionPipeline,
    BatchIngestionResult,
    ArticleFetchResult,
)
from merlt.sources.utils.norma import NormaVisitata, Norma


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_kg():
    """Create mock LegalKnowledgeGraph."""
    kg = MagicMock()

    # Config
    kg.config = MagicMock()
    kg.config.qdrant_collection = "test_collection"

    # Scrapers
    kg._normattiva_scraper = AsyncMock()
    kg._brocardi_scraper = AsyncMock()

    # Pipeline
    kg._ingestion_pipeline = MagicMock()
    kg._ingestion_pipeline.ingest_article = AsyncMock()

    # Embedding service
    kg._embedding_service = MagicMock()
    kg._embedding_service.encode_batch_async = AsyncMock()

    # Qdrant
    kg._qdrant = MagicMock()
    kg._qdrant.upsert = MagicMock()

    # Bridge
    kg._bridge_builder = MagicMock()
    kg._bridge_builder.insert_mappings = AsyncMock(return_value=0)

    # Multivigenza
    kg._multivigenza_pipeline = MagicMock()
    kg._multivigenza_pipeline.ingest_with_history = AsyncMock()

    # Norm tree cache
    kg._get_cached_norm_tree = AsyncMock(return_value=None)

    return kg


@pytest.fixture
def sample_brocardi_info():
    """Sample Brocardi data with all fields."""
    return {
        "Position": "Libro IV - Delle obbligazioni, Titolo I - ...",
        "Spiegazione": "La norma disciplina le fonti delle obbligazioni. "
                       "Le obbligazioni possono nascere da contratto, fatto illecito, "
                       "o da ogni altro atto o fatto idoneo a produrle.",
        "Ratio": "Il legislatore ha voluto indicare le principali fonti "
                 "di obbligazioni, pur lasciando aperta la categoria residuale.",
        "Massime": [
            {
                "autorita": "Cass. civ.",
                "numero": "12345",
                "anno": "2023",
                "massima": "L'obbligazione sorge quando si verificano i presupposti "
                           "previsti dalla legge per la sua nascita.",
            },
            {
                "autorita": "Cass. civ.",
                "numero": "67890",
                "anno": "2022",
                "massima": "Il fatto illecito come fonte di obbligazione richiede "
                           "la sussistenza di tutti gli elementi costitutivi.",
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ArticleFetchResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestArticleFetchResult:
    """Test ArticleFetchResult dataclass."""

    def test_success_property_true(self):
        """Test success property when fetch is successful."""
        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        result = ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text="Le obbligazioni derivano da contratto...",
            article_url="https://normattiva.it/...",
            brocardi_info={"Spiegazione": "Test"},
        )

        assert result.success is True
        assert result.error is None

    def test_success_property_false_no_text(self):
        """Test success property when article_text is None."""
        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        result = ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text=None,
            error="Network error",
        )

        assert result.success is False

    def test_success_property_false_with_error(self):
        """Test success property when error is set."""
        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        result = ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text="Some text",
            error="Brocardi failed",
        )

        assert result.success is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BatchIngestionResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchIngestionResult:
    """Test BatchIngestionResult dataclass."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = BatchIngestionResult(
            total_articles=100,
            successful=75,
            failed=25,
            embeddings_created=300,
            graph_nodes_created=1000,
            bridge_mappings_created=400,
            duration_seconds=120.5,
        )

        assert result.success_rate == 0.75

    def test_success_rate_zero_articles(self):
        """Test success rate with zero articles."""
        result = BatchIngestionResult(
            total_articles=0,
            successful=0,
            failed=0,
            embeddings_created=0,
            graph_nodes_created=0,
            bridge_mappings_created=0,
            duration_seconds=0,
        )

        assert result.success_rate == 0.0

    def test_summary_format(self):
        """Test summary string format."""
        result = BatchIngestionResult(
            total_articles=10,
            successful=8,
            failed=2,
            embeddings_created=40,
            graph_nodes_created=100,
            bridge_mappings_created=32,
            duration_seconds=15.5,
        )

        summary = result.summary()

        assert "8/10" in summary
        assert "80.0%" in summary
        assert "40" in summary  # embeddings
        assert "100" in summary  # nodes
        assert "32" in summary  # bridge


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Parallel Fetch
# ═══════════════════════════════════════════════════════════════════════════════

class TestParallelFetch:
    """Test parallel article fetching."""

    @pytest.mark.asyncio
    async def test_fetch_articles_parallel_success(self, mock_kg):
        """Test that parallel fetch returns all articles."""
        # Setup mocks
        mock_kg._normattiva_scraper.get_document = AsyncMock(
            side_effect=[
                ("Testo articolo 1173", "https://url/1173"),
                ("Testo articolo 1174", "https://url/1174"),
                ("Testo articolo 1175", "https://url/1175"),
            ]
        )
        mock_kg._brocardi_scraper.get_info = AsyncMock(
            return_value=("Position", {"Spiegazione": "Test"}, "https://brocardi.it")
        )

        pipeline = BatchIngestionPipeline(
            kg=mock_kg,
            batch_size=10,
            max_concurrent_fetches=3,
        )

        results = await pipeline._fetch_articles_parallel(
            tipo_atto="codice civile",
            article_numbers=["1173", "1174", "1175"],
            include_brocardi=True,
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].article_text == "Testo articolo 1173"
        assert results[1].article_text == "Testo articolo 1174"
        assert results[2].article_text == "Testo articolo 1175"

    @pytest.mark.asyncio
    async def test_fetch_articles_parallel_partial_failure(self, mock_kg):
        """Test that partial failures are handled correctly."""
        mock_kg._normattiva_scraper.get_document = AsyncMock(
            side_effect=[
                ("Testo articolo 1173", "https://url/1173"),
                Exception("Network error"),
                ("Testo articolo 1175", "https://url/1175"),
            ]
        )
        mock_kg._brocardi_scraper.get_info = AsyncMock(
            return_value=("Position", {}, "https://brocardi.it")
        )

        pipeline = BatchIngestionPipeline(kg=mock_kg)

        results = await pipeline._fetch_articles_parallel(
            tipo_atto="codice civile",
            article_numbers=["1173", "1174", "1175"],
            include_brocardi=True,
        )

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None
        assert results[2].success is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Batch Embeddings - NO DATA LOSS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchEmbeddings:
    """Test batch embedding generation - CRITICAL for data integrity."""

    @pytest.mark.asyncio
    async def test_all_text_types_embedded(self, mock_kg, sample_brocardi_info):
        """
        CRITICAL TEST: Verify ALL text types are embedded.

        Must embed:
        1. Article text (norma)
        2. Spiegazione
        3. Ratio
        4. Each massima (up to 5)

        Total for sample: 1 + 1 + 1 + 2 = 5 embeddings
        """
        # Setup mock embedding service
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024 for _ in range(5)]  # 5 embeddings
        )

        # Create fetch result with full Brocardi info
        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        fetch_results = [ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text="Le obbligazioni derivano da contratto, da fatto illecito, "
                         "o da ogni altro atto o fatto idoneo a produrle.",
            article_url="https://normattiva.it/1173",
            brocardi_info=sample_brocardi_info,
        )]

        # Mock ingestion result
        mock_ingestion = MagicMock()
        mock_ingestion.article_urn = "urn:nir:stato:codice.civile~art1173"
        mock_ingestion.bridge_mappings = []
        ingestion_results = {"1173": mock_ingestion}

        pipeline = BatchIngestionPipeline(kg=mock_kg)

        # Run batch embeddings
        count = await pipeline._generate_embeddings_batch(
            fetch_results=fetch_results,
            ingestion_results=ingestion_results,
        )

        # Verify
        assert count == 5, f"Expected 5 embeddings (norma + spiegazione + ratio + 2 massime), got {count}"

        # Verify encode_batch_async was called with all texts
        call_args = mock_kg._embedding_service.encode_batch_async.call_args
        texts = call_args[0][0]

        assert len(texts) == 5
        # Verify text types
        assert any("obbligazioni derivano" in t for t in texts)  # norma
        assert any("disciplina le fonti" in t for t in texts)  # spiegazione
        assert any("legislatore ha voluto" in t for t in texts)  # ratio

    @pytest.mark.asyncio
    async def test_empty_brocardi_still_embeds_norma(self, mock_kg):
        """Test that article text is embedded even without Brocardi."""
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024]  # 1 embedding
        )

        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        fetch_results = [ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text="Testo articolo sufficientemente lungo per embedding test.",
            article_url="https://normattiva.it/1173",
            brocardi_info=None,  # No Brocardi
        )]

        mock_ingestion = MagicMock()
        mock_ingestion.article_urn = "urn:nir:stato:codice.civile~art1173"
        ingestion_results = {"1173": mock_ingestion}

        pipeline = BatchIngestionPipeline(kg=mock_kg)
        count = await pipeline._generate_embeddings_batch(
            fetch_results=fetch_results,
            ingestion_results=ingestion_results,
        )

        assert count == 1, "Should embed article text even without Brocardi"

    @pytest.mark.asyncio
    async def test_short_texts_skipped(self, mock_kg):
        """Test that short texts are correctly skipped."""
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024]
        )

        norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo="1173")

        # Brocardi with short texts that should be skipped
        brocardi_info = {
            "Spiegazione": "Breve",  # < 50 chars, should skip
            "Ratio": "Corto",  # < 50 chars, should skip
            "Massime": [
                {"massima": "Ok"},  # < 50 chars, should skip
            ],
        }

        fetch_results = [ArticleFetchResult(
            article_num="1173",
            norma_visitata=nv,
            article_text="Testo articolo sufficientemente lungo per essere embedded.",
            article_url="https://normattiva.it/1173",
            brocardi_info=brocardi_info,
        )]

        mock_ingestion = MagicMock()
        mock_ingestion.article_urn = "urn:nir:stato:codice.civile~art1173"
        ingestion_results = {"1173": mock_ingestion}

        pipeline = BatchIngestionPipeline(kg=mock_kg)
        count = await pipeline._generate_embeddings_batch(
            fetch_results=fetch_results,
            ingestion_results=ingestion_results,
        )

        # Only article text should be embedded
        assert count == 1, "Only article text should be embedded, short Brocardi texts skipped"

    @pytest.mark.asyncio
    async def test_multiple_articles_batch(self, mock_kg, sample_brocardi_info):
        """Test batch processing of multiple articles."""
        # Each article: norma + spiegazione + ratio + 2 massime = 5 embeddings
        # 3 articles = 15 embeddings
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024 for _ in range(15)]
        )

        fetch_results = []
        ingestion_results = {}

        for art_num in ["1173", "1174", "1175"]:
            norma = Norma(tipo_atto="codice civile", data=None, numero_atto=None)
            nv = NormaVisitata(norma=norma, numero_articolo=art_num)

            fetch_results.append(ArticleFetchResult(
                article_num=art_num,
                norma_visitata=nv,
                article_text=f"Testo articolo {art_num} sufficientemente lungo per test.",
                article_url=f"https://normattiva.it/{art_num}",
                brocardi_info=sample_brocardi_info,
            ))

            mock_ingestion = MagicMock()
            mock_ingestion.article_urn = f"urn:nir:stato:codice.civile~art{art_num}"
            ingestion_results[art_num] = mock_ingestion

        pipeline = BatchIngestionPipeline(kg=mock_kg)
        count = await pipeline._generate_embeddings_batch(
            fetch_results=fetch_results,
            ingestion_results=ingestion_results,
        )

        assert count == 15, f"Expected 15 embeddings (3 articles × 5 types), got {count}"

        # Verify single batch call (not sequential)
        assert mock_kg._embedding_service.encode_batch_async.call_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Bridge Table - NO DATA LOSS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBridgeTableIntegrity:
    """Test bridge table batch insertion."""

    @pytest.mark.asyncio
    async def test_all_mappings_inserted(self, mock_kg):
        """Test that all bridge mappings are inserted."""
        from merlt.models import BridgeMapping

        # Create mock ingestion results with mappings
        ingestion_results = {}
        for art_num in ["1173", "1174", "1175"]:
            mock_ingestion = MagicMock()
            mock_ingestion.bridge_mappings = [
                BridgeMapping(
                    chunk_id=f"chunk_{art_num}_1",
                    graph_node_urn=f"urn:art{art_num}",
                    mapping_type="PRIMARY",
                    confidence=1.0,
                    chunk_text=f"Text for {art_num}",
                ),
                BridgeMapping(
                    chunk_id=f"chunk_{art_num}_1",
                    graph_node_urn=f"urn:libro4",
                    mapping_type="HIERARCHIC",
                    confidence=0.9,
                    chunk_text=f"Text for {art_num}",
                ),
            ]
            ingestion_results[art_num] = mock_ingestion

        mock_kg._bridge_builder.insert_mappings = AsyncMock(return_value=6)

        pipeline = BatchIngestionPipeline(kg=mock_kg)
        count = await pipeline._insert_bridge_mappings_batch(ingestion_results)

        assert count == 6

        # Verify all mappings were passed
        call_args = mock_kg._bridge_builder.insert_mappings.call_args
        mappings = call_args[0][0]
        assert len(mappings) == 6  # 3 articles × 2 mappings


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Full Batch Processing
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullBatchProcessing:
    """Integration tests for full batch processing."""

    @pytest.mark.asyncio
    async def test_full_batch_success(self, mock_kg, sample_brocardi_info):
        """Test complete batch processing flow."""
        # Setup mocks for successful flow
        mock_kg._normattiva_scraper.get_document = AsyncMock(
            side_effect=[
                (f"Testo articolo {i} sufficientemente lungo per test.", f"https://url/{i}")
                for i in range(1173, 1178)
            ]
        )
        mock_kg._brocardi_scraper.get_info = AsyncMock(
            return_value=("Position", sample_brocardi_info, "https://brocardi.it")
        )

        # Mock ingestion pipeline
        async def mock_ingest(article, **kwargs):
            from merlt.models import BridgeMapping
            mock_result = MagicMock()
            mock_result.article_urn = f"urn:art{article.metadata.numero_articolo}"
            mock_result.nodes_created = ["node1", "node2"]
            mock_result.bridge_mappings = [
                BridgeMapping(
                    chunk_id="chunk1",
                    graph_node_urn=mock_result.article_urn,
                    mapping_type="PRIMARY",
                    confidence=1.0,
                    chunk_text="Test text",
                ),
            ]
            return mock_result

        mock_kg._ingestion_pipeline.ingest_article = AsyncMock(side_effect=mock_ingest)

        # Mock embeddings
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024 for _ in range(25)]  # 5 articles × 5 types
        )

        mock_kg._bridge_builder.insert_mappings = AsyncMock(return_value=5)

        pipeline = BatchIngestionPipeline(
            kg=mock_kg,
            batch_size=5,
            max_concurrent_fetches=5,
        )

        result = await pipeline.ingest_batch(
            tipo_atto="codice civile",
            article_numbers=["1173", "1174", "1175", "1176", "1177"],
            include_brocardi=True,
            include_multivigenza=False,  # Skip for simplicity
        )

        # Verify results
        assert result.successful == 5
        assert result.failed == 0
        assert result.embeddings_created == 25
        assert result.bridge_mappings_created == 5
        assert len(result.articles_processed) == 5

    @pytest.mark.asyncio
    async def test_batch_with_failures_continues(self, mock_kg):
        """Test that batch continues despite some failures."""
        # Some fetches fail
        mock_kg._normattiva_scraper.get_document = AsyncMock(
            side_effect=[
                ("Testo 1173", "https://url/1173"),
                Exception("Network error"),  # 1174 fails
                ("Testo 1175", "https://url/1175"),
            ]
        )
        mock_kg._brocardi_scraper.get_info = AsyncMock(
            return_value=("Position", {}, "https://brocardi.it")
        )

        async def mock_ingest(article, **kwargs):
            mock_result = MagicMock()
            mock_result.article_urn = f"urn:art{article.metadata.numero_articolo}"
            mock_result.nodes_created = ["node1"]
            mock_result.bridge_mappings = []
            return mock_result

        mock_kg._ingestion_pipeline.ingest_article = AsyncMock(side_effect=mock_ingest)
        mock_kg._embedding_service.encode_batch_async = AsyncMock(
            return_value=[[0.1] * 1024 for _ in range(2)]
        )
        mock_kg._bridge_builder.insert_mappings = AsyncMock(return_value=0)

        pipeline = BatchIngestionPipeline(kg=mock_kg)

        result = await pipeline.ingest_batch(
            tipo_atto="codice civile",
            article_numbers=["1173", "1174", "1175"],
            include_brocardi=True,
            include_multivigenza=False,
        )

        # 2 successful, 1 failed
        assert result.successful == 2
        assert result.failed == 1
        assert len(result.errors) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Concurrency Control
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrencyControl:
    """Test concurrency limiting."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_fetches(self, mock_kg):
        """Test that semaphore limits concurrent HTTP requests."""
        max_concurrent = 2
        concurrent_count = 0
        max_observed = 0

        async def counting_fetch(nv):
            nonlocal concurrent_count, max_observed
            concurrent_count += 1
            max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.1)  # Simulate network delay
            concurrent_count -= 1
            return (f"Text for {nv.numero_articolo}", f"https://url/{nv.numero_articolo}")

        mock_kg._normattiva_scraper.get_document = counting_fetch
        mock_kg._brocardi_scraper.get_info = AsyncMock(
            return_value=("Position", {}, "url")
        )

        pipeline = BatchIngestionPipeline(
            kg=mock_kg,
            max_concurrent_fetches=max_concurrent,
        )

        await pipeline._fetch_articles_parallel(
            tipo_atto="codice civile",
            article_numbers=["1", "2", "3", "4", "5"],
            include_brocardi=True,
        )

        # Max concurrent should not exceed limit
        assert max_observed <= max_concurrent, \
            f"Max concurrent {max_observed} exceeded limit {max_concurrent}"
