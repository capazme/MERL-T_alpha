"""
Tests for all Expert implementations.

Tests per i 4 Expert basati sui canoni ermeneutici delle Preleggi:
- LiteralExpert: Art. 12, I (significato proprio)
- SystemicExpert: Art. 12, I (connessione) + Art. 14 (storico)
- PrinciplesExpert: Art. 12, II (intenzione legislatore)
- PrecedentExpert: Prassi applicativa
"""

import pytest
from typing import List

from merlt.experts import (
    LiteralExpert,
    SystemicExpert,
    PrinciplesExpert,
    PrecedentExpert,
    ExpertContext,
)
from merlt.tools import BaseTool, ToolResult, ToolParameter, ParameterType


# ============================================================================
# Mock Tools
# ============================================================================

class MockSemanticSearchTool(BaseTool):
    """Mock per SemanticSearchTool."""
    name = "semantic_search"
    description = "Mock semantic search"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", ParameterType.STRING, "Query"),
            ToolParameter("top_k", ParameterType.INTEGER, "Results", required=False, default=5),
            ToolParameter("expert_type", ParameterType.STRING, "Expert", required=False),
        ]

    async def execute(self, query: str, top_k: int = 5, expert_type: str = None) -> ToolResult:
        return ToolResult.ok(
            data={
                "results": [
                    {
                        "chunk_id": "chunk_1",
                        "text": f"Risultato per: {query}",
                        "urn": "urn:norma:test:art1",
                        "final_score": 0.9
                    }
                ],
                "total": 1,
                "expert_type": expert_type
            },
            tool_name=self.name
        )


class MockGraphSearchTool(BaseTool):
    """Mock per GraphSearchTool."""
    name = "graph_search"
    description = "Mock graph search"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("start_node", ParameterType.STRING, "Start"),
            ToolParameter("relation_types", ParameterType.ARRAY, "Relations", required=False),
            ToolParameter("max_hops", ParameterType.INTEGER, "Hops", required=False, default=2),
            ToolParameter("direction", ParameterType.STRING, "Direction", required=False),
        ]

    async def execute(self, start_node: str, **kwargs) -> ToolResult:
        return ToolResult.ok(
            data={
                "nodes": [
                    {
                        "urn": "urn:related:node1",
                        "type": "Norma",
                        "properties": {"testo": "Norma correlata..."}
                    }
                ],
                "edges": [],
                "total_nodes": 1
            },
            tool_name=self.name
        )


# ============================================================================
# SystemicExpert Tests
# ============================================================================

class TestSystemicExpert:
    """Test per SystemicExpert."""

    def test_init_default(self):
        """Inizializza con default."""
        expert = SystemicExpert()

        assert expert.expert_type == "systemic"
        assert "connessione" in expert.description.lower() or "sistematica" in expert.description.lower()
        assert expert.traversal_weights is not None

    def test_init_with_tools(self):
        """Inizializza con tools."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = SystemicExpert(tools=tools)

        assert len(expert.tools) == 2
        assert "semantic_search" in expert._tool_registry

    def test_default_traversal_weights(self):
        """Verifica pesi default sistematici."""
        expert = SystemicExpert()
        weights = expert.DEFAULT_TRAVERSAL_WEIGHTS

        # Pesi specifici per interpretazione sistematica
        assert weights["connesso_a"] == 1.0  # Connessioni sistematiche
        assert weights["modifica"] == 0.95   # Evoluzione storica
        assert weights["abroga"] == 0.90     # Abrogazioni
        assert weights["deroga"] == 0.90     # Deroghe
        assert weights["rinvia"] == 0.85     # Riferimenti
        assert weights["default"] == 0.50

    def test_prompt_template(self):
        """Verifica prompt template sistematico."""
        expert = SystemicExpert()

        assert "connessione" in expert.prompt_template.lower()
        assert "storica" in expert.prompt_template.lower() or "storico" in expert.prompt_template.lower()


class TestSystemicExpertAsync:
    """Test async per SystemicExpert."""

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """Analyze base."""
        expert = SystemicExpert()
        context = ExpertContext(query_text="Test sistematico")

        response = await expert.analyze(context)

        assert response.expert_type == "systemic"
        assert response.trace_id == context.trace_id
        assert response.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_analyze_with_tools(self):
        """Analyze con tools espande relazioni."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]
        expert = SystemicExpert(tools=tools)

        context = ExpertContext(
            query_text="Relazione tra art. 1453 e 1455 c.c.",
            entities={"norm_references": ["urn:norma:cc:art1453"]}
        )

        response = await expert.analyze(context)

        assert response.expert_type == "systemic"
        assert response.trace_id == context.trace_id

    @pytest.mark.asyncio
    async def test_expand_systemic_relations(self):
        """Test espansione relazioni sistematiche."""
        tools = [MockGraphSearchTool()]
        expert = SystemicExpert(tools=tools)

        context = ExpertContext(
            query_text="test",
            entities={"norm_references": ["urn:norma:test:art1"]}
        )

        expanded = await expert._expand_systemic_relations(context, [])

        # Dovrebbe espandere tramite graph_search
        assert isinstance(expanded, list)


# ============================================================================
# PrinciplesExpert Tests
# ============================================================================

class TestPrinciplesExpert:
    """Test per PrinciplesExpert."""

    def test_init_default(self):
        """Inizializza con default."""
        expert = PrinciplesExpert()

        assert expert.expert_type == "principles"
        assert "teleologica" in expert.description.lower() or "principi" in expert.description.lower()

    def test_init_with_tools(self):
        """Inizializza con tools."""
        tools = [MockSemanticSearchTool()]
        expert = PrinciplesExpert(tools=tools)

        assert len(expert.tools) == 1

    def test_default_traversal_weights(self):
        """Verifica pesi default per principi."""
        expert = PrinciplesExpert()
        weights = expert.DEFAULT_TRAVERSAL_WEIGHTS

        # Pesi specifici per principi
        assert weights["attua"] == 1.0           # Attuazione principi
        assert weights["esprime"] == 0.95        # Espressione principi
        assert weights["costituzionale"] == 0.95 # Norme cost.
        assert weights["comunitario"] == 0.90    # Norme EU
        assert weights["principio"] == 0.90      # Principi generali

    def test_prompt_template(self):
        """Verifica prompt template teleologico."""
        expert = PrinciplesExpert()

        assert "ratio" in expert.prompt_template.lower() or "finalità" in expert.prompt_template.lower()
        assert "principi" in expert.prompt_template.lower()


class TestPrinciplesExpertAsync:
    """Test async per PrinciplesExpert."""

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """Analyze base."""
        expert = PrinciplesExpert()
        context = ExpertContext(query_text="Ratio legis dell'art. 2043 c.c.")

        response = await expert.analyze(context)

        assert response.expert_type == "principles"
        assert response.trace_id == context.trace_id

    @pytest.mark.asyncio
    async def test_analyze_with_tools(self):
        """Analyze cerca principi."""
        tools = [MockSemanticSearchTool()]
        expert = PrinciplesExpert(tools=tools)

        context = ExpertContext(
            query_text="Diritti fondamentali nella Costituzione",
            entities={"legal_concepts": ["diritti fondamentali"]}
        )

        response = await expert.analyze(context)

        assert response.expert_type == "principles"

    @pytest.mark.asyncio
    async def test_search_principles(self):
        """Test ricerca principi."""
        tools = [MockSemanticSearchTool()]
        expert = PrinciplesExpert(tools=tools)

        context = ExpertContext(
            query_text="test",
            entities={"legal_concepts": ["buona fede"]}
        )

        principles = await expert._search_principles(context)

        assert isinstance(principles, list)


# ============================================================================
# PrecedentExpert Tests
# ============================================================================

class TestPrecedentExpert:
    """Test per PrecedentExpert."""

    def test_init_default(self):
        """Inizializza con default."""
        expert = PrecedentExpert()

        assert expert.expert_type == "precedent"
        assert "giurisprudenziale" in expert.description.lower() or "prassi" in expert.description.lower()

    def test_init_with_tools(self):
        """Inizializza con tools."""
        tools = [MockSemanticSearchTool()]
        expert = PrecedentExpert(tools=tools)

        assert len(expert.tools) == 1

    def test_default_traversal_weights(self):
        """Verifica pesi default giurisprudenziali."""
        expert = PrecedentExpert()
        weights = expert.DEFAULT_TRAVERSAL_WEIGHTS

        # Pesi specifici per giurisprudenza
        assert weights["interpreta"] == 1.0   # Interpretazione
        assert weights["applica"] == 0.95     # Applicazione
        assert weights["cita"] == 0.90        # Citazioni
        assert weights["conferma"] == 0.85    # Conferme
        assert weights["supera"] == 0.80      # Overruling

    def test_court_hierarchy(self):
        """Verifica gerarchia corti."""
        expert = PrecedentExpert()

        assert expert.COURT_HIERARCHY["corte_costituzionale"] == 1.0
        assert expert.COURT_HIERARCHY["cassazione_su"] == 0.95
        assert expert.COURT_HIERARCHY["cassazione"] == 0.85
        assert expert.COURT_HIERARCHY["cgue"] == 0.90

    def test_prompt_template(self):
        """Verifica prompt template giurisprudenziale."""
        expert = PrecedentExpert()

        assert "giurisprudenziale" in expert.prompt_template.lower()
        assert "massima" in expert.prompt_template.lower() or "precedent" in expert.prompt_template.lower()


class TestPrecedentExpertAsync:
    """Test async per PrecedentExpert."""

    @pytest.mark.asyncio
    async def test_analyze_basic(self):
        """Analyze base."""
        expert = PrecedentExpert()
        context = ExpertContext(query_text="Orientamento della Cassazione sul danno")

        response = await expert.analyze(context)

        assert response.expert_type == "precedent"
        assert response.trace_id == context.trace_id

    @pytest.mark.asyncio
    async def test_analyze_with_tools(self):
        """Analyze cerca giurisprudenza."""
        tools = [MockSemanticSearchTool()]
        expert = PrecedentExpert(tools=tools)

        context = ExpertContext(
            query_text="Cassazione SU su responsabilità",
            entities={"legal_concepts": ["responsabilità contrattuale"]}
        )

        response = await expert.analyze(context)

        assert response.expert_type == "precedent"

    @pytest.mark.asyncio
    async def test_rank_by_authority(self):
        """Test ranking per autorità."""
        expert = PrecedentExpert()

        sources = [
            {"text": "Sentenza tribunale...", "court": "tribunale"},
            {"text": "Corte Costituzionale n. 123/2020...", "court": "corte_costituzionale"},
            {"text": "Cass. sez. III...", "court": "cassazione"},
        ]

        ranked = expert._rank_by_authority(sources)

        # Corte Cost. dovrebbe essere prima
        assert ranked[0]["court"] == "corte_costituzionale"
        assert ranked[0]["authority_score"] == 1.0

    @pytest.mark.asyncio
    async def test_search_jurisprudence(self):
        """Test ricerca giurisprudenza."""
        tools = [MockSemanticSearchTool()]
        expert = PrecedentExpert(tools=tools)

        context = ExpertContext(
            query_text="test giurisprudenza",
            entities={"legal_concepts": ["legittima difesa"]}
        )

        jur = await expert._search_jurisprudence(context)

        assert isinstance(jur, list)


# ============================================================================
# Integration Tests - All 4 Experts
# ============================================================================

class TestAllExpertsIntegration:
    """Test di integrazione per tutti e 4 gli Expert."""

    @pytest.mark.asyncio
    async def test_all_experts_same_query(self):
        """Tutti gli expert analizzano la stessa query."""
        query = "Interpretazione dell'art. 2043 c.c. sul danno ingiusto"

        experts = [
            LiteralExpert(),
            SystemicExpert(),
            PrinciplesExpert(),
            PrecedentExpert(),
        ]

        context = ExpertContext(
            query_text=query,
            entities={
                "norm_references": ["urn:norma:cc:art2043"],
                "legal_concepts": ["danno ingiusto", "responsabilità civile"]
            }
        )

        responses = []
        for expert in experts:
            response = await expert.analyze(context)
            responses.append(response)

        # Tutti dovrebbero produrre risposte valide
        assert len(responses) == 4

        expert_types = [r.expert_type for r in responses]
        assert "literal" in expert_types
        assert "systemic" in expert_types
        assert "principles" in expert_types
        assert "precedent" in expert_types

        # Tutti dovrebbero avere lo stesso trace_id
        trace_ids = [r.trace_id for r in responses]
        assert all(t == context.trace_id for t in trace_ids)

    @pytest.mark.asyncio
    async def test_all_experts_with_tools(self):
        """Tutti gli expert con tools."""
        tools = [MockSemanticSearchTool(), MockGraphSearchTool()]

        experts = [
            LiteralExpert(tools=tools),
            SystemicExpert(tools=tools),
            PrinciplesExpert(tools=tools),
            PrecedentExpert(tools=tools),
        ]

        context = ExpertContext(query_text="Test con tools")

        for expert in experts:
            response = await expert.analyze(context)
            assert response.execution_time_ms > 0
            assert response.trace_id == context.trace_id

    def test_all_experts_different_weights(self):
        """Verifica che ogni expert abbia pesi diversi."""
        experts = [
            LiteralExpert(),
            SystemicExpert(),
            PrinciplesExpert(),
            PrecedentExpert(),
        ]

        # I pesi dovrebbero essere diversi per ogni expert
        weight_sets = []
        for expert in experts:
            weights = expert.traversal_weights
            # Prendi le top-3 relazioni per ogni expert
            top_relations = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
            weight_sets.append(tuple(r[0] for r in top_relations))

        # Le top relazioni dovrebbero essere diverse
        # (ogni expert privilegia relazioni diverse)
        assert len(set(weight_sets)) >= 3  # Almeno 3 set diversi
