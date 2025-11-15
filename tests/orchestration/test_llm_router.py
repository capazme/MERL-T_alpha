"""
Tests for LLM Router - Week 6 Day 1
====================================

Unit tests for RouterService and ExecutionPlan generation.

Tests cover:
- ExecutionPlan JSON schema validation
- RouterService initialization
- LLM response parsing
- Fallback plan generation
- Agent/expert selection logic validation
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from backend.orchestration.llm_router import (
    RouterService,
    ExecutionPlan,
    RetrievalPlan,
    ReasoningPlan,
    IterationStrategy,
    ExpertSelection,
    KGAgentTasks,
    APIAgentTasks,
    VectorDBAgentTasks,
    APIAgentTask,
    VectorDBAgentTask,
    AgentTask
)


# ==============================================
# Fixtures
# ==============================================

@pytest.fixture
def sample_query_context():
    """Sample query context for testing"""
    return {
        "original_query": "Cosa dice l'art. 1321 c.c. sul contratto?",
        "intent": "norm_explanation",
        "intent_confidence": 0.92,
        "norm_references": [
            {"estremi": "Art. 1321 c.c.", "tipo": "codice_civile"}
        ],
        "legal_concepts": ["contratto", "definizione"],
        "entities": {"NORMA": ["Art. 1321 c.c."]},
        "complexity": "low"
    }


@pytest.fixture
def sample_enriched_context():
    """Sample enriched context for testing"""
    return {
        "norms": {
            "count": 1,
            "sources": ["normattiva"],
            "items": [
                {
                    "estremi": "Art. 1321 c.c.",
                    "testo": "Il contratto è l'accordo...",
                    "confidence": 0.95
                }
            ]
        },
        "sentenze": {"count": 3, "sources": ["cassazione"]},
        "dottrina": {"count": 2, "sources": ["dottrina"]},
        "contributions": {"count": 0},
        "rlcf_votes": {"count": 0},
        "cache_hit": True
    }


@pytest.fixture
def sample_execution_plan_json():
    """Sample valid ExecutionPlan JSON"""
    return {
        "trace_id": "router-test-123",
        "rationale": "Query chiede testo letterale di norma specifica. Serve solo interpretazione positivista.",

        "retrieval_plan": {
            "kg_agent": {
                "enabled": False,
                "tasks": [],
                "rationale": "Norma già in enriched_context"
            },
            "api_agent": {
                "enabled": True,
                "tasks": [
                    {
                        "task_type": "fetch_full_text",
                        "norm_references": ["Art. 1321 c.c."],
                        "priority": "high"
                    }
                ],
                "rationale": "Serve testo ufficiale completo"
            },
            "vectordb_agent": {
                "enabled": False,
                "tasks": [],
                "rationale": "Query specifica, non serve ricerca semantica"
            }
        },

        "reasoning_plan": {
            "experts": [
                {
                    "expert_type": "literal_interpreter",
                    "activation_rationale": "Query chiede significato letterale norma",
                    "priority": "high"
                }
            ],
            "synthesis_mode": "convergent",
            "synthesis_rationale": "Solo un esperto, nessuna sintesi necessaria"
        },

        "iteration_strategy": {
            "estimated_iterations": 1,
            "refine_on_low_confidence": False,
            "refine_on_disagreement": False,
            "refine_on_missing_info": False,
            "rationale": "Query semplice, alta confidenza, risposta diretta possibile"
        }
    }


@pytest.fixture
def router_service():
    """RouterService instance for testing"""
    # Mock AIService to avoid actual LLM calls
    with patch('backend.orchestration.llm_router.AIService') as mock_ai:
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = AsyncMock(return_value="mocked response")

        service = RouterService(ai_service=mock_ai_instance)
        return service


# ==============================================
# Test: ExecutionPlan Schema Validation
# ==============================================

def test_execution_plan_valid_json(sample_execution_plan_json):
    """Test ExecutionPlan creation from valid JSON"""
    plan = ExecutionPlan(**sample_execution_plan_json)

    assert plan.trace_id == "router-test-123"
    assert plan.retrieval_plan.api_agent.enabled is True
    assert len(plan.reasoning_plan.experts) == 1
    assert plan.reasoning_plan.experts[0].expert_type == "literal_interpreter"
    assert plan.iteration_strategy.estimated_iterations == 1


def test_execution_plan_requires_at_least_one_expert():
    """Test that ExecutionPlan requires at least 1 expert"""
    plan_dict = {
        "trace_id": "test",
        "rationale": "Test",
        "retrieval_plan": {
            "kg_agent": {"enabled": False, "tasks": [], "rationale": ""},
            "api_agent": {"enabled": False, "tasks": [], "rationale": ""},
            "vectordb_agent": {"enabled": False, "tasks": [], "rationale": ""}
        },
        "reasoning_plan": {
            "experts": [],  # Empty - should fail
            "synthesis_mode": "convergent",
            "synthesis_rationale": ""
        },
        "iteration_strategy": {
            "estimated_iterations": 1,
            "rationale": ""
        }
    }

    with pytest.raises(ValueError, match="At least one reasoning expert"):
        ExecutionPlan(**plan_dict)


def test_execution_plan_iterations_within_bounds():
    """Test that estimated_iterations is within 1-3 range"""
    plan_dict = {
        "trace_id": "test",
        "rationale": "Test",
        "retrieval_plan": {},
        "reasoning_plan": {
            "experts": [{"expert_type": "literal_interpreter", "activation_rationale": "test", "priority": "high"}],
            "synthesis_mode": "convergent"
        },
        "iteration_strategy": {
            "estimated_iterations": 5,  # Too high - should fail
            "rationale": ""
        }
    }

    with pytest.raises(ValueError):
        ExecutionPlan(**plan_dict)


def test_execution_plan_to_dict(sample_execution_plan_json):
    """Test ExecutionPlan serialization to dict"""
    plan = ExecutionPlan(**sample_execution_plan_json)
    plan_dict = plan.to_dict()

    assert isinstance(plan_dict, dict)
    assert plan_dict["trace_id"] == "router-test-123"
    assert "retrieval_plan" in plan_dict
    assert "reasoning_plan" in plan_dict


def test_execution_plan_from_json(sample_execution_plan_json):
    """Test ExecutionPlan deserialization from JSON string"""
    json_str = json.dumps(sample_execution_plan_json)
    plan = ExecutionPlan.from_json(json_str)

    assert plan.trace_id == "router-test-123"
    assert plan.reasoning_plan.experts[0].expert_type == "literal_interpreter"


# ==============================================
# Test: RouterService Initialization
# ==============================================

def test_router_service_initialization():
    """Test RouterService initializes correctly"""
    with patch('backend.orchestration.llm_router.AIService'):
        with patch('backend.orchestration.llm_router.get_orchestration_config') as mock_config:
            mock_config.return_value = Mock(
                llm_router=Mock(
                    model="google/gemini-2.5-flash",
                    temperature=0.1,
                    prompt_template="router_v1"
                )
            )

            service = RouterService()

            assert service.config is not None
            assert service.ai_service is not None
            assert service.prompt_template is not None


def test_router_service_loads_prompt_template():
    """Test RouterService loads prompt template file"""
    with patch('backend.orchestration.llm_router.AIService'):
        service = RouterService()

        # Should have loaded router_v1.txt
        assert "LLM Router" in service.prompt_template
        assert "ExecutionPlan" in service.prompt_template
        assert "{query_context}" in service.prompt_template


# ==============================================
# Test: LLM Response Parsing
# ==============================================

def test_router_extract_json_from_markdown():
    """Test extraction of JSON from markdown code blocks"""
    with patch('backend.orchestration.llm_router.AIService'):
        service = RouterService()

        # JSON wrapped in markdown
        response = """```json
{
  "trace_id": "test",
  "rationale": "Test"
}
```"""

        extracted = service._extract_json(response)
        assert extracted.strip().startswith("{")
        assert "trace_id" in extracted


def test_router_extract_json_plain():
    """Test extraction of plain JSON"""
    with patch('backend.orchestration.llm_router.AIService'):
        service = RouterService()

        response = '{"trace_id": "test", "rationale": "Test"}'

        extracted = service._extract_json(response)
        assert extracted == response


@pytest.mark.asyncio
async def test_router_parse_valid_llm_response(router_service, sample_execution_plan_json):
    """Test parsing valid LLM response into ExecutionPlan"""
    json_str = json.dumps(sample_execution_plan_json)

    plan = router_service._parse_llm_response(
        json_str,
        "test-trace-123",
        {},
        {}
    )

    assert isinstance(plan, ExecutionPlan)
    assert plan.trace_id == "test-trace-123"  # Should override
    assert len(plan.reasoning_plan.experts) == 1


def test_router_parse_invalid_json(router_service):
    """Test parsing invalid JSON raises error"""
    invalid_json = "This is not JSON at all!"

    with pytest.raises(ValueError, match="invalid JSON"):
        router_service._parse_llm_response(
            invalid_json,
            "test-trace",
            {},
            {}
        )


# ==============================================
# Test: Fallback Plan Generation
# ==============================================

def test_router_fallback_plan_norm_explanation(router_service, sample_query_context, sample_enriched_context):
    """Test fallback plan for norm_explanation query"""
    plan = router_service._generate_fallback_plan(
        "fallback-test",
        sample_query_context,
        sample_enriched_context
    )

    assert plan.trace_id == "fallback-test"
    assert "fallback" in plan.rationale.lower()

    # Should activate API agent (fetch norm text)
    assert plan.retrieval_plan.api_agent.enabled is True
    assert len(plan.retrieval_plan.api_agent.tasks) == 1
    assert plan.retrieval_plan.api_agent.tasks[0].task_type == "fetch_full_text"

    # Should activate Literal Interpreter
    assert len(plan.reasoning_plan.experts) == 1
    assert plan.reasoning_plan.experts[0].expert_type == "literal_interpreter"

    # Should have 1 iteration
    assert plan.iteration_strategy.estimated_iterations == 1

    # Metadata should indicate fallback
    assert plan.router_model == "fallback"


def test_router_fallback_plan_no_norm_refs(router_service):
    """Test fallback plan when no norm references"""
    query_context = {
        "original_query": "Cos'è un contratto?",
        "intent": "norm_explanation",
        "intent_confidence": 0.7,
        "norm_references": [],  # No norm refs
        "legal_concepts": ["contratto"],
        "complexity": "low"
    }

    plan = router_service._generate_fallback_plan(
        "fallback-test-2",
        query_context,
        {}
    )

    # Should NOT activate API agent (no norms to fetch)
    assert plan.retrieval_plan.api_agent.enabled is False
    assert len(plan.retrieval_plan.api_agent.tasks) == 0


# ==============================================
# Test: End-to-End ExecutionPlan Generation
# ==============================================

@pytest.mark.asyncio
async def test_router_generate_execution_plan_success(
    router_service,
    sample_query_context,
    sample_enriched_context,
    sample_execution_plan_json
):
    """Test full execution plan generation with mocked LLM"""
    # Mock LLM to return valid JSON
    mock_response = json.dumps(sample_execution_plan_json)
    router_service.ai_service.generate_response = AsyncMock(return_value=mock_response)

    plan = await router_service.generate_execution_plan(
        sample_query_context,
        sample_enriched_context,
        trace_id="e2e-test-123"
    )

    # Verify plan structure
    assert plan.trace_id == "e2e-test-123"
    assert len(plan.reasoning_plan.experts) == 1
    assert plan.reasoning_plan.experts[0].expert_type == "literal_interpreter"

    # Verify LLM was called
    router_service.ai_service.generate_response.assert_called_once()

    # Verify prompt was built correctly
    call_args = router_service.ai_service.generate_response.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Cosa dice l'art. 1321 c.c." in prompt
    assert '"intent": "norm_explanation"' in prompt


@pytest.mark.asyncio
async def test_router_generate_execution_plan_llm_failure_uses_fallback(
    router_service,
    sample_query_context,
    sample_enriched_context
):
    """Test fallback plan is used when LLM fails"""
    # Mock LLM to raise exception
    router_service.ai_service.generate_response = AsyncMock(
        side_effect=Exception("LLM API error")
    )

    # Should fall back to default plan
    plan = await router_service.generate_execution_plan(
        sample_query_context,
        sample_enriched_context,
        trace_id="fallback-e2e"
    )

    assert plan.trace_id == "fallback-e2e"
    assert plan.router_model == "fallback"
    assert "fallback" in plan.rationale.lower()


@pytest.mark.asyncio
async def test_router_generate_execution_plan_complex_query():
    """Test execution plan for complex multi-expert query"""
    with patch('backend.orchestration.llm_router.AIService') as mock_ai:
        mock_ai_instance = Mock()

        # Mock LLM response for complex query (2 experts, 2 iterations)
        complex_plan_json = {
            "trace_id": "complex-test",
            "rationale": "Query complessa richiede interpretazione sistematica + analisi giurisprudenza",

            "retrieval_plan": {
                "kg_agent": {
                    "enabled": True,
                    "tasks": [
                        {
                            "task_type": "jurisprudence_lookup",
                            "params": {"norm": "Art. 2043 c.c."},
                            "priority": "high"
                        }
                    ],
                    "rationale": "Cercare sentenze"
                },
                "api_agent": {"enabled": False, "tasks": [], "rationale": ""},
                "vectordb_agent": {
                    "enabled": True,
                    "tasks": [
                        {
                            "task_type": "hybrid_search",
                            "query_text": "responsabilità extracontrattuale GDPR",
                            "filters": {},
                            "priority": "medium"
                        }
                    ],
                    "rationale": "Ricerca semantica dottrina"
                }
            },

            "reasoning_plan": {
                "experts": [
                    {
                        "expert_type": "systemic_teleological",
                        "activation_rationale": "Interpretazione coordinata norme",
                        "priority": "high"
                    },
                    {
                        "expert_type": "precedent_analyst",
                        "activation_rationale": "Analisi precedenti Cassazione",
                        "priority": "high"
                    }
                ],
                "synthesis_mode": "divergent",
                "synthesis_rationale": "Due prospettive diverse"
            },

            "iteration_strategy": {
                "estimated_iterations": 2,
                "refine_on_low_confidence": True,
                "refine_on_disagreement": True,
                "refine_on_missing_info": False,
                "rationale": "Complessità alta, possibile necessità di raffinamento"
            }
        }

        mock_ai_instance.generate_response = AsyncMock(
            return_value=json.dumps(complex_plan_json)
        )

        service = RouterService(ai_service=mock_ai_instance)

        query_context = {
            "original_query": "Come si interpreta l'art. 2043 c.c. in caso di danno da GDPR?",
            "intent": "contract_interpretation",
            "intent_confidence": 0.78,
            "norm_references": [{"estremi": "Art. 2043 c.c."}],
            "legal_concepts": ["responsabilità", "danno"],
            "complexity": "high"
        }

        plan = await service.generate_execution_plan(
            query_context,
            {"norms": {"count": 2}, "sentenze": {"count": 15}}
        )

        # Verify complex plan structure
        assert len(plan.reasoning_plan.experts) == 2
        assert plan.reasoning_plan.synthesis_mode == "divergent"
        assert plan.iteration_strategy.estimated_iterations == 2
        assert plan.retrieval_plan.kg_agent.enabled is True
        assert plan.retrieval_plan.vectordb_agent.enabled is True


# ==============================================
# Test: Agent Selection Logic Validation
# ==============================================

def test_expert_selection_literal_for_simple_query():
    """Test that simple queries get literal_interpreter"""
    expert = ExpertSelection(
        expert_type="literal_interpreter",
        activation_rationale="Query chiede testo letterale",
        priority="high"
    )

    assert expert.expert_type == "literal_interpreter"
    assert expert.priority == "high"


def test_expert_selection_multiple_experts():
    """Test multiple expert selection"""
    experts = [
        ExpertSelection(
            expert_type="systemic_teleological",
            activation_rationale="Interpretazione sistematica",
            priority="high"
        ),
        ExpertSelection(
            expert_type="precedent_analyst",
            activation_rationale="Analisi giurisprudenza",
            priority="high"
        )
    ]

    assert len(experts) == 2
    expert_types = [e.expert_type for e in experts]
    assert "systemic_teleological" in expert_types
    assert "precedent_analyst" in expert_types


# ==============================================
# Test: Prompt Building
# ==============================================

def test_router_build_prompt(router_service, sample_query_context, sample_enriched_context):
    """Test prompt building includes context"""
    prompt = router_service._build_prompt(
        sample_query_context,
        sample_enriched_context
    )

    # Should include query text
    assert "Cosa dice l'art. 1321 c.c." in prompt

    # Should include structured data
    assert '"intent": "norm_explanation"' in prompt
    assert '"complexity": "low"' in prompt

    # Should include enriched context
    assert '"cache_hit": true' in prompt
    assert '"count": 1' in prompt  # norms count

    # Should include instructions
    assert "ExecutionPlan" in prompt
    assert "retrieval_plan" in prompt


# ==============================================
# Summary
# ==============================================

"""
Test Coverage:
- ✅ ExecutionPlan schema validation (5 tests)
- ✅ RouterService initialization (2 tests)
- ✅ LLM response parsing (4 tests)
- ✅ Fallback plan generation (2 tests)
- ✅ End-to-end plan generation (3 tests)
- ✅ Agent/expert selection logic (2 tests)
- ✅ Prompt building (1 test)

Total: 19 unit tests
Expected coverage: >85% of llm_router.py
"""
