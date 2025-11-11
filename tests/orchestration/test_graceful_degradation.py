"""
Graceful Degradation Tests - Week 7 Preprocessing
==================================================

Tests system behavior when external dependencies are unavailable:
- Neo4j offline (KG enrichment fails)
- Redis offline (no caching)
- OpenRouter API down (LLM fails)
- Multiple failures simultaneously

Focus:
- System continues without crashing
- Fallback mechanisms work correctly
- Appropriate error logging
- State remains valid after failures

Author: Claude Code
Date: Week 7 Day 4
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from backend.preprocessing.kg_enrichment_service import KGEnrichmentService
from backend.preprocessing.query_understanding import (
    QueryUnderstandingResult,
    QueryIntentType
)
from backend.orchestration.langgraph_workflow import preprocessing_node


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_query():
    return "Quali sono gli obblighi del GDPR per le PMI?"


@pytest.fixture
def sample_state(sample_query):
    return {
        "trace_id": "DEGRADE-001",
        "session_id": "degrade_session",
        "original_query": sample_query,
        "query_context": {
            "query": sample_query,
            "intent": "unknown",
            "complexity": 0.5
        },
        "enriched_context": {},
        "execution_plan": None,
        "agent_results": {},
        "expert_context": None,
        "expert_opinions": [],
        "provisional_answer": None,
        "iteration_context": None,
        "current_iteration": 1,
        "should_continue": True,
        "stop_reason": None,
        "refinement_instructions": None,
        "execution_time_ms": 0.0,
        "tokens_used": 0,
        "errors": []
    }


@pytest.fixture
def sample_qu_result(sample_query):
    return QueryUnderstandingResult(
        query_id="DEGRADE-QU-001",
        original_query=sample_query,
        intent=QueryIntentType.COMPLIANCE_CHECK,
        intent_confidence=0.91,
        intent_reasoning="GDPR compliance question",
        entities=[],
        norm_references=["gdpr_art_5", "gdpr_art_32"],
        legal_concepts=["data protection", "security measures"],
        dates=[],
        language="it",
        query_length=len(sample_query),
        processing_time_ms=120.0,
        model_version="test",
        timestamp=datetime.utcnow(),
        overall_confidence=0.87,
        needs_review=False
    )


# ============================================================================
# Test 1: Neo4j Offline - KG Enrichment Graceful Degradation
# ============================================================================

@pytest.mark.asyncio
async def test_kg_enrichment_neo4j_offline(sample_qu_result):
    """Test KG enrichment returns empty context when Neo4j is offline."""

    # Initialize with no Neo4j driver
    kg_service = KGEnrichmentService(
        neo4j_driver=None,  # Simulate offline
        redis_client=None,
        config=None
    )

    # Should not raise exception
    enriched = await kg_service.enrich_context(sample_qu_result)

    # Assertions
    assert enriched is not None
    assert enriched.query_understanding == sample_qu_result
    assert len(enriched.norms) == 0
    assert len(enriched.sentenze) == 0
    assert len(enriched.dottrina) == 0
    assert enriched.enrichment_metadata["degraded_mode"] is True
    assert enriched.enrichment_metadata["reason"] == "neo4j_unavailable"


@pytest.mark.asyncio
async def test_kg_enrichment_neo4j_connection_error(sample_qu_result):
    """Test KG enrichment handles Neo4j connection errors gracefully."""

    # Mock Neo4j driver that raises connection error
    mock_driver = AsyncMock()
    mock_driver.session.side_effect = Exception("Neo4j connection refused")

    kg_service = KGEnrichmentService(
        neo4j_driver=mock_driver,
        redis_client=None,
        config=None
    )

    # Should handle exception gracefully
    try:
        enriched = await kg_service.enrich_context(sample_qu_result)
        # If it returns without exception, verify it's degraded
        assert enriched.enrichment_metadata.get("degraded_mode", False)
    except Exception as e:
        # If it does raise, verify error handling exists
        pytest.fail(f"KG enrichment should handle Neo4j errors gracefully, but raised: {e}")


# ============================================================================
# Test 2: Redis Offline - Caching Disabled
# ============================================================================

@pytest.mark.asyncio
async def test_kg_enrichment_redis_offline(sample_qu_result):
    """Test KG enrichment works without Redis caching."""

    # Mock Neo4j driver (working)
    mock_driver = AsyncMock()
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    async def mock_records():
        yield {
            "estremi": "gdpr_art_5",
            "titolo": "Principles relating to processing",
            "descrizione": "Test",
            "stato": "vigente",
            "testo_vigente": "Test text",
            "data_entrata_in_vigore": "2018-05-25",
            "has_controversy": False
        }

    mock_result.__aiter__ = mock_records
    mock_session.run.return_value = mock_result
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    # Initialize with no Redis
    kg_service = KGEnrichmentService(
        neo4j_driver=mock_driver,
        redis_client=None,  # No Redis
        config=None
    )

    # Should work without Redis
    enriched = await kg_service.enrich_context(sample_qu_result)

    # Assertions
    assert enriched is not None
    assert len(enriched.norms) > 0
    assert enriched.enrichment_metadata["cache_hit"] is False


@pytest.mark.asyncio
async def test_kg_enrichment_redis_connection_error(sample_qu_result):
    """Test KG enrichment continues when Redis connection fails."""

    # Mock Redis that raises connection error
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection refused")

    # Mock Neo4j (working)
    mock_driver = AsyncMock()
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    async def mock_records():
        return
        yield

    mock_result.__aiter__ = mock_records
    mock_session.run.return_value = mock_result
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    kg_service = KGEnrichmentService(
        neo4j_driver=mock_driver,
        redis_client=mock_redis,
        config=None
    )

    # Should handle Redis error gracefully and continue
    enriched = await kg_service.enrich_context(sample_qu_result)
    assert enriched is not None


# ============================================================================
# Test 3: Query Understanding LLM Failure
# ============================================================================

@pytest.mark.asyncio
async def test_query_understanding_llm_fallback(sample_query):
    """Test query understanding falls back to heuristic when LLM fails."""

    from backend.preprocessing import query_understanding

    # Mock OpenRouter to fail
    with patch('backend.preprocessing.query_understanding.openrouter_service') as mock_openrouter:
        mock_openrouter.complete.side_effect = Exception("OpenRouter API timeout")

        # Should fallback to heuristic
        result = await query_understanding.analyze_query(
            query=sample_query,
            query_id="FALLBACK-001",
            use_llm=True  # Request LLM, but will fallback
        )

        # Should still return valid result
        assert result is not None
        assert result.query_id == "FALLBACK-001"
        assert result.intent in QueryIntentType
        # May have lower confidence
        assert result.intent_confidence >= 0.0


# ============================================================================
# Test 4: Preprocessing Node - Complete Degradation
# ============================================================================

@pytest.mark.asyncio
async def test_preprocessing_node_all_services_offline(sample_state):
    """Test preprocessing node when all external services are offline."""

    # Mock query understanding to fail
    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.side_effect = Exception("Query understanding service unreachable")

        # Mock Neo4j unavailable
        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            result_state = await preprocessing_node(sample_state)

        # Should return state with error but not crash
        assert result_state is not None
        assert len(result_state["errors"]) > 0
        assert "Preprocessing failed" in result_state["errors"][0]

        # Original state preserved
        assert result_state["trace_id"] == sample_state["trace_id"]
        assert result_state["original_query"] == sample_state["original_query"]


@pytest.mark.asyncio
async def test_preprocessing_node_partial_degradation(sample_state, sample_qu_result):
    """Test preprocessing node when only Neo4j is offline (query understanding works)."""

    # Mock query understanding working
    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.return_value = sample_qu_result

        # Mock Neo4j unavailable
        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            result_state = await preprocessing_node(sample_state)

        # Should complete successfully with fallback enriched_context
        assert result_state is not None
        assert len(result_state["errors"]) == 0

        # Query understanding data should be present
        assert result_state["query_context"]["intent"] == "compliance_check"
        assert result_state["query_context"]["intent_confidence"] == 0.91

        # Enriched context should have degradation metadata
        assert "enrichment_metadata" in result_state["enriched_context"]
        assert result_state["enriched_context"]["enrichment_metadata"]["degraded_mode"] is True


# ============================================================================
# Test 5: Error Logging and Monitoring
# ============================================================================

@pytest.mark.asyncio
async def test_degradation_error_logging(sample_state, caplog):
    """Test that degradation scenarios are logged appropriately."""

    import logging
    caplog.set_level(logging.WARNING)

    # Mock Neo4j unavailable
    with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
        with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
            mock_qu.return_value = QueryUnderstandingResult(
                query_id="LOG-001",
                original_query=sample_state["original_query"],
                intent=QueryIntentType.UNKNOWN,
                intent_confidence=0.60,
                intent_reasoning="Low confidence",
                entities=[],
                norm_references=[],
                legal_concepts=[],
                dates=[],
                language="it",
                query_length=50,
                processing_time_ms=100.0,
                model_version="test",
                timestamp=datetime.utcnow(),
                overall_confidence=0.65,
                needs_review=True
            )

            await preprocessing_node(sample_state)

    # Check for degradation warnings
    assert "Neo4j not available" in caplog.text or "degraded" in caplog.text.lower()


# ============================================================================
# Test 6: State Validity After Failures
# ============================================================================

@pytest.mark.asyncio
async def test_state_validity_after_neo4j_failure(sample_state, sample_qu_result):
    """Test that state remains valid and usable after Neo4j failure."""

    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.return_value = sample_qu_result

        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            result_state = await preprocessing_node(sample_state)

        # Verify all required state fields are present
        required_fields = [
            "trace_id", "session_id", "original_query", "query_context",
            "enriched_context", "execution_plan", "agent_results",
            "expert_context", "expert_opinions", "provisional_answer",
            "iteration_context", "current_iteration", "should_continue",
            "stop_reason", "refinement_instructions", "execution_time_ms",
            "tokens_used", "errors"
        ]

        for field in required_fields:
            assert field in result_state, f"Required field '{field}' missing from state"

        # Verify types
        assert isinstance(result_state["query_context"], dict)
        assert isinstance(result_state["enriched_context"], dict)
        assert isinstance(result_state["errors"], list)


@pytest.mark.asyncio
async def test_downstream_nodes_receive_valid_state_after_degradation(sample_state, sample_qu_result):
    """Test that downstream nodes (router, retrieval) receive valid state even after degradation."""

    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.return_value = sample_qu_result

        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            result_state = await preprocessing_node(sample_state)

        # Simulate router node reading the state
        router_query_context = result_state["query_context"]
        router_enriched_context = result_state["enriched_context"]

        # Router should be able to process this
        assert "intent" in router_query_context
        assert router_query_context["intent"] != "unknown"  # Should have real value
        assert "enrichment_metadata" in router_enriched_context


# ============================================================================
# Test 7: Recovery and Retry Mechanisms
# ============================================================================

@pytest.mark.asyncio
async def test_kg_enrichment_partial_source_failure(sample_qu_result):
    """Test KG enrichment when some sources fail but others succeed."""

    # Mock Neo4j driver where some queries fail
    mock_driver = AsyncMock()
    mock_session = AsyncMock()

    # Mock different results for different queries
    async def mock_run(query, **kwargs):
        mock_result = AsyncMock()
        if "Norma" in query:
            # Norms query succeeds
            async def norm_records():
                yield {
                    "estremi": "test_norm",
                    "titolo": "Test",
                    "descrizione": "Test",
                    "stato": "vigente",
                    "testo_vigente": "Test",
                    "data_entrata_in_vigore": "2020-01-01",
                    "has_controversy": False
                }
            mock_result.__aiter__ = norm_records
        else:
            # Other queries fail
            async def empty_records():
                return
                yield
            mock_result.__aiter__ = empty_records
        return mock_result

    mock_session.run = mock_run
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    kg_service = KGEnrichmentService(
        neo4j_driver=mock_driver,
        redis_client=None,
        config=None
    )

    enriched = await kg_service.enrich_context(sample_qu_result)

    # Should have norms but not sentenze/dottrina
    assert len(enriched.norms) > 0
    assert len(enriched.sentenze) == 0
    assert len(enriched.dottrina) == 0


# ============================================================================
# Summary
# ============================================================================

"""
Graceful Degradation Test Summary
==================================

Coverage:
- Neo4j offline: 2 tests
- Redis offline: 2 tests
- LLM failure: 1 test
- Complete degradation: 1 test
- Partial degradation: 1 test
- Error logging: 1 test
- State validity: 2 tests
- Partial failures: 1 test

Total: 11 test cases

Run with:
    pytest tests/orchestration/test_graceful_degradation.py -v

These tests verify the system's resilience and ability to continue
operating with reduced functionality when external services fail.
"""
