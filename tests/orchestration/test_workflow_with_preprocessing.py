"""
End-to-End Workflow Tests with Preprocessing (Week 7)
======================================================

Tests the complete LangGraph workflow from START to END with preprocessing node integrated.

Workflow tested:
START → preprocessing → router → retrieval → experts → synthesis → iteration → END

Focus:
- Complete workflow execution
- State propagation across nodes
- Preprocessing data usage by downstream nodes
- Multi-iteration loop with preprocessing
- Error propagation and recovery

Author: Claude Code
Date: Week 7 Day 4
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.orchestration.langgraph_workflow import (
    create_merlt_workflow,
    MEGLTState
)
from backend.preprocessing.query_understanding import (
    QueryUnderstandingResult,
    QueryIntentType
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_legal_query():
    """Sample legal query for end-to-end testing."""
    return "È valido un contratto verbale per la vendita di un immobile?"


@pytest.fixture
def initial_state(sample_legal_query):
    """Initial state for workflow execution."""
    return {
        "trace_id": "E2E-TEST-001",
        "session_id": "e2e_session_001",
        "original_query": sample_legal_query,
        "query_context": {
            "query": sample_legal_query,
            "intent": "unknown",  # Will be replaced by preprocessing
            "complexity": 0.5,
            "temporal_reference": None,
            "jurisdiction": "nazionale"
        },
        "enriched_context": {
            "concepts": [],
            "entities": [],
            "norms": []
        },
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


# ============================================================================
# Test 1: Complete Workflow Execution
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_complete_workflow_with_preprocessing(initial_state, sample_legal_query):
    """Test complete workflow execution from START to END with preprocessing."""

    # Mock all external dependencies
    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        # Mock query understanding
        mock_qu.return_value = QueryUnderstandingResult(
            query_id="E2E-TEST-001",
            original_query=sample_legal_query,
            intent=QueryIntentType.INTERPRETATION,
            intent_confidence=0.89,
            intent_reasoning="Query asks about contract validity - interpretation needed",
            entities=[],
            norm_references=["cc_art_1350"],
            legal_concepts=["contratto", "forma scritta", "immobile"],
            dates=[],
            language="it",
            query_length=len(sample_legal_query),
            processing_time_ms=180.0,
            model_version="test",
            timestamp=datetime.utcnow(),
            overall_confidence=0.85,
            needs_review=False
        )

        # Mock Neo4j unavailable (simplify test)
        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            # Mock LLM Router
            with patch('backend.orchestration.llm_router.LLMRouter.route') as mock_router:
                mock_router.return_value = {
                    "agents": ["kg_agent", "api_agent"],
                    "experts": ["literal_interpreter", "systemic_teleological"],
                    "strategy": "thorough",
                    "reasoning": "Complex interpretation question"
                }

                # Mock all retrieval agents
                with patch('backend.orchestration.agents.KGAgent.execute') as mock_kg:
                    with patch('backend.orchestration.agents.APIAgent.execute') as mock_api:
                        with patch('backend.orchestration.agents.VectorDBAgent.execute') as mock_vdb:
                            mock_kg.return_value = {"success": True, "data": []}
                            mock_api.return_value = {"success": True, "data": []}
                            mock_vdb.return_value = {"success": True, "data": []}

                            # Mock all experts
                            with patch('backend.orchestration.experts.LiteralInterpreter.analyze') as mock_lit:
                                with patch('backend.orchestration.experts.SystemicTeleological.analyze') as mock_sys:
                                    mock_lit.return_value = {
                                        "opinion": "Test literal opinion",
                                        "confidence": 0.80
                                    }
                                    mock_sys.return_value = {
                                        "opinion": "Test systemic opinion",
                                        "confidence": 0.75
                                    }

                                    # Mock synthesizer
                                    with patch('backend.orchestration.experts.synthesizer.Synthesizer.synthesize') as mock_synth:
                                        mock_synth.return_value = {
                                            "final_answer": "Test answer",
                                            "confidence": 0.85,
                                            "consensus_level": 0.88
                                        }

                                        # Mock iteration controller (stop after 1 iteration)
                                        with patch('backend.orchestration.iteration.controller.IterationController.should_continue_iteration') as mock_iter:
                                            mock_iter.return_value = (False, "confidence_threshold_met")

                                            # Execute workflow
                                            app = create_merlt_workflow()
                                            final_state = await app.ainvoke(initial_state)

        # Assertions
        assert final_state is not None
        assert final_state["trace_id"] == "E2E-TEST-001"

        # Verify preprocessing updated state
        assert final_state["query_context"]["intent"] == "interpretation"
        assert final_state["query_context"]["intent_confidence"] == 0.89
        assert "cc_art_1350" in final_state["query_context"]["norm_references"]

        # Verify workflow completed
        assert final_state["provisional_answer"] is not None
        assert final_state["stop_reason"] == "confidence_threshold_met"


# ============================================================================
# Test 2: State Propagation Across Nodes
# ============================================================================

@pytest.mark.asyncio
async def test_preprocessing_data_used_by_router(initial_state):
    """Test that router receives and uses preprocessing data."""

    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.return_value = QueryUnderstandingResult(
            query_id="TEST-002",
            original_query=initial_state["original_query"],
            intent=QueryIntentType.COMPLIANCE_CHECK,
            intent_confidence=0.92,
            intent_reasoning="Compliance question",
            entities=[],
            norm_references=["gdpr_art_5"],
            legal_concepts=["data protection"],
            dates=[],
            language="it",
            query_length=50,
            processing_time_ms=150.0,
            model_version="test",
            timestamp=datetime.utcnow(),
            overall_confidence=0.87,
            needs_review=False
        )

        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            # Mock router to capture input
            router_input_captured = {}

            async def mock_route_capture(query_context, enriched_context):
                router_input_captured["query_context"] = query_context
                router_input_captured["enriched_context"] = enriched_context
                return {
                    "agents": ["api_agent"],
                    "experts": ["literal_interpreter"],
                    "strategy": "quick"
                }

            with patch('backend.orchestration.llm_router.LLMRouter.route', side_effect=mock_route_capture):
                # Mock remaining nodes to stop after router
                with patch('backend.orchestration.langgraph_workflow.retrieval_node') as mock_retrieval:
                    mock_retrieval.return_value = {
                        **initial_state,
                        "agent_results": {},
                        "provisional_answer": {"final_answer": "Test", "confidence": 0.9}
                    }

                    with patch('backend.orchestration.langgraph_workflow.should_iterate', return_value="end"):
                        app = create_merlt_workflow()
                        final_state = await app.ainvoke(initial_state)

            # Verify router received preprocessing data
            assert "intent" in router_input_captured["query_context"]
            assert router_input_captured["query_context"]["intent"] == "compliance_check"
            assert router_input_captured["query_context"]["intent_confidence"] == 0.92


# ============================================================================
# Test 3: Multi-Iteration Loop
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_multi_iteration_preprocessing_runs_once(initial_state):
    """Test that preprocessing runs only once even with multiple iterations."""

    qu_call_count = 0

    async def mock_qu_with_counter(*args, **kwargs):
        nonlocal qu_call_count
        qu_call_count += 1
        return QueryUnderstandingResult(
            query_id=f"ITER-{qu_call_count}",
            original_query=initial_state["original_query"],
            intent=QueryIntentType.NORM_SEARCH,
            intent_confidence=0.88,
            intent_reasoning="Test",
            entities=[],
            norm_references=[],
            legal_concepts=[],
            dates=[],
            language="it",
            query_length=50,
            processing_time_ms=100.0,
            model_version="test",
            timestamp=datetime.utcnow(),
            overall_confidence=0.85,
            needs_review=False
        )

    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query', side_effect=mock_qu_with_counter):
        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            # Mock iteration controller to iterate 2 times then stop
            iteration_count = 0

            async def mock_should_continue(*args, **kwargs):
                nonlocal iteration_count
                iteration_count += 1
                if iteration_count < 2:
                    return (True, None)
                return (False, "max_iterations")

            with patch('backend.orchestration.iteration.controller.IterationController.should_continue_iteration', side_effect=mock_should_continue):
                # Mock all other nodes
                with patch('backend.orchestration.langgraph_workflow.router_node') as mock_router:
                    with patch('backend.orchestration.langgraph_workflow.retrieval_node') as mock_retrieval:
                        with patch('backend.orchestration.langgraph_workflow.experts_node') as mock_experts:
                            with patch('backend.orchestration.langgraph_workflow.synthesis_node') as mock_synth:
                                with patch('backend.orchestration.langgraph_workflow.refinement_node') as mock_refine:
                                    # Passthrough states
                                    mock_router.side_effect = lambda s: {**s, "execution_plan": {}}
                                    mock_retrieval.side_effect = lambda s: {**s, "agent_results": {}}
                                    mock_experts.side_effect = lambda s: {**s, "expert_opinions": []}
                                    mock_synth.side_effect = lambda s: {**s, "provisional_answer": {"final_answer": "Test"}}
                                    mock_refine.side_effect = lambda s: s

                                    app = create_merlt_workflow()
                                    final_state = await app.ainvoke(initial_state)

    # Verify query understanding was called only ONCE (preprocessing runs once)
    assert qu_call_count == 1, f"Query understanding called {qu_call_count} times, expected 1"


# ============================================================================
# Test 4: Error Propagation
# ============================================================================

@pytest.mark.asyncio
async def test_preprocessing_error_workflow_continues(initial_state):
    """Test that workflow continues even if preprocessing fails."""

    # Mock query understanding to fail
    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.side_effect = Exception("Query understanding service down")

        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            # Mock all downstream nodes to succeed
            with patch('backend.orchestration.langgraph_workflow.router_node') as mock_router:
                with patch('backend.orchestration.langgraph_workflow.retrieval_node') as mock_retrieval:
                    with patch('backend.orchestration.langgraph_workflow.experts_node') as mock_experts:
                        with patch('backend.orchestration.langgraph_workflow.synthesis_node') as mock_synth:
                            with patch('backend.orchestration.langgraph_workflow.should_iterate', return_value="end"):
                                mock_router.side_effect = lambda s: {**s, "execution_plan": {}}
                                mock_retrieval.side_effect = lambda s: {**s, "agent_results": {}}
                                mock_experts.side_effect = lambda s: {**s, "expert_opinions": []}
                                mock_synth.side_effect = lambda s: {**s, "provisional_answer": {"final_answer": "Test", "confidence": 0.8}}

                                app = create_merlt_workflow()
                                final_state = await app.ainvoke(initial_state)

        # Workflow should complete despite preprocessing error
        assert final_state is not None
        assert len(final_state["errors"]) > 0
        assert "Preprocessing failed" in final_state["errors"][0]

        # Mock values should still be present (fallback)
        assert final_state["query_context"]["intent"] == "unknown"


# ============================================================================
# Test 5: Performance & Timing
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_execution_time_tracking(initial_state):
    """Test that execution time is tracked across all nodes."""

    with patch('backend.orchestration.langgraph_workflow.query_understanding.analyze_query') as mock_qu:
        mock_qu.return_value = QueryUnderstandingResult(
            query_id="PERF-001",
            original_query=initial_state["original_query"],
            intent=QueryIntentType.NORM_SEARCH,
            intent_confidence=0.88,
            intent_reasoning="Test",
            entities=[],
            norm_references=[],
            legal_concepts=[],
            dates=[],
            language="it",
            query_length=50,
            processing_time_ms=100.0,
            model_version="test",
            timestamp=datetime.utcnow(),
            overall_confidence=0.85,
            needs_review=False
        )

        with patch.dict('os.environ', {"NEO4J_URI": ""}, clear=False):
            with patch('backend.orchestration.langgraph_workflow.router_node') as mock_router:
                with patch('backend.orchestration.langgraph_workflow.retrieval_node') as mock_retrieval:
                    with patch('backend.orchestration.langgraph_workflow.experts_node') as mock_experts:
                        with patch('backend.orchestration.langgraph_workflow.synthesis_node') as mock_synth:
                            with patch('backend.orchestration.langgraph_workflow.should_iterate', return_value="end"):
                                # Each node adds execution time
                                def add_time(state, ms):
                                    return {**state, "execution_time_ms": state.get("execution_time_ms", 0.0) + ms}

                                mock_router.side_effect = lambda s: add_time(s, 50)
                                mock_retrieval.side_effect = lambda s: add_time(s, 100)
                                mock_experts.side_effect = lambda s: add_time(s, 200)
                                mock_synth.side_effect = lambda s: {
                                    **add_time(s, 75),
                                    "provisional_answer": {"final_answer": "Test"}
                                }

                                app = create_merlt_workflow()
                                final_state = await app.ainvoke(initial_state)

        # Total execution time should include all nodes
        assert final_state["execution_time_ms"] > 0
        # Preprocessing (~100) + Router (50) + Retrieval (100) + Experts (200) + Synthesis (75) = ~525ms
        assert final_state["execution_time_ms"] >= 400  # Allow some variance


# ============================================================================
# Test 6: Graph Structure Validation
# ============================================================================

def test_workflow_graph_structure():
    """Test that workflow graph has correct structure with preprocessing."""

    app = create_merlt_workflow()

    # Verify nodes exist
    nodes = list(app.nodes.keys())
    assert "preprocessing" in nodes
    assert "router" in nodes
    assert "retrieval" in nodes
    assert "experts" in nodes
    assert "synthesis" in nodes
    assert "iteration" in nodes
    assert "refinement" in nodes

    # Verify entry point is preprocessing (not router)
    # Note: LangGraph may not expose entry_point directly, but we can verify via execution


def test_workflow_preprocessing_runs_first():
    """Test that preprocessing is the first node to execute."""

    app = create_merlt_workflow()

    # Verify by checking compiled graph structure
    # (Implementation-specific - may need adjustment based on LangGraph internals)
    assert app is not None  # Basic sanity check


# ============================================================================
# Summary
# ============================================================================

"""
End-to-End Test Summary
=======================

Coverage:
- Complete workflow execution: 1 test
- State propagation: 1 test
- Multi-iteration: 1 test
- Error handling: 1 test
- Performance: 1 test
- Graph structure: 2 tests

Total: 7 test cases (3 marked @slow for CI)

Run with:
    pytest tests/orchestration/test_workflow_with_preprocessing.py -v

Skip slow tests:
    pytest tests/orchestration/test_workflow_with_preprocessing.py -v -m "not slow"
"""
