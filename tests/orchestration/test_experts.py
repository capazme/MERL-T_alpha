"""
Tests for Reasoning Experts and Synthesizer.

This module tests the 4 expert types (LiteralInterpreter, SystemicTeleological,
PrinciplesBalancer, PrecedentAnalyst) and the Synthesizer component.

Test Coverage:
- Expert initialization and configuration
- ExpertContext creation and validation
- Individual expert analysis (mocked LLM responses)
- ExpertOpinion parsing and validation
- Synthesizer convergent mode
- Synthesizer divergent mode
- Full pipeline integration (4 experts → synthesizer)
- Error handling and edge cases
"""

import pytest
import json
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.orchestration.experts import (
    ReasoningExpert,
    ExpertContext,
    ExpertOpinion,
    LegalBasis,
    ReasoningStep,
    ConfidenceFactors,
    LiteralInterpreter,
    SystemicTeleological,
    PrinciplesBalancer,
    PrecedentAnalyst,
    Synthesizer,
    ProvisionalAnswer,
    ProvenanceClaim
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_expert_context() -> ExpertContext:
    """Sample ExpertContext for testing."""
    return ExpertContext(
        query_text="È valido un contratto verbale per la vendita di un immobile?",
        intent="legal_validity",
        complexity=0.7,
        norm_references=["Art. 1350 c.c.", "Art. 1325 c.c."],
        legal_concepts=["contratto", "forma scritta", "vendita immobiliare"],
        entities={
            "contratto_type": "vendita",
            "oggetto": "immobile",
            "forma": "verbale"
        },
        kg_results=[
            {
                "norm_id": "art_1350_cc",
                "citation": "Art. 1350 c.c.",
                "text": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità: 1) i contratti che trasferiscono la proprietà di beni immobili...",
                "source": "Codice Civile"
            }
        ],
        api_results=[
            {
                "norm_id": "art_1350_cc",
                "full_text": "Art. 1350 - Atti che devono farsi per iscritto...",
                "metadata": {"type": "norm", "source": "normattiva"}
            }
        ],
        vectordb_results=[
            {
                "document_id": "doc_123",
                "text": "La forma scritta ad substantiam è richiesta per i contratti immobiliari...",
                "score": 0.89,
                "metadata": {"type": "dottrina"}
            }
        ],
        enriched_context={
            "rlcf_consensus": 0.92,
            "controversy": False
        },
        trace_id="test-trace-123",
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def mock_literal_interpreter_response() -> Dict[str, Any]:
    """Mock LLM response for LiteralInterpreter."""
    return {
        "interpretation": "L'Art. 1350 c.c. prescrive inequivocabilmente la forma scritta 'sotto pena di nullità' per i contratti che trasferiscono la proprietà di beni immobili. Il contratto verbale non soddisfa questo requisito testuale. Conclusione: il contratto è **nullo** per difetto di forma ai sensi dell'Art. 1350, n. 1 c.c.",

        "legal_basis": [
            {
                "source_type": "norm",
                "source_id": "art_1350_cc",
                "citation": "Art. 1350 c.c.",
                "excerpt": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità: 1) i contratti che trasferiscono la proprietà di beni immobili",
                "relevance": "Requisito di forma scritta ad substantiam",
                "application": "Il contratto verbale non soddisfa il requisito"
            }
        ],

        "reasoning_steps": [
            {
                "step_number": 1,
                "description": "Identificazione norma applicabile: Art. 1350 c.c.",
                "sources": ["art_1350_cc"]
            },
            {
                "step_number": 2,
                "description": "Analisi testuale: 'sotto pena di nullità' è inequivocabile",
                "sources": ["art_1350_cc"]
            },
            {
                "step_number": 3,
                "description": "Applicazione: contratto verbale non soddisfa forma scritta",
                "sources": ["art_1350_cc"]
            },
            {
                "step_number": 4,
                "description": "Conclusione: nullità del contratto",
                "sources": ["art_1350_cc"]
            }
        ],

        "confidence": 0.95,

        "confidence_factors": {
            "norm_clarity": 1.0,
            "jurisprudence_alignment": 0.9,
            "contextual_ambiguity": 0.0,
            "source_availability": 1.0
        },

        "sources": [
            {
                "source_type": "norm",
                "source_id": "art_1350_cc",
                "citation": "Art. 1350 c.c.",
                "excerpt": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità",
                "relevance": "Forma scritta ad substantiam",
                "application": "Contratto verbale non valido"
            }
        ],

        "limitations": "L'interpretazione letterale ignora la ratio legis e il contesto sistematico. Non considera eccezioni giurisprudenziali."
    }


@pytest.fixture
def mock_systemic_response() -> Dict[str, Any]:
    """Mock LLM response for SystemicTeleological expert."""
    return {
        "interpretation": "L'Art. 1350 c.c. richiede forma scritta. La **ratio legis** è garantire certezza giuridica nei trasferimenti immobiliari e facilitare la pubblicità nei registri. Il requisito formale protegge sia le parti che i terzi. Conclusione: **nullo**, perché la forma serve a scopi di ordine pubblico.",

        "legal_basis": [
            {
                "source_type": "norm",
                "source_id": "art_1350_cc",
                "citation": "Art. 1350 c.c.",
                "excerpt": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità: 1) i contratti che trasferiscono la proprietà di beni immobili",
                "relevance": "Ratio: certezza giuridica e pubblicità",
                "application": "Forma scritta è requisito di ordine pubblico"
            }
        ],

        "reasoning_steps": [
            {
                "step_number": 1,
                "description": "Ratio legis: certezza giuridica + pubblicità registri",
                "sources": ["art_1350_cc"]
            },
            {
                "step_number": 2,
                "description": "Interpretazione teleologica: forma serve interessi pubblici",
                "sources": ["art_1350_cc"]
            },
            {
                "step_number": 3,
                "description": "Conclusione: nullità conforme a ratio",
                "sources": ["art_1350_cc"]
            }
        ],

        "confidence": 0.90,

        "confidence_factors": {
            "norm_clarity": 0.9,
            "jurisprudence_alignment": 0.9,
            "contextual_ambiguity": 0.1,
            "source_availability": 0.9
        },

        "sources": [
            {
                "source_type": "norm",
                "source_id": "art_1350_cc",
                "citation": "Art. 1350 c.c.",
                "excerpt": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità",
                "relevance": "Forma ad substantiam per ordine pubblico",
                "application": "Ratio confermata"
            }
        ],

        "limitations": "Ratio legis inferita (non esplicitamente dichiarata nel testo normativo)."
    }


@pytest.fixture
def mock_convergent_synthesis_response() -> Dict[str, Any]:
    """Mock LLM response for convergent synthesis."""
    return {
        "final_answer": "Il contratto verbale per la vendita di un immobile è **nullo** per difetto di forma ai sensi dell'Art. 1350 c.c.\n\n**Base testuale**: L'Art. 1350 c.c. prescrive inequivocabilmente la forma scritta 'sotto pena di nullità'. Il contratto verbale non soddisfa questo requisito.\n\n**Ratio legis**: La forma scritta serve a garantire certezza giuridica nei trasferimenti immobiliari e a facilitare la pubblicità nei registri immobiliari.\n\n**Conclusione**: La nullità è certa (convergenza di tutte le metodologie interpretative).",

        "synthesis_strategy": "Tutti gli esperti concordano sulla nullità del contratto. Ho estratto il consenso combinando: (1) base testuale da literal_interpreter, (2) ratio legis da systemic_teleological, (3) principi costituzionali da principles_balancer, (4) conferma giurisprudenziale da precedent_analyst.",

        "consensus_level": 0.95,

        "confidence": 0.93,

        "confidence_rationale": "Alta confidenza grazie alla convergenza di 4 metodologie indipendenti. Tutti gli esperti hanno confidenza > 0.90 e raggiungono la stessa conclusione.",

        "provenance": [
            {
                "claim_id": "claim_1",
                "claim_text": "Il contratto verbale è nullo per difetto di forma (Art. 1350 c.c.)",
                "sources": [
                    {
                        "type": "norm",
                        "citation": "Art. 1350 c.c.",
                        "excerpt": "Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità",
                        "relevance": "Requisito di forma scritta ad substantiam"
                    }
                ],
                "expert_support": [
                    {
                        "expert": "literal_interpreter",
                        "support_level": "strong",
                        "reasoning": "Testo inequivocabile: 'sotto pena di nullità'"
                    },
                    {
                        "expert": "systemic_teleological",
                        "support_level": "strong",
                        "reasoning": "Ratio legis: certezza giuridica e pubblicità"
                    },
                    {
                        "expert": "principles_balancer",
                        "support_level": "strong",
                        "reasoning": "Forma serve a proteggere ordine pubblico"
                    },
                    {
                        "expert": "precedent_analyst",
                        "support_level": "strong",
                        "reasoning": "Giurisprudenza unanime sulla nullità"
                    }
                ]
            }
        ]
    }


# ============================================================================
# Test: ExpertContext Validation
# ============================================================================

def test_expert_context_creation(sample_expert_context):
    """Test that ExpertContext can be created with all required fields."""
    assert sample_expert_context.query_text == "È valido un contratto verbale per la vendita di un immobile?"
    assert sample_expert_context.intent == "legal_validity"
    assert sample_expert_context.complexity == 0.7
    assert len(sample_expert_context.norm_references) == 2
    assert len(sample_expert_context.kg_results) == 1
    assert sample_expert_context.trace_id == "test-trace-123"


def test_expert_context_validation():
    """Test ExpertContext validation constraints."""
    # Valid context
    context = ExpertContext(
        query_text="Test query",
        intent="test",
        complexity=0.5,
        trace_id="trace-123",
        timestamp=datetime.now().isoformat()
    )
    assert context.complexity == 0.5

    # Invalid complexity (> 1.0)
    with pytest.raises(ValueError):
        ExpertContext(
            query_text="Test",
            intent="test",
            complexity=1.5,  # Invalid
            trace_id="trace-123",
            timestamp=datetime.now().isoformat()
        )


# ============================================================================
# Test: LiteralInterpreter
# ============================================================================

@pytest.mark.asyncio
async def test_literal_interpreter_initialization():
    """Test LiteralInterpreter initialization."""
    expert = LiteralInterpreter()
    assert expert.expert_type == "literal_interpreter"
    assert expert.model == "google/gemini-2.5-flash"
    assert expert.temperature == 0.3
    assert expert.prompt_template is not None


@pytest.mark.asyncio
async def test_literal_interpreter_analyze(
    sample_expert_context,
    mock_literal_interpreter_response
):
    """Test LiteralInterpreter.analyze() with mocked LLM."""
    expert = LiteralInterpreter()

    # Mock the LLM call
    with patch.object(expert, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_literal_interpreter_response

        opinion = await expert.analyze(sample_expert_context)

        # Assertions
        assert opinion.expert_type == "literal_interpreter"
        assert opinion.trace_id == "test-trace-123"
        assert "nullo" in opinion.interpretation.lower()
        assert opinion.confidence == 0.95
        assert len(opinion.legal_basis) >= 1
        assert len(opinion.reasoning_steps) == 4
        assert opinion.confidence_factors.norm_clarity == 1.0


@pytest.mark.asyncio
async def test_literal_interpreter_format_context(sample_expert_context):
    """Test LiteralInterpreter context formatting."""
    expert = LiteralInterpreter()
    formatted = expert._format_context(sample_expert_context)

    assert "È valido un contratto verbale" in formatted
    assert "Art. 1350 c.c." in formatted
    assert "vendita immobiliare" in formatted


# ============================================================================
# Test: SystemicTeleological
# ============================================================================

@pytest.mark.asyncio
async def test_systemic_teleological_initialization():
    """Test SystemicTeleological initialization."""
    expert = SystemicTeleological()
    assert expert.expert_type == "systemic_teleological"
    assert expert.model == "google/gemini-2.5-flash"
    assert expert.prompt_template is not None


@pytest.mark.asyncio
async def test_systemic_teleological_analyze(
    sample_expert_context,
    mock_systemic_response
):
    """Test SystemicTeleological.analyze() with mocked LLM."""
    expert = SystemicTeleological()

    with patch.object(expert, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_systemic_response

        opinion = await expert.analyze(sample_expert_context)

        assert opinion.expert_type == "systemic_teleological"
        assert "ratio legis" in opinion.interpretation.lower()
        assert opinion.confidence == 0.90
        assert len(opinion.reasoning_steps) >= 3


# ============================================================================
# Test: PrinciplesBalancer
# ============================================================================

@pytest.mark.asyncio
async def test_principles_balancer_initialization():
    """Test PrinciplesBalancer initialization."""
    expert = PrinciplesBalancer()
    assert expert.expert_type == "principles_balancer"
    assert expert.model == "google/gemini-2.5-flash"


@pytest.mark.asyncio
async def test_principles_balancer_with_custom_config():
    """Test PrinciplesBalancer with custom configuration."""
    config = {
        "model": "anthropic/claude-3-opus",
        "temperature": 0.5
    }
    expert = PrinciplesBalancer(config=config)
    assert expert.model == "anthropic/claude-3-opus"
    assert expert.temperature == 0.5


# ============================================================================
# Test: PrecedentAnalyst
# ============================================================================

@pytest.mark.asyncio
async def test_precedent_analyst_initialization():
    """Test PrecedentAnalyst initialization."""
    expert = PrecedentAnalyst()
    assert expert.expert_type == "precedent_analyst"
    assert expert.model == "google/gemini-2.5-flash"


# ============================================================================
# Test: Synthesizer - Convergent Mode
# ============================================================================

@pytest.mark.asyncio
async def test_synthesizer_initialization():
    """Test Synthesizer initialization."""
    synthesizer = Synthesizer()
    assert synthesizer.model == "google/gemini-2.5-flash"
    assert synthesizer.temperature == 0.2
    assert synthesizer.convergent_prompt is not None
    assert synthesizer.divergent_prompt is not None


@pytest.mark.asyncio
async def test_synthesizer_convergent_mode(
    sample_expert_context,
    mock_literal_interpreter_response,
    mock_systemic_response,
    mock_convergent_synthesis_response
):
    """Test Synthesizer in convergent mode (experts agree)."""
    # Create mock expert opinions
    opinion1 = ExpertOpinion(
        expert_type="literal_interpreter",
        trace_id="test-trace-123",
        interpretation=mock_literal_interpreter_response["interpretation"],
        legal_basis=[LegalBasis(**lb) for lb in mock_literal_interpreter_response["legal_basis"]],
        reasoning_steps=[ReasoningStep(**rs) for rs in mock_literal_interpreter_response["reasoning_steps"]],
        confidence=0.95,
        confidence_factors=ConfidenceFactors(**mock_literal_interpreter_response["confidence_factors"]),
        sources=[LegalBasis(**s) for s in mock_literal_interpreter_response["sources"]],
        limitations=mock_literal_interpreter_response["limitations"],
        llm_model="google/gemini-2.5-flash",
        temperature=0.3,
        tokens_used=500,
        execution_time_ms=1200.0
    )

    opinion2 = ExpertOpinion(
        expert_type="systemic_teleological",
        trace_id="test-trace-123",
        interpretation=mock_systemic_response["interpretation"],
        legal_basis=[LegalBasis(**lb) for lb in mock_systemic_response["legal_basis"]],
        reasoning_steps=[ReasoningStep(**rs) for rs in mock_systemic_response["reasoning_steps"]],
        confidence=0.90,
        confidence_factors=ConfidenceFactors(**mock_systemic_response["confidence_factors"]),
        sources=[LegalBasis(**s) for s in mock_systemic_response["sources"]],
        limitations=mock_systemic_response["limitations"],
        llm_model="google/gemini-2.5-flash",
        temperature=0.3,
        tokens_used=450,
        execution_time_ms=1100.0
    )

    synthesizer = Synthesizer()

    with patch.object(synthesizer, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_convergent_synthesis_response

        result = await synthesizer.synthesize(
            expert_opinions=[opinion1, opinion2],
            synthesis_mode="convergent",
            query_text=sample_expert_context.query_text,
            trace_id="test-trace-123"
        )

        # Assertions
        assert isinstance(result, ProvisionalAnswer)
        assert result.synthesis_mode == "convergent"
        assert result.consensus_level == 0.95
        assert result.confidence == 0.93
        assert "nullo" in result.final_answer.lower()
        assert len(result.experts_consulted) == 2
        assert "literal_interpreter" in result.experts_consulted
        assert "systemic_teleological" in result.experts_consulted
        assert len(result.provenance) >= 1


# ============================================================================
# Test: Synthesizer - Divergent Mode
# ============================================================================

@pytest.mark.asyncio
async def test_synthesizer_divergent_mode():
    """Test Synthesizer in divergent mode (experts disagree)."""
    # Create two conflicting opinions
    opinion1 = ExpertOpinion(
        expert_type="literal_interpreter",
        trace_id="test-trace-456",
        interpretation="Interpretazione letterale: il contratto è **nullo**.",
        legal_basis=[],
        reasoning_steps=[],
        confidence=0.80,
        confidence_factors=ConfidenceFactors(
            norm_clarity=0.8,
            jurisprudence_alignment=0.7,
            contextual_ambiguity=0.2,
            source_availability=0.9
        ),
        sources=[],
        limitations="",
        llm_model="google/gemini-2.5-flash",
        temperature=0.3,
        tokens_used=400,
        execution_time_ms=1000.0
    )

    opinion2 = ExpertOpinion(
        expert_type="systemic_teleological",
        trace_id="test-trace-456",
        interpretation="Interpretazione teleologica: il contratto è **valido** se la ratio è soddisfatta.",
        legal_basis=[],
        reasoning_steps=[],
        confidence=0.75,
        confidence_factors=ConfidenceFactors(
            norm_clarity=0.6,
            jurisprudence_alignment=0.7,
            contextual_ambiguity=0.3,
            source_availability=0.8
        ),
        sources=[],
        limitations="",
        llm_model="google/gemini-2.5-flash",
        temperature=0.3,
        tokens_used=420,
        execution_time_ms=1050.0
    )

    mock_divergent_response = {
        "final_answer": "La questione è **giuridicamente incerta**. Due prospettive:\n\n**Prospettiva letterale**: Contratto nullo per difetto di forma.\n\n**Prospettiva teleologica**: Contratto valido se ratio è soddisfatta.",
        "synthesis_strategy": "Gli esperti divergono sulla conclusione. Ho preservato entrambe le prospettive.",
        "consensus_level": 0.20,
        "confidence": 0.50,
        "confidence_rationale": "Bassa confidenza per divergenza tra esperti.",
        "provenance": [
            {
                "claim_id": "perspective_1",
                "claim_text": "Contratto nullo",
                "sources": [],
                "expert_support": [
                    {
                        "expert": "literal_interpreter",
                        "support_level": "strong",
                        "reasoning": "Lettura testuale"
                    }
                ]
            }
        ]
    }

    synthesizer = Synthesizer()

    with patch.object(synthesizer, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_divergent_response

        result = await synthesizer.synthesize(
            expert_opinions=[opinion1, opinion2],
            synthesis_mode="divergent",
            query_text="Query divergente",
            trace_id="test-trace-456"
        )

        # Assertions
        assert result.synthesis_mode == "divergent"
        assert result.consensus_level < 0.5
        assert result.confidence < 0.7
        assert "incerta" in result.final_answer.lower() or "prospettiva" in result.final_answer.lower()


# ============================================================================
# Test: Full Expert Pipeline Integration
# ============================================================================

@pytest.mark.asyncio
async def test_full_expert_pipeline_integration(
    sample_expert_context,
    mock_literal_interpreter_response,
    mock_systemic_response,
    mock_convergent_synthesis_response
):
    """
    Integration test: 4 experts analyze → synthesizer combines.

    Workflow:
    1. Create 4 expert instances
    2. Each expert analyzes the context (mocked LLM)
    3. Synthesizer combines opinions (mocked LLM)
    4. Validate final ProvisionalAnswer
    """
    # Initialize experts
    experts = [
        LiteralInterpreter(),
        SystemicTeleological(),
        PrinciplesBalancer(),
        PrecedentAnalyst()
    ]

    # Mock expert responses
    expert_responses = [
        mock_literal_interpreter_response,
        mock_systemic_response,
        mock_systemic_response,  # Reuse for principles_balancer
        mock_systemic_response   # Reuse for precedent_analyst
    ]

    opinions = []

    # Run all experts in parallel (mocked)
    for expert, response in zip(experts, expert_responses):
        with patch.object(expert, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = response
            opinion = await expert.analyze(sample_expert_context)
            opinions.append(opinion)

    # Validate we have 4 opinions
    assert len(opinions) == 4
    assert opinions[0].expert_type == "literal_interpreter"
    assert opinions[1].expert_type == "systemic_teleological"
    assert opinions[2].expert_type == "principles_balancer"
    assert opinions[3].expert_type == "precedent_analyst"

    # Synthesize opinions
    synthesizer = Synthesizer()

    with patch.object(synthesizer, '_call_llm', new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = mock_convergent_synthesis_response

        final_answer = await synthesizer.synthesize(
            expert_opinions=opinions,
            synthesis_mode="convergent",
            query_text=sample_expert_context.query_text,
            trace_id=sample_expert_context.trace_id
        )

        # Validate final answer
        assert isinstance(final_answer, ProvisionalAnswer)
        assert final_answer.synthesis_mode == "convergent"
        assert final_answer.consensus_level >= 0.9
        assert final_answer.confidence >= 0.9
        assert len(final_answer.experts_consulted) == 4
        assert "literal_interpreter" in final_answer.experts_consulted
        assert "nullo" in final_answer.final_answer.lower()


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_expert_llm_error_handling(sample_expert_context):
    """Test expert behavior when LLM call fails."""
    expert = LiteralInterpreter()

    with patch.object(expert, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("LLM API error")

        with pytest.raises(Exception) as exc_info:
            await expert.analyze(sample_expert_context)

        assert "LLM API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_synthesizer_empty_opinions():
    """Test Synthesizer with empty opinion list."""
    synthesizer = Synthesizer()

    # Should raise validation error or handle gracefully
    with pytest.raises(Exception):
        await synthesizer.synthesize(
            expert_opinions=[],
            synthesis_mode="convergent",
            query_text="Test query",
            trace_id="test-trace"
        )


# ============================================================================
# Test: Confidence Calculation
# ============================================================================

def test_confidence_factors_validation():
    """Test ConfidenceFactors validation."""
    # Valid
    cf = ConfidenceFactors(
        norm_clarity=0.8,
        jurisprudence_alignment=0.7,
        contextual_ambiguity=0.2,
        source_availability=0.9
    )
    assert cf.norm_clarity == 0.8

    # Invalid (> 1.0)
    with pytest.raises(ValueError):
        ConfidenceFactors(
            norm_clarity=1.5,  # Invalid
            jurisprudence_alignment=0.7,
            contextual_ambiguity=0.2,
            source_availability=0.9
        )


# ============================================================================
# Test: ProvisionalAnswer Validation
# ============================================================================

def test_provisional_answer_creation():
    """Test ProvisionalAnswer creation and validation."""
    answer = ProvisionalAnswer(
        trace_id="test-trace",
        final_answer="Il contratto è nullo.",
        synthesis_mode="convergent",
        synthesis_strategy="Estratto consenso da 4 esperti.",
        experts_consulted=["literal_interpreter", "systemic_teleological"],
        consensus_level=0.95,
        confidence=0.93,
        confidence_rationale="Alta convergenza.",
        provenance=[
            ProvenanceClaim(
                claim_id="claim_1",
                claim_text="Contratto nullo",
                sources=[],
                expert_support=[]
            )
        ],
        llm_model="google/gemini-2.5-flash",
        tokens_used=800,
        execution_time_ms=2500.0
    )

    assert answer.synthesis_mode == "convergent"
    assert answer.consensus_level == 0.95
    assert len(answer.experts_consulted) == 2


# ============================================================================
# Test: Prompt Template Loading
# ============================================================================

def test_expert_prompt_template_loading():
    """Test that experts load prompt templates correctly."""
    expert = LiteralInterpreter()
    assert expert.prompt_template is not None
    assert len(expert.prompt_template) > 100
    assert "LITERAL INTERPRETER" in expert.prompt_template.upper()


def test_synthesizer_prompt_loading():
    """Test that Synthesizer loads both prompt templates."""
    synthesizer = Synthesizer()
    assert synthesizer.convergent_prompt is not None
    assert synthesizer.divergent_prompt is not None
    assert "CONVERGENT" in synthesizer.convergent_prompt.upper()
    assert "DIVERGENT" in synthesizer.divergent_prompt.upper()


# ============================================================================
# Test: ExpertOpinion Serialization
# ============================================================================

def test_expert_opinion_serialization(mock_literal_interpreter_response):
    """Test that ExpertOpinion can be serialized to/from JSON."""
    opinion = ExpertOpinion(
        expert_type="literal_interpreter",
        trace_id="test-trace",
        interpretation="Test interpretation",
        legal_basis=[],
        reasoning_steps=[],
        confidence=0.85,
        confidence_factors=ConfidenceFactors(
            norm_clarity=0.9,
            jurisprudence_alignment=0.8,
            contextual_ambiguity=0.1,
            source_availability=0.95
        ),
        sources=[],
        limitations="Test limitations",
        llm_model="google/gemini-2.5-flash",
        temperature=0.3,
        tokens_used=500,
        execution_time_ms=1200.0
    )

    # Serialize to JSON
    json_data = opinion.model_dump_json()
    assert isinstance(json_data, str)

    # Deserialize from JSON
    parsed = json.loads(json_data)
    reconstructed = ExpertOpinion(**parsed)

    assert reconstructed.expert_type == "literal_interpreter"
    assert reconstructed.confidence == 0.85
    assert reconstructed.trace_id == "test-trace"
