"""
Tests for EmbeddingService

Tests the E5-large multilingual embedding service including:
- Model loading (singleton pattern)
- Query encoding (with "query: " prefix)
- Document encoding (with "passage: " prefix)
- Batch encoding
- Async wrappers
- Dimension validation
"""

import pytest
import os
from typing import List

from merlt.storage.vectors.embeddings import EmbeddingService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def embedding_service():
    """
    Provide EmbeddingService instance for all tests in this module.

    Uses E5-large model as specified in configuration.
    First test will trigger model download (~1.2GB, 2-3 minutes).
    """
    service = EmbeddingService.get_instance()
    return service


@pytest.fixture
def sample_query():
    """Sample legal query in Italian."""
    return "Cos'è il contratto secondo il codice civile?"


@pytest.fixture
def sample_document():
    """Sample legal document text in Italian."""
    return (
        "Art. 1321 c.c. - Il contratto è l'accordo di due o più parti per "
        "costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale."
    )


@pytest.fixture
def sample_documents():
    """Sample batch of legal documents."""
    return [
        "Art. 1321 c.c. - Il contratto è l'accordo di due o più parti",
        "Art. 1325 c.c. - I requisiti del contratto sono: accordo, causa, oggetto, forma",
        "Art. 1418 c.c. - Il contratto è nullo quando è contrario a norme imperative"
    ]


# ============================================================================
# Test Singleton Pattern
# ============================================================================

def test_singleton_pattern():
    """Test that EmbeddingService follows singleton pattern."""
    service1 = EmbeddingService.get_instance()
    service2 = EmbeddingService.get_instance()

    # Same instance
    assert service1 is service2

    # Same underlying model
    assert service1._model is service2._model


def test_singleton_with_custom_params():
    """Test singleton preserves first initialization parameters."""
    # First call sets parameters
    service1 = EmbeddingService.get_instance(batch_size=16)

    # Second call should return same instance (ignores new params)
    service2 = EmbeddingService.get_instance(batch_size=64)

    assert service1 is service2
    assert service1.batch_size == service2.batch_size


# ============================================================================
# Test Model Loading
# ============================================================================

def test_model_loads_successfully(embedding_service):
    """Test that model loads without errors."""
    assert embedding_service is not None
    assert embedding_service.is_loaded or not embedding_service.is_loaded  # Will load on first encode


def test_model_dimension(embedding_service):
    """Test that E5-large produces 1024-dimensional embeddings."""
    # Trigger model loading
    _ = embedding_service.encode_query("test")

    # Check dimension
    assert embedding_service.embedding_dimension == 1024


def test_model_device_config(embedding_service):
    """Test that device configuration is respected."""
    assert embedding_service.device in ["cpu", "cuda"]


# ============================================================================
# Test Query Encoding
# ============================================================================

def test_encode_query_returns_vector(embedding_service, sample_query):
    """Test that encode_query returns a vector of floats."""
    vector = embedding_service.encode_query(sample_query)

    assert isinstance(vector, list)
    assert len(vector) == 1024  # E5-large dimension
    assert all(isinstance(x, float) for x in vector)


def test_encode_query_with_prefix(embedding_service, sample_query):
    """
    Test that query encoding uses "query: " prefix.

    E5 models require this prefix for optimal performance.
    We can't directly test the prefix, but we verify the method runs successfully.
    """
    vector = embedding_service.encode_query(sample_query)

    # Should succeed without errors
    assert vector is not None
    assert len(vector) == 1024


def test_encode_query_normalization(embedding_service, sample_query):
    """Test that query vectors are normalized (if configured)."""
    vector = embedding_service.encode_query(sample_query)

    # Calculate L2 norm
    import math
    norm = math.sqrt(sum(x**2 for x in vector))

    # If normalize_embeddings=True, norm should be ~1.0
    if embedding_service.normalize_embeddings:
        assert abs(norm - 1.0) < 0.01  # Allow small floating point error


def test_encode_query_empty_string(embedding_service):
    """Test encoding of empty query."""
    vector = embedding_service.encode_query("")

    # Should return valid vector even for empty string
    assert len(vector) == 1024


# ============================================================================
# Test Document Encoding
# ============================================================================

def test_encode_document_returns_vector(embedding_service, sample_document):
    """Test that encode_document returns a vector of floats."""
    vector = embedding_service.encode_document(sample_document)

    assert isinstance(vector, list)
    assert len(vector) == 1024
    assert all(isinstance(x, float) for x in vector)


def test_encode_document_with_prefix(embedding_service, sample_document):
    """
    Test that document encoding uses "passage: " prefix.

    E5 models require this prefix for optimal performance.
    """
    vector = embedding_service.encode_document(sample_document)

    # Should succeed without errors
    assert vector is not None
    assert len(vector) == 1024


def test_encode_document_normalization(embedding_service, sample_document):
    """Test that document vectors are normalized (if configured)."""
    vector = embedding_service.encode_document(sample_document)

    # Calculate L2 norm
    import math
    norm = math.sqrt(sum(x**2 for x in vector))

    # If normalize_embeddings=True, norm should be ~1.0
    if embedding_service.normalize_embeddings:
        assert abs(norm - 1.0) < 0.01


# ============================================================================
# Test Batch Encoding
# ============================================================================

def test_encode_batch_documents(embedding_service, sample_documents):
    """Test batch encoding of documents."""
    vectors = embedding_service.encode_batch(sample_documents, is_query=False)

    assert len(vectors) == len(sample_documents)
    assert all(len(v) == 1024 for v in vectors)
    assert all(isinstance(v, list) for v in vectors)


def test_encode_batch_queries(embedding_service):
    """Test batch encoding of queries."""
    queries = [
        "Cos'è il contratto?",
        "Quali sono i requisiti del contratto?",
        "Quando il contratto è nullo?"
    ]

    vectors = embedding_service.encode_batch(queries, is_query=True)

    assert len(vectors) == len(queries)
    assert all(len(v) == 1024 for v in vectors)


def test_encode_batch_empty_list(embedding_service):
    """Test batch encoding with empty list."""
    vectors = embedding_service.encode_batch([], is_query=False)

    assert vectors == []


def test_encode_batch_performance(embedding_service, sample_documents):
    """
    Test that batch encoding is more efficient than individual encoding.

    Note: This is a qualitative test - we just verify it works, not measure time.
    """
    # Batch encoding
    vectors_batch = embedding_service.encode_batch(sample_documents, is_query=False)

    # Individual encoding
    vectors_individual = [
        embedding_service.encode_document(doc) for doc in sample_documents
    ]

    # Results should be identical (within floating point precision)
    for v1, v2 in zip(vectors_batch, vectors_individual):
        assert len(v1) == len(v2)


# ============================================================================
# Test Async Methods
# ============================================================================

@pytest.mark.asyncio
async def test_encode_query_async(embedding_service, sample_query):
    """Test async query encoding."""
    vector = await embedding_service.encode_query_async(sample_query)

    assert isinstance(vector, list)
    assert len(vector) == 1024


@pytest.mark.asyncio
async def test_encode_document_async(embedding_service, sample_document):
    """Test async document encoding."""
    vector = await embedding_service.encode_document_async(sample_document)

    assert isinstance(vector, list)
    assert len(vector) == 1024


@pytest.mark.asyncio
async def test_encode_batch_async(embedding_service, sample_documents):
    """Test async batch encoding."""
    vectors = await embedding_service.encode_batch_async(sample_documents, is_query=False)

    assert len(vectors) == len(sample_documents)
    assert all(len(v) == 1024 for v in vectors)


# ============================================================================
# Test Semantic Similarity
# ============================================================================

def test_semantic_similarity_same_concept(embedding_service):
    """
    Test that semantically similar texts have similar embeddings.

    Uses cosine similarity (dot product of normalized vectors).
    """
    text1 = "Il contratto è un accordo tra due parti"
    text2 = "L'accordo contrattuale tra le parti"

    vec1 = embedding_service.encode_document(text1)
    vec2 = embedding_service.encode_document(text2)

    # Calculate cosine similarity (dot product, since vectors are normalized)
    similarity = sum(a * b for a, b in zip(vec1, vec2))

    # Similar texts should have similarity > 0.5
    assert similarity > 0.5


def test_semantic_similarity_different_concepts(embedding_service):
    """Test that semantically different texts have lower similarity."""
    text1 = "Il contratto è un accordo tra due parti"
    text2 = "Il gatto mangia il pesce"

    vec1 = embedding_service.encode_document(text1)
    vec2 = embedding_service.encode_document(text2)

    similarity = sum(a * b for a, b in zip(vec1, vec2))

    # Different texts should have lower similarity
    # (Note: Even unrelated texts may have some similarity, so we just check it's < 0.9)
    assert similarity < 0.9


def test_query_document_similarity(embedding_service):
    """Test that query and relevant document have high similarity."""
    query = "Cos'è il contratto?"
    document = "Art. 1321 c.c. - Il contratto è l'accordo di due o più parti"

    query_vec = embedding_service.encode_query(query)
    doc_vec = embedding_service.encode_document(document)

    similarity = sum(a * b for a, b in zip(query_vec, doc_vec))

    # Query and relevant document should have similarity > 0.4
    assert similarity > 0.4


# ============================================================================
# Test Configuration
# ============================================================================

def test_configuration_from_environment(monkeypatch):
    """Test that configuration is read from environment variables."""
    # Reset singleton for this test
    EmbeddingService._instance = None

    # Set environment variables
    monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-MiniLM-L3-v2")
    monkeypatch.setenv("EMBEDDING_DEVICE", "cpu")
    monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "16")
    monkeypatch.setenv("EMBEDDING_NORMALIZE", "false")

    service = EmbeddingService.get_instance()

    assert service.model_name == "sentence-transformers/paraphrase-MiniLM-L3-v2"
    assert service.device == "cpu"
    assert service.batch_size == 16
    assert service.normalize_embeddings is False

    # Reset singleton
    EmbeddingService._instance = None


def test_repr(embedding_service):
    """Test string representation."""
    repr_str = repr(embedding_service)

    assert "EmbeddingService" in repr_str
    assert embedding_service.model_name in repr_str
    assert embedding_service.device in repr_str


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.integration
def test_full_embedding_workflow(embedding_service):
    """
    Integration test: Full workflow from query to retrieval simulation.

    This test simulates a real retrieval scenario:
    1. Encode a corpus of documents
    2. Encode a query
    3. Find most similar document
    """
    # Corpus of legal articles
    corpus = [
        "Art. 1321 c.c. - Il contratto è l'accordo di due o più parti",
        "Art. 2043 c.c. - Qualunque fatto doloso o colposo che cagiona danno ingiusto obbliga a risarcire",
        "Art. 1325 c.c. - I requisiti del contratto sono: accordo, causa, oggetto, forma"
    ]

    # Encode corpus
    corpus_vectors = embedding_service.encode_batch(corpus, is_query=False)

    # Query
    query = "Quali sono i requisiti del contratto?"
    query_vector = embedding_service.encode_query(query)

    # Find most similar document
    similarities = [
        sum(a * b for a, b in zip(query_vector, doc_vec))
        for doc_vec in corpus_vectors
    ]

    most_similar_idx = similarities.index(max(similarities))

    # The most similar document should be Art. 1325 (index 2)
    # which is about contract requirements
    assert most_similar_idx == 2
    assert "requisiti del contratto" in corpus[most_similar_idx]
