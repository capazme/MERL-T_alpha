"""
Tests for Expert base classes.
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime

from merlt.experts import (
    BaseExpert,
    ExpertWithTools,
    ExpertContext,
    ExpertResponse,
    LegalSource,
    ReasoningStep,
    ConfidenceFactors,
)
from merlt.tools import BaseTool, ToolResult, ToolParameter, ParameterType


class TestExpertContext:
    """Test per ExpertContext."""

    def test_create_simple(self):
        """Crea context semplice."""
        ctx = ExpertContext(query_text="Cos'è la legittima difesa?")

        assert ctx.query_text == "Cos'è la legittima difesa?"
        assert ctx.query_embedding is None
        assert ctx.entities == {}
        assert ctx.retrieved_chunks == []
        assert ctx.trace_id is not None

    def test_create_with_entities(self):
        """Crea context con entità estratte."""
        ctx = ExpertContext(
            query_text="Art. 52 c.p.",
            entities={
                "norm_references": ["urn:norma:cp:art52"],
                "legal_concepts": ["legittima difesa", "scriminante"]
            }
        )

        assert ctx.norm_references == ["urn:norma:cp:art52"]
        assert ctx.legal_concepts == ["legittima difesa", "scriminante"]

    def test_create_with_chunks(self):
        """Crea context con chunks recuperati."""
        chunks = [
            {"chunk_id": "1", "text": "Art. 52 - Difesa legittima..."},
            {"chunk_id": "2", "text": "La scriminante..."}
        ]

        ctx = ExpertContext(
            query_text="test",
            retrieved_chunks=chunks
        )

        assert len(ctx.retrieved_chunks) == 2
        assert ctx.retrieved_chunks[0]["chunk_id"] == "1"


class TestLegalSource:
    """Test per LegalSource."""

    def test_create(self):
        """Crea source."""
        source = LegalSource(
            source_type="norm",
            source_id="urn:norma:cp:art52",
            citation="Art. 52 c.p.",
            excerpt="Non è punibile chi ha commesso il fatto...",
            relevance="Definisce la legittima difesa"
        )

        assert source.source_type == "norm"
        assert source.source_id == "urn:norma:cp:art52"
        assert source.citation == "Art. 52 c.p."

    def test_to_dict(self):
        """Serializza in dizionario."""
        source = LegalSource(
            source_type="jurisprudence",
            source_id="cass:pen:2020:12345",
            citation="Cass. pen. 12345/2020"
        )

        data = source.to_dict()

        assert data["source_type"] == "jurisprudence"
        assert data["source_id"] == "cass:pen:2020:12345"
        assert "citation" in data


class TestReasoningStep:
    """Test per ReasoningStep."""

    def test_create(self):
        """Crea step."""
        step = ReasoningStep(
            step_number=1,
            description="Analisi del testo dell'art. 52 c.p.",
            sources=["urn:norma:cp:art52"]
        )

        assert step.step_number == 1
        assert step.description == "Analisi del testo dell'art. 52 c.p."
        assert step.sources == ["urn:norma:cp:art52"]

    def test_to_dict(self):
        """Serializza in dizionario."""
        step = ReasoningStep(
            step_number=2,
            description="Identificazione dei requisiti"
        )

        data = step.to_dict()

        assert data["step_number"] == 2
        assert data["description"] == "Identificazione dei requisiti"
        assert data["sources"] == []


class TestConfidenceFactors:
    """Test per ConfidenceFactors."""

    def test_create_default(self):
        """Crea con valori default."""
        cf = ConfidenceFactors()

        assert cf.norm_clarity == 0.5
        assert cf.jurisprudence_alignment == 0.5
        assert cf.contextual_ambiguity == 0.5
        assert cf.source_availability == 0.5

    def test_create_custom(self):
        """Crea con valori custom."""
        cf = ConfidenceFactors(
            norm_clarity=0.9,
            jurisprudence_alignment=0.8,
            contextual_ambiguity=0.2,
            source_availability=0.95
        )

        assert cf.norm_clarity == 0.9
        assert cf.contextual_ambiguity == 0.2

    def test_to_dict(self):
        """Serializza in dizionario."""
        cf = ConfidenceFactors(norm_clarity=0.9)

        data = cf.to_dict()

        assert data["norm_clarity"] == 0.9
        assert "jurisprudence_alignment" in data


class TestExpertResponse:
    """Test per ExpertResponse."""

    def test_create_simple(self):
        """Crea response semplice."""
        response = ExpertResponse(
            expert_type="literal",
            interpretation="La legittima difesa è una causa di giustificazione...",
            confidence=0.85
        )

        assert response.expert_type == "literal"
        assert "legittima difesa" in response.interpretation
        assert response.confidence == 0.85
        assert response.timestamp is not None

    def test_create_full(self):
        """Crea response completa."""
        response = ExpertResponse(
            expert_type="literal",
            interpretation="Interpretazione completa...",
            legal_basis=[
                LegalSource(
                    source_type="norm",
                    source_id="urn:norma:cp:art52",
                    citation="Art. 52 c.p."
                )
            ],
            reasoning_steps=[
                ReasoningStep(step_number=1, description="Step 1")
            ],
            confidence=0.9,
            confidence_factors=ConfidenceFactors(norm_clarity=0.95),
            limitations="Analisi limitata al codice penale",
            trace_id="test_trace",
            execution_time_ms=150.5,
            tokens_used=1234
        )

        assert len(response.legal_basis) == 1
        assert len(response.reasoning_steps) == 1
        assert response.confidence_factors.norm_clarity == 0.95
        assert response.trace_id == "test_trace"
        assert response.execution_time_ms == 150.5
        assert response.tokens_used == 1234

    def test_to_dict(self):
        """Serializza in dizionario."""
        response = ExpertResponse(
            expert_type="systemic",
            interpretation="Test interpretation",
            legal_basis=[
                LegalSource(
                    source_type="norm",
                    source_id="test",
                    citation="Test"
                )
            ]
        )

        data = response.to_dict()

        assert data["expert_type"] == "systemic"
        assert data["interpretation"] == "Test interpretation"
        assert len(data["legal_basis"]) == 1
        assert "timestamp" in data


# Mock Tool per test
class MockSearchTool(BaseTool):
    """Tool di test per ricerca."""
    name = "mock_search"
    description = "Tool di test per ricerca semantica"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", ParameterType.STRING, "Query di ricerca"),
            ToolParameter("top_k", ParameterType.INTEGER, "Risultati", required=False, default=5),
        ]

    async def execute(self, query: str, top_k: int = 5) -> ToolResult:
        return ToolResult.ok(
            data={
                "results": [
                    {"chunk_id": "1", "text": f"Risultato per: {query}", "score": 0.9}
                ]
            },
            tool_name=self.name
        )


# Mock Expert per test
class MockExpert(BaseExpert):
    """Expert di test."""
    expert_type = "mock"
    description = "Expert di test"

    async def analyze(self, context: ExpertContext) -> ExpertResponse:
        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=f"Mock analysis for: {context.query_text}",
            confidence=0.8,
            trace_id=context.trace_id
        )


class TestBaseExpert:
    """Test per BaseExpert."""

    def test_init_valid(self):
        """Inizializza expert valido."""
        expert = MockExpert()

        assert expert.expert_type == "mock"
        assert expert.description == "Expert di test"
        assert len(expert.tools) == 0

    def test_init_with_tools(self):
        """Inizializza con tools."""
        tool = MockSearchTool()
        expert = MockExpert(tools=[tool])

        assert len(expert.tools) == 1
        assert "mock_search" in expert._tool_registry

    def test_init_no_type(self):
        """Errore se manca expert_type."""
        class NoTypeExpert(BaseExpert):
            description = "Test"

            async def analyze(self, context):
                pass

        with pytest.raises(ValueError, match="must have an expert_type"):
            NoTypeExpert()

    def test_init_no_description(self):
        """Errore se manca description."""
        class NoDescExpert(BaseExpert):
            expert_type = "test"

            async def analyze(self, context):
                pass

        with pytest.raises(ValueError, match="must have a description"):
            NoDescExpert()

    def test_get_tools_schema(self):
        """Genera schema tools."""
        tool = MockSearchTool()
        expert = MockExpert(tools=[tool])

        schemas = expert.get_tools_schema()

        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock_search"

    def test_repr(self):
        """Rappresentazione stringa."""
        expert = MockExpert()
        assert "MockExpert" in repr(expert)
        assert "mock" in repr(expert)


class TestBaseExpertAsync:
    """Test async per BaseExpert."""

    @pytest.mark.asyncio
    async def test_analyze(self):
        """Esegue analyze."""
        expert = MockExpert()
        context = ExpertContext(query_text="Test query")

        response = await expert.analyze(context)

        assert response.expert_type == "mock"
        assert "Test query" in response.interpretation
        assert response.confidence == 0.8

    @pytest.mark.asyncio
    async def test_use_tool(self):
        """Usa tool registrato."""
        tool = MockSearchTool()
        expert = MockExpert(tools=[tool])

        result = await expert.use_tool("mock_search", query="test")

        assert result.success is True
        assert len(result.data["results"]) == 1

    @pytest.mark.asyncio
    async def test_use_tool_not_found(self):
        """Errore tool non trovato."""
        expert = MockExpert()

        result = await expert.use_tool("non_existent", query="test")

        assert result.success is False
        assert "not found" in result.error


class TestExpertWithTools:
    """Test per ExpertWithTools."""

    def test_create(self):
        """Crea expert con tools."""
        expert = ExpertWithTools(
            expert_type="test",
            description="Test expert",
            tools=[MockSearchTool()]
        )

        assert expert.expert_type == "test"
        assert len(expert.tools) == 1

    @pytest.mark.asyncio
    async def test_analyze_without_ai_service(self):
        """Analyze senza AI service ritorna errore."""
        expert = ExpertWithTools(
            expert_type="test",
            description="Test expert"
        )

        context = ExpertContext(query_text="Test")
        response = await expert.analyze(context)

        assert response.confidence == 0.0
        assert "AI service non configurato" in response.interpretation
