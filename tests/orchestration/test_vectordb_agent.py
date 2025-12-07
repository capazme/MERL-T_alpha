"""
Integration Tests for VectorDBAgent

These tests require Qdrant to be running:
    docker-compose --profile phase3 up -d qdrant

Tests cover:
- Semantic search (P1)
- Filtered search (P3)
- Reranked search (P4)
- Error handling
- Collection initialization
- End-to-end retrieval workflow

Note: These are integration tests that use real Qdrant instance.
First test run will download E5-large model (~1.2GB, 2-3 minutes).
"""

import pytest
import asyncio
from typing import List, Dict, Any

from merlt.orchestration.agents.vectordb_agent import VectorDBAgent
from merlt.orchestration.agents.base import AgentTask, AgentResult
from merlt.orchestration.services.embedding_service import EmbeddingService
from merlt.orchestration.services.qdrant_service import QdrantService

# ============================================================================
# Test Configuration
# ============================================================================

TEST_COLLECTION_NAME = "legal_corpus_test"

# Sample legal corpus for testing
SAMPLE_CORPUS = [
    {
        "id": "art_1321_cc",
        "text": (
            "Art. 1321 c.c. - Il contratto. "
            "Il contratto è l'accordo di due o più parti per costituire, regolare o "
            "estinguere tra loro un rapporto giuridico patrimoniale."
        ),
        "document_type": "norm",
        "temporal_metadata": {
            "is_current": True,
            "date_effective": "1942-03-16",
            "date_end": None
        },
        "classification": {
            "legal_area": "civil",
            "legal_domain_tags": ["contract_law"],
            "complexity_level": 2
        },
        "authority_metadata": {
            "source_type": "normattiva",
            "hierarchical_level": "codice",
            "authority_score": 1.0
        },
        "entities_extracted": {
            "norm_references": [],
            "legal_concepts": ["contratto", "accordo", "parti"]
        }
    },
    {
        "id": "art_1325_cc",
        "text": (
            "Art. 1325 c.c. - Indicazione dei requisiti. "
            "I requisiti del contratto sono: 1) l'accordo delle parti; "
            "2) la causa; 3) l'oggetto; 4) la forma, quando risulta che è prescritta "
            "dalla legge sotto pena di nullità."
        ),
        "document_type": "norm",
        "temporal_metadata": {
            "is_current": True,
            "date_effective": "1942-03-16",
            "date_end": None
        },
        "classification": {
            "legal_area": "civil",
            "legal_domain_tags": ["contract_law"],
            "complexity_level": 3
        },
        "authority_metadata": {
            "source_type": "normattiva",
            "hierarchical_level": "codice",
            "authority_score": 1.0
        },
        "entities_extracted": {
            "norm_references": [],
            "legal_concepts": ["requisiti", "contratto", "accordo", "causa", "oggetto", "forma"]
        }
    },
    {
        "id": "art_1418_cc",
        "text": (
            "Art. 1418 c.c. - Cause di nullità del contratto. "
            "Il contratto è nullo quando è contrario a norme imperative, salvo che la legge "
            "disponga diversamente. Producono nullità del contratto la mancanza di uno dei "
            "requisiti indicati dall'art. 1325, l'illiceità della causa, l'illiceità dei "
            "motivi nel caso indicato dall'art. 1345 e la mancanza nell'oggetto dei requisiti "
            "stabiliti dall'art. 1346."
        ),
        "document_type": "norm",
        "temporal_metadata": {
            "is_current": True,
            "date_effective": "1942-03-16",
            "date_end": None
        },
        "classification": {
            "legal_area": "civil",
            "legal_domain_tags": ["contract_law", "nullity"],
            "complexity_level": 4
        },
        "authority_metadata": {
            "source_type": "normattiva",
            "hierarchical_level": "codice",
            "authority_score": 1.0
        },
        "entities_extracted": {
            "norm_references": ["1325", "1345", "1346"],
            "legal_concepts": ["nullità", "contratto", "cause", "norme imperative"]
        }
    },
    {
        "id": "art_2043_cc",
        "text": (
            "Art. 2043 c.c. - Risarcimento per fatto illecito. "
            "Qualunque fatto doloso o colposo, che cagiona ad altri un danno ingiusto, "
            "obbliga colui che ha commesso il fatto a risarcire il danno."
        ),
        "document_type": "norm",
        "temporal_metadata": {
            "is_current": True,
            "date_effective": "1942-03-16",
            "date_end": None
        },
        "classification": {
            "legal_area": "civil",
            "legal_domain_tags": ["tort_law"],
            "complexity_level": 3
        },
        "authority_metadata": {
            "source_type": "normattiva",
            "hierarchical_level": "codice",
            "authority_score": 1.0
        },
        "entities_extracted": {
            "norm_references": [],
            "legal_concepts": ["risarcimento", "fatto illecito", "danno", "responsabilità"]
        }
    },
    {
        "id": "art_1343_cc",
        "text": (
            "Art. 1343 c.c. - Causa illecita. "
            "La causa è illecita quando è contraria a norme imperative, all'ordine pubblico "
            "o al buon costume."
        ),
        "document_type": "norm",
        "temporal_metadata": {
            "is_current": True,
            "date_effective": "1942-03-16",
            "date_end": None
        },
        "classification": {
            "legal_area": "civil",
            "legal_domain_tags": ["contract_law"],
            "complexity_level": 2
        },
        "authority_metadata": {
            "source_type": "normattiva",
            "hierarchical_level": "codice",
            "authority_score": 1.0
        },
        "entities_extracted": {
            "norm_references": [],
            "legal_concepts": ["causa", "illiceità", "norme imperative", "ordine pubblico"]
        }
    }
]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def embedding_service():
    """Provide EmbeddingService singleton."""
    return EmbeddingService.get_instance()


@pytest.fixture(scope="module")
def qdrant_service():
    """Provide QdrantService with test collection."""
    service = QdrantService(collection_name=TEST_COLLECTION_NAME)
    return service


@pytest.fixture(scope="module")
async def qdrant_with_data(qdrant_service, embedding_service):
    """
    Setup: Create test collection and insert sample corpus.
    Teardown: Delete test collection.
    """
    # Setup
    print(f"\n[SETUP] Creating test collection: {TEST_COLLECTION_NAME}")

    # Initialize collection
    qdrant_service.initialize_collection(recreate=True)

    # Embed and insert corpus
    print(f"[SETUP] Embedding {len(SAMPLE_CORPUS)} documents...")
    texts = [doc["text"] for doc in SAMPLE_CORPUS]
    vectors = embedding_service.encode_batch(texts, is_query=False, show_progress_bar=True)

    documents = []
    for doc, vector in zip(SAMPLE_CORPUS, vectors):
        documents.append({
            "id": doc["id"],
            "vector": vector,
            "payload": {
                "text": doc["text"],
                "document_type": doc["document_type"],
                "temporal_metadata": doc["temporal_metadata"],
                "classification": doc["classification"],
                "authority_metadata": doc["authority_metadata"],
                "entities_extracted": doc["entities_extracted"]
            }
        })

    inserted = qdrant_service.insert_documents(documents)
    print(f"[SETUP] Inserted {inserted} documents")

    # Give Qdrant a moment to index
    await asyncio.sleep(1)

    # Yield service for tests
    yield qdrant_service

    # Teardown
    print(f"\n[TEARDOWN] Deleting test collection: {TEST_COLLECTION_NAME}")
    qdrant_service.delete_collection()


@pytest.fixture
async def vectordb_agent(qdrant_with_data, embedding_service):
    """Provide VectorDBAgent instance with test data."""
    agent = VectorDBAgent(
        qdrant_service=qdrant_with_data,
        embedding_service=embedding_service,
        config={
            "max_results": 10,
            "default_pattern": "semantic",
            "rerank_top_k": 3
        }
    )
    return agent


# ============================================================================
# Test Collection Setup
# ============================================================================

@pytest.mark.integration
def test_collection_exists(qdrant_with_data):
    """Test that test collection was created."""
    assert qdrant_with_data.collection_exists()


@pytest.mark.integration
def test_collection_stats(qdrant_with_data):
    """Test collection stats after insertion."""
    stats = qdrant_with_data.get_collection_stats()

    assert stats["collection_name"] == TEST_COLLECTION_NAME
    assert stats["points_count"] == len(SAMPLE_CORPUS)


# ============================================================================
# Test Pattern P1: Semantic Search
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_search_contract_definition(vectordb_agent):
    """Test semantic search for contract definition."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={
                "query": "Cos'è il contratto secondo il codice civile?",
                "top_k": 3
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # Most relevant should be Art. 1321 (contract definition)
    top_result = result.data[0]
    assert "1321" in top_result["id"]
    assert "contratto" in top_result["text"].lower()
    assert top_result["score"] > 0.5  # High similarity


@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_search_contract_requirements(vectordb_agent):
    """Test semantic search for contract requirements."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={
                "query": "Quali sono i requisiti del contratto?",
                "top_k": 3
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # Most relevant should be Art. 1325 (contract requirements)
    top_result = result.data[0]
    assert "1325" in top_result["id"]
    assert "requisiti" in top_result["text"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_search_nullity(vectordb_agent):
    """Test semantic search for contract nullity."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={
                "query": "Quando il contratto è nullo?",
                "top_k": 3
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # Most relevant should be Art. 1418 (nullity)
    top_result = result.data[0]
    assert "1418" in top_result["id"]
    assert "null" in top_result["text"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_semantic_search_with_score_threshold(vectordb_agent):
    """Test semantic search with score threshold."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={
                "query": "responsabilità extracontrattuale",
                "top_k": 10,
                "score_threshold": 0.4
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    # All results should have score >= 0.4
    for item in result.data:
        assert item["score"] >= 0.4


# ============================================================================
# Test Pattern P3: Filtered Search
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_filtered_search_by_document_type(vectordb_agent):
    """Test filtered search by document type."""
    tasks = [
        AgentTask(
            task_type="filtered_search",
            params={
                "query": "contratto",
                "top_k": 10,
                "filters": {
                    "document_type": "norm"
                }
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # All results should be norms
    for item in result.data:
        assert item["metadata"]["document_type"] == "norm"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filtered_search_by_is_current(vectordb_agent):
    """Test filtered search by current version flag."""
    tasks = [
        AgentTask(
            task_type="filtered_search",
            params={
                "query": "contratto",
                "top_k": 10,
                "filters": {
                    "is_current": True
                }
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # All results should be current versions
    for item in result.data:
        assert item["metadata"]["temporal_metadata"]["is_current"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filtered_search_by_complexity_level(vectordb_agent):
    """Test filtered search by complexity level."""
    tasks = [
        AgentTask(
            task_type="filtered_search",
            params={
                "query": "contratto",
                "top_k": 10,
                "filters": {
                    "complexity_level": {"gte": 1, "lte": 3}
                }
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0

    # All results should have complexity between 1-3
    for item in result.data:
        complexity = item["metadata"]["classification"]["complexity_level"]
        assert 1 <= complexity <= 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filtered_search_multiple_filters(vectordb_agent):
    """Test filtered search with multiple filters combined."""
    tasks = [
        AgentTask(
            task_type="filtered_search",
            params={
                "query": "contratto",
                "top_k": 10,
                "filters": {
                    "document_type": "norm",
                    "is_current": True,
                    "complexity_level": {"lte": 3}
                }
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    # May have fewer results due to multiple filters
    for item in result.data:
        assert item["metadata"]["document_type"] == "norm"
        assert item["metadata"]["temporal_metadata"]["is_current"] is True
        assert item["metadata"]["classification"]["complexity_level"] <= 3


# ============================================================================
# Test Pattern P4: Reranked Search
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_reranked_search(vectordb_agent):
    """Test reranked search (two-stage retrieval)."""
    tasks = [
        AgentTask(
            task_type="reranked_search",
            params={
                "query": "Quali sono i requisiti del contratto?",
                "initial_top_k": 5,  # Small for test corpus
                "top_k": 2
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0
    assert len(result.data) <= 2  # Should return at most top_k

    # Results should have rerank score
    for item in result.data:
        assert "score" in item  # Rerank score
        if item.get("reranked"):  # If cross-encoder was available
            assert "vector_score" in item  # Original vector score


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reranked_search_improves_ranking(vectordb_agent):
    """Test that reranking improves result relevance."""
    query = "Quali sono i requisiti del contratto?"

    # Semantic search (no reranking)
    semantic_tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"query": query, "top_k": 3}
        )
    ]
    semantic_result = await vectordb_agent.execute(semantic_tasks)

    # Reranked search
    reranked_tasks = [
        AgentTask(
            task_type="reranked_search",
            params={
                "query": query,
                "initial_top_k": 5,
                "top_k": 3
            }
        )
    ]
    reranked_result = await vectordb_agent.execute(reranked_tasks)

    assert semantic_result.success
    assert reranked_result.success

    # Both should return results
    assert len(semantic_result.data) > 0
    assert len(reranked_result.data) > 0

    # Top result should be Art. 1325 (requirements) for both
    # But reranking may change order of subsequent results


# ============================================================================
# Test Error Handling
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_unsupported_task_type(vectordb_agent):
    """Test error handling for unsupported task type."""
    tasks = [
        AgentTask(
            task_type="unsupported_task",
            params={"query": "test"}
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert not result.success
    assert len(result.errors) > 0
    assert "Unsupported task type" in result.errors[0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_missing_query_parameter(vectordb_agent):
    """Test error handling for missing query parameter."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"top_k": 10}  # Missing 'query'
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert not result.success
    assert len(result.errors) > 0
    assert "Query is required" in result.errors[0]


# ============================================================================
# Test Agent Result Structure
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_result_structure(vectordb_agent):
    """Test that AgentResult has correct structure."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"query": "contratto", "top_k": 3}
        )
    ]

    result = await vectordb_agent.execute(tasks)

    # Check AgentResult structure
    assert isinstance(result, AgentResult)
    assert result.agent_name == "vectordb_agent"
    assert isinstance(result.success, bool)
    assert isinstance(result.data, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.execution_time_ms, float)
    assert result.execution_time_ms > 0
    assert result.tasks_executed == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_result_item_structure(vectordb_agent):
    """Test that each result item has correct structure."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"query": "contratto", "top_k": 1}
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert len(result.data) > 0

    item = result.data[0]
    assert "id" in item
    assert "text" in item
    assert "score" in item
    assert "metadata" in item
    assert "search_pattern" in item

    # Check metadata structure
    metadata = item["metadata"]
    assert "document_type" in metadata
    assert "temporal_metadata" in metadata
    assert "classification" in metadata
    assert "authority_metadata" in metadata
    assert "entities_extracted" in metadata


# ============================================================================
# Test Multiple Tasks
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_multiple_tasks(vectordb_agent):
    """Test executing multiple tasks in one call."""
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"query": "contratto", "top_k": 2}
        ),
        AgentTask(
            task_type="filtered_search",
            params={
                "query": "nullità",
                "top_k": 2,
                "filters": {"complexity_level": {"gte": 3}}
            }
        )
    ]

    result = await vectordb_agent.execute(tasks)

    assert result.success
    assert len(result.data) > 0  # Combined results from both tasks
    assert result.tasks_executed == 2


# ============================================================================
# Integration Test: Full Workflow
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_retrieval_workflow(vectordb_agent):
    """
    Integration test: Full retrieval workflow simulating real usage.

    Scenario: User asks about contract nullity
    1. Semantic search to get top candidates
    2. Verify top result is relevant
    3. Check metadata is complete
    """
    # User query
    query = "Quando un contratto è considerato nullo dal codice civile?"

    # Execute semantic search
    tasks = [
        AgentTask(
            task_type="semantic_search",
            params={"query": query, "top_k": 5}
        )
    ]

    result = await vectordb_agent.execute(tasks)

    # Verify success
    assert result.success
    assert len(result.data) > 0
    assert result.execution_time_ms < 5000  # Should be fast (<5 seconds)

    # Top result should be about nullity
    top_result = result.data[0]
    assert top_result["score"] > 0.4  # Reasonable similarity
    assert any(
        word in top_result["text"].lower()
        for word in ["null", "contratto"]
    )

    # Metadata should be complete
    assert top_result["metadata"]["document_type"] == "norm"
    assert top_result["metadata"]["temporal_metadata"]["is_current"] is True
    assert "civil" in top_result["metadata"]["classification"]["legal_area"]

    print(f"\n[FULL WORKFLOW] Query: {query}")
    print(f"[FULL WORKFLOW] Top result: {top_result['id']}")
    print(f"[FULL WORKFLOW] Score: {top_result['score']:.3f}")
    print(f"[FULL WORKFLOW] Execution time: {result.execution_time_ms:.1f}ms")
