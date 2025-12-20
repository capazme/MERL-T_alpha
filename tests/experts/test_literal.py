"""
Tests for LiteralExpert.
"""

import pytest
from typing import List, Dict, Any

from merlt.experts import LiteralExpert, ExpertContext, ExpertResponse
from merlt.tools import BaseTool, ToolResult, ToolParameter, ParameterType


# Mock Tools per test
class MockSemanticSearchTool(BaseTool):
    """Mock per SemanticSearchTool."""
    name = "semantic_search"
    description = "Mock semantic search tool"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", ParameterType.STRING, "Query di ricerca"),
            ToolParameter("top_k", ParameterType.INTEGER, "Risultati", required=False, default=5),
            ToolParameter("expert_type", ParameterType.STRING, "Expert type", required=False),
        ]

    async def execute(self, query: str, top_k: int = 5, expert_type: str = None) -> ToolResult:
        return ToolResult.ok(
            data={
                "results": [
                    {
                        "chunk_id": "chunk_1",
                        "text": "Art. 52 c.p. - Difesa legittima. Non è punibile chi ha commesso il fatto per esservi stato costretto dalla necessità di difendere un diritto proprio o altrui...",
                        "urn": "urn:norma:cp:art52",
                        "final_score": 0.95,
                        "similarity_score": 0.92,
                        "graph_score": 0.98
                    },
                    {
                        "chunk_id": "chunk_2",
                        "text": "Nei casi previsti dall'articolo 614, primo e secondo comma, sussiste il rapporto di proporzione...",
                        "urn": "urn:norma:cp:art52:c2",
                        "final_score": 0.88,
                        "similarity_score": 0.85,
                        "graph_score": 0.91
                    }
                ],
                "total": 2,
                "query": query,
                "expert_type": expert_type
            },
            tool_name=self.name
        )


class MockGraphSearchTool(BaseTool):
    """Mock per GraphSearchTool."""
    name = "graph_search"
    description = "Mock graph search tool"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("start_node", ParameterType.STRING, "Nodo di partenza"),
            ToolParameter("relation_types", ParameterType.ARRAY, "Tipi relazione", required=False),
            ToolParameter("max_hops", ParameterType.INTEGER, "Max hops", required=False, default=2),
        ]

    async def execute(
        self,
        start_node: str,
        relation_types: List[str] = None,
        max_hops: int = 2
    ) -> ToolResult:
        return ToolResult.ok(
            data={
                "start_node": start_node,
                "nodes": [
                    {
                        "urn": "urn:concetto:legittima_difesa",
                        "type": "ConcettoGiuridico",
                        "properties": {
                            "testo": "La legittima difesa è una causa di giustificazione..."
                        }
                    }
                ],
                "edges": [
                    {
                        "type": "definisce",
                        "properties": {}
                    }
                ],
                "total_nodes": 1,
                "total_edges": 1
            },
            tool_name=self.name
        )


class TestLiteralExpert:
    """Test per LiteralExpert."""

    def test_init_default(self):
        """Inizializza con default."""
        expert = LiteralExpert()

        assert expert.expert_type == "literal"
        assert "art. 12" in expert.description.lower()
        assert expert.traversal_weights is not None
        assert expert.traversal_weights["contiene"] == 1.0

    def test_init_with_tools(self):
        """Inizializza con tools."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = LiteralExpert(tools=tools)

        assert len(expert.tools) == 2
        assert "semantic_search" in expert._tool_registry
        assert "graph_search" in expert._tool_registry

    def test_init_custom_traversal_weights(self):
        """Inizializza con pesi custom."""
        custom_weights = {
            "contiene": 0.9,
            "disciplina": 0.8,
            "default": 0.3
        }
        expert = LiteralExpert(config={"traversal_weights": custom_weights})

        assert expert.traversal_weights["contiene"] == 0.9
        assert expert.traversal_weights["disciplina"] == 0.8

    def test_default_traversal_weights(self):
        """Verifica pesi default."""
        expert = LiteralExpert()
        weights = expert.DEFAULT_TRAVERSAL_WEIGHTS

        # Pesi specifici per interpretazione letterale
        assert weights["contiene"] == 1.0  # Struttura articolo
        assert weights["disciplina"] == 0.95  # Norma-concetto
        assert weights["definisce"] == 0.95  # Definizioni legali
        assert weights["rinvia"] == 0.90  # Riferimenti
        assert weights["modifica"] == 0.85  # Versioni
        assert weights["default"] == 0.50  # Fallback

    def test_prompt_template(self):
        """Verifica prompt template."""
        expert = LiteralExpert()

        assert "art. 12" in expert.prompt_template.lower()
        assert "significato proprio delle parole" in expert.prompt_template.lower()
        assert "JSON" in expert.prompt_template

    def test_repr(self):
        """Rappresentazione stringa."""
        expert = LiteralExpert()

        repr_str = repr(expert)
        assert "LiteralExpert" in repr_str
        assert "literal" in repr_str


class TestLiteralExpertAsync:
    """Test async per LiteralExpert."""

    @pytest.mark.asyncio
    async def test_analyze_without_tools(self):
        """Analyze senza tools ritorna response basic."""
        expert = LiteralExpert()
        context = ExpertContext(query_text="Cos'è la legittima difesa?")

        response = await expert.analyze(context)

        assert response.expert_type == "literal"
        assert response.trace_id == context.trace_id
        assert response.execution_time_ms > 0
        # Senza AI service, confidence bassa
        assert response.confidence <= 0.5

    @pytest.mark.asyncio
    async def test_analyze_with_tools(self):
        """Analyze con tools recupera fonti."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = LiteralExpert(tools=tools)

        context = ExpertContext(query_text="Cos'è la legittima difesa?")
        response = await expert.analyze(context)

        assert response.expert_type == "literal"
        # Con tools ma senza AI, dovrebbe avere fonti recuperate
        assert response.trace_id == context.trace_id

    @pytest.mark.asyncio
    async def test_analyze_with_norm_references(self):
        """Analyze espande riferimenti normativi."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = LiteralExpert(tools=tools)

        context = ExpertContext(
            query_text="Art. 52 c.p.",
            entities={
                "norm_references": ["urn:norma:cp:art52"],
                "legal_concepts": ["legittima difesa"]
            }
        )

        response = await expert.analyze(context)

        assert response.expert_type == "literal"
        assert response.trace_id == context.trace_id

    @pytest.mark.asyncio
    async def test_analyze_with_existing_chunks(self):
        """Analyze usa chunks già recuperati."""
        expert = LiteralExpert()

        chunks = [
            {
                "chunk_id": "1",
                "text": "Art. 52 c.p. - Difesa legittima...",
                "urn": "urn:norma:cp:art52",
                "final_score": 0.95
            }
        ]

        context = ExpertContext(
            query_text="Legittima difesa",
            retrieved_chunks=chunks
        )

        response = await expert.analyze(context)

        # Dovrebbe usare chunks esistenti
        assert len(response.legal_basis) > 0 or "52" in response.interpretation

    @pytest.mark.asyncio
    async def test_retrieve_sources_semantic(self):
        """Test _retrieve_sources con semantic search."""
        tools = [MockSemanticSearchTool()]
        expert = LiteralExpert(tools=tools)

        context = ExpertContext(query_text="contratto")
        sources = await expert._retrieve_sources(context)

        assert len(sources) > 0
        assert sources[0]["chunk_id"] == "chunk_1"

    @pytest.mark.asyncio
    async def test_retrieve_sources_graph(self):
        """Test _retrieve_sources con graph search."""
        tools = [MockGraphSearchTool()]
        expert = LiteralExpert(tools=tools)

        context = ExpertContext(
            query_text="test",
            entities={"norm_references": ["urn:norma:cp:art52"]}
        )

        sources = await expert._retrieve_sources(context)

        # Graph search aggiunge nodi
        assert any(s.get("source") == "graph_traversal" for s in sources)

    @pytest.mark.asyncio
    async def test_analyze_without_llm_response(self):
        """Analyze senza LLM produce response strutturata."""
        tools = [MockSemanticSearchTool()]
        expert = LiteralExpert(tools=tools)

        context = ExpertContext(query_text="Art. 52 c.p.")
        response = await expert.analyze(context)

        assert response.expert_type == "literal"
        assert response.confidence == 0.3  # Low confidence without LLM
        assert "AI" in response.limitations or "LLM" in response.limitations


class TestLiteralExpertIntegration:
    """Test di integrazione per LiteralExpert."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test pipeline completo senza AI service."""
        # Setup
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = LiteralExpert(tools=tools)

        # Context con tutto
        context = ExpertContext(
            query_text="Cosa prevede l'art. 52 del codice penale sulla legittima difesa?",
            entities={
                "norm_references": ["urn:norma:cp:art52"],
                "legal_concepts": ["legittima difesa", "scriminante"]
            },
            retrieved_chunks=[
                {
                    "chunk_id": "pre_1",
                    "text": "Chunk pre-recuperato...",
                    "urn": "urn:test:pre",
                    "final_score": 0.8
                }
            ]
        )

        # Execute
        response = await expert.analyze(context)

        # Verify
        assert response.expert_type == "literal"
        assert response.trace_id == context.trace_id
        assert response.execution_time_ms > 0

        # Dovrebbe avere legal_basis dalle fonti recuperate
        # (nota: senza AI service, il parsing è limitato)
        assert isinstance(response.legal_basis, list)
        assert isinstance(response.reasoning_steps, list)

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test gestione errori tool."""
        class FailingTool(BaseTool):
            name = "semantic_search"
            description = "Failing tool"

            @property
            def parameters(self):
                return [ToolParameter("query", ParameterType.STRING, "Query")]

            async def execute(self, **kwargs):
                raise ValueError("Simulated error")

        expert = LiteralExpert(tools=[FailingTool()])
        context = ExpertContext(query_text="test")

        # Non dovrebbe crashare
        response = await expert.analyze(context)

        assert response.expert_type == "literal"
        # Dovrebbe comunque produrre una response
        assert response.trace_id == context.trace_id
