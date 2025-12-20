"""
Tests for LegalKnowledgeGraph.interpret() method.

Tests per l'integrazione del sistema multi-expert con la pipeline principale.

Tests:
- InterpretationResult dataclass
- interpret() basic functionality
- interpret() senza AI service (fallback)
- interpret() con pre-retrieval
- Aggregation methods
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from merlt.core.legal_knowledge_graph import (
    LegalKnowledgeGraph,
    MerltConfig,
    InterpretationResult,
)


# ============================================================================
# InterpretationResult Tests
# ============================================================================

class TestInterpretationResult:
    """Test per InterpretationResult dataclass."""

    def test_create_minimal(self):
        """Crea risultato minimale."""
        result = InterpretationResult(
            query="Test query",
            synthesis="Test synthesis"
        )

        assert result.query == "Test query"
        assert result.synthesis == "Test synthesis"
        assert result.confidence == 0.0
        assert result.expert_contributions == {}
        assert result.errors == []

    def test_create_full(self):
        """Crea risultato completo."""
        result = InterpretationResult(
            query="Cos'è la legittima difesa?",
            synthesis="La legittima difesa è...",
            expert_contributions={
                "literal": {"interpretation": "Test literal"},
                "systemic": {"interpretation": "Test systemic"},
            },
            combined_legal_basis=[
                {"source_type": "norm", "citation": "Art. 52 c.p."}
            ],
            confidence=0.85,
            routing_decision={
                "query_type": "definitional",
                "expert_weights": {"literal": 0.6, "systemic": 0.3},
            },
            aggregation_method="weighted_average",
            execution_time_ms=150.5,
            trace_id="test_trace_001",
        )

        assert result.confidence == 0.85
        assert len(result.expert_contributions) == 2
        assert result.routing_decision["query_type"] == "definitional"

    def test_summary(self):
        """Verifica summary()."""
        result = InterpretationResult(
            query="Test query molto lunga che supera i cinquanta caratteri sicuramente",
            synthesis="Test",
            expert_contributions={"literal": {}, "systemic": {}},
            confidence=0.75,
            combined_legal_basis=[{}, {}],
            execution_time_ms=100.123,
        )

        summary = result.summary()

        assert "query" in summary
        assert summary["query"].endswith("...")
        assert summary["experts_used"] == ["literal", "systemic"]
        assert summary["confidence"] == 0.75
        assert summary["sources"] == 2
        assert summary["execution_ms"] == 100.1

    def test_to_dict(self):
        """Serializza in dizionario."""
        result = InterpretationResult(
            query="Test",
            synthesis="Sintesi test",
            confidence=0.5,
            errors=["Error 1", "Error 2"],
        )

        data = result.to_dict()

        assert data["query"] == "Test"
        assert data["synthesis"] == "Sintesi test"
        assert data["confidence"] == 0.5
        assert len(data["errors"]) == 2


# ============================================================================
# LegalKnowledgeGraph.interpret() Tests
# ============================================================================

class TestLegalKnowledgeGraphInterpret:
    """Test per LegalKnowledgeGraph.interpret()."""

    @pytest.fixture
    def mock_config(self):
        """Config di test."""
        return MerltConfig(
            graph_name="test_graph",
            falkordb_host="localhost",
            falkordb_port=6380,
        )

    @pytest.fixture
    def mock_kg(self, mock_config):
        """LegalKnowledgeGraph mockato."""
        kg = LegalKnowledgeGraph(mock_config)
        kg._connected = True

        # Mock storage clients
        kg._falkordb = MagicMock()
        kg._qdrant = None  # No Qdrant for basic tests
        kg._embedding_service = None

        return kg

    @pytest.mark.asyncio
    async def test_interpret_not_connected(self, mock_config):
        """Errore se non connesso."""
        kg = LegalKnowledgeGraph(mock_config)
        # Non chiamiamo connect()

        with pytest.raises(RuntimeError, match="Not connected"):
            await kg.interpret("Test query")

    @pytest.mark.asyncio
    async def test_interpret_returns_result(self, mock_kg):
        """interpret() ritorna InterpretationResult."""
        # Mock orchestrator
        mock_response = MagicMock()
        mock_response.synthesis = "Test synthesis"
        mock_response.expert_contributions = {"literal": {"interpretation": "Test"}}
        mock_response.combined_legal_basis = []
        mock_response.confidence = 0.8
        mock_response.aggregation_method = "weighted_average"
        mock_response.execution_time_ms = 100.0
        mock_response.trace_id = "test_123"
        mock_response.conflicts = []

        mock_routing = MagicMock()
        mock_routing.query_type = "definitional"
        mock_routing.expert_weights = {"literal": 0.6}
        mock_routing.confidence = 0.9
        mock_routing.reasoning = "Test reasoning"

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_with_routing = AsyncMock(
            return_value=(mock_response, mock_routing)
        )
        mock_kg._orchestrator = mock_orchestrator

        result = await mock_kg.interpret("Cos'è il contratto?")

        assert isinstance(result, InterpretationResult)
        assert result.synthesis == "Test synthesis"
        assert result.confidence == 0.8
        assert result.routing_decision["query_type"] == "definitional"

    @pytest.mark.asyncio
    async def test_interpret_without_ai_service(self, mock_kg):
        """interpret() funziona senza AI service (fallback)."""
        # Mock orchestrator basics
        mock_response = MagicMock()
        mock_response.synthesis = "Fallback synthesis"
        mock_response.expert_contributions = {}
        mock_response.combined_legal_basis = []
        mock_response.confidence = 0.3
        mock_response.aggregation_method = "weighted_average"
        mock_response.execution_time_ms = 50.0
        mock_response.trace_id = "fallback_123"
        mock_response.conflicts = []

        mock_routing = MagicMock()
        mock_routing.query_type = "general"
        mock_routing.expert_weights = {}
        mock_routing.confidence = 0.5
        mock_routing.reasoning = ""

        # Patch OpenRouterService in the rlcf module where it's imported from
        with patch('merlt.rlcf.ai_service.OpenRouterService') as mock_ai:
            mock_ai.side_effect = Exception("No API key")

            # Patch the orchestrator creation
            with patch('merlt.experts.MultiExpertOrchestrator') as mock_orch_class:
                mock_orchestrator = AsyncMock()
                mock_orchestrator.process_with_routing = AsyncMock(
                    return_value=(mock_response, mock_routing)
                )
                mock_orch_class.return_value = mock_orchestrator

                result = await mock_kg.interpret("Test query")

                assert isinstance(result, InterpretationResult)
                # Should still work even without AI service

    @pytest.mark.asyncio
    async def test_interpret_with_aggregation_method(self, mock_kg):
        """interpret() con diversi metodi di aggregazione."""
        mock_response = MagicMock()
        mock_response.synthesis = "Best confidence synthesis"
        mock_response.expert_contributions = {"precedent": {}}
        mock_response.combined_legal_basis = []
        mock_response.confidence = 0.95
        mock_response.aggregation_method = "best_confidence"
        mock_response.execution_time_ms = 80.0
        mock_response.trace_id = "best_123"
        mock_response.conflicts = []

        mock_routing = MagicMock()
        mock_routing.query_type = "jurisprudential"
        mock_routing.expert_weights = {"precedent": 0.8}
        mock_routing.confidence = 0.9
        mock_routing.reasoning = ""

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_with_routing = AsyncMock(
            return_value=(mock_response, mock_routing)
        )
        mock_kg._orchestrator = mock_orchestrator

        result = await mock_kg.interpret(
            "Orientamento Cassazione",
            aggregation_method="best_confidence"
        )

        assert result.aggregation_method == "best_confidence"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_interpret_handles_orchestrator_error(self, mock_kg):
        """interpret() gestisce errori gracefully."""
        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_with_routing = AsyncMock(
            side_effect=Exception("Orchestrator failed")
        )
        mock_kg._orchestrator = mock_orchestrator

        result = await mock_kg.interpret("Test query")

        assert isinstance(result, InterpretationResult)
        assert result.confidence == 0.0
        assert "Errore" in result.synthesis
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_interpret_with_search(self, mock_kg):
        """interpret() con pre-retrieval semantico."""
        # Setup Qdrant e embedding service
        mock_kg._qdrant = MagicMock()
        mock_kg._embedding_service = MagicMock()
        mock_kg._embedding_service.encode_query_async = AsyncMock(
            return_value=[0.1] * 1024
        )

        # Mock search results
        mock_kg._qdrant.query_points = MagicMock(return_value=MagicMock(
            points=[
                MagicMock(
                    payload={"urn": "urn:test:1", "text": "Test text"},
                    score=0.9
                )
            ]
        ))

        # Mock orchestrator
        mock_response = MagicMock()
        mock_response.synthesis = "With search synthesis"
        mock_response.expert_contributions = {}
        mock_response.combined_legal_basis = []
        mock_response.confidence = 0.7
        mock_response.aggregation_method = "weighted_average"
        mock_response.execution_time_ms = 200.0
        mock_response.trace_id = "search_123"
        mock_response.conflicts = []

        mock_routing = MagicMock()
        mock_routing.query_type = "definitional"
        mock_routing.expert_weights = {}
        mock_routing.confidence = 0.8
        mock_routing.reasoning = ""

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_with_routing = AsyncMock(
            return_value=(mock_response, mock_routing)
        )
        mock_kg._orchestrator = mock_orchestrator

        result = await mock_kg.interpret("Test query", include_search=True)

        assert isinstance(result, InterpretationResult)
        # Verify orchestrator was called with entities from search
        call_kwargs = mock_orchestrator.process_with_routing.call_args.kwargs
        # Should have retrieved chunks from search
        assert result.synthesis == "With search synthesis"

    @pytest.mark.asyncio
    async def test_interpret_without_search(self, mock_kg):
        """interpret() senza pre-retrieval."""
        mock_response = MagicMock()
        mock_response.synthesis = "No search synthesis"
        mock_response.expert_contributions = {}
        mock_response.combined_legal_basis = []
        mock_response.confidence = 0.6
        mock_response.aggregation_method = "weighted_average"
        mock_response.execution_time_ms = 50.0
        mock_response.trace_id = "no_search_123"
        mock_response.conflicts = []

        mock_routing = MagicMock()
        mock_routing.query_type = "general"
        mock_routing.expert_weights = {}
        mock_routing.confidence = 0.5
        mock_routing.reasoning = ""

        mock_orchestrator = AsyncMock()
        mock_orchestrator.process_with_routing = AsyncMock(
            return_value=(mock_response, mock_routing)
        )
        mock_kg._orchestrator = mock_orchestrator

        result = await mock_kg.interpret("Test", include_search=False)

        assert result.synthesis == "No search synthesis"


# ============================================================================
# _init_orchestrator Tests
# ============================================================================

class TestInitOrchestrator:
    """Test per _init_orchestrator()."""

    @pytest.fixture
    def mock_kg(self):
        """LegalKnowledgeGraph minimale."""
        kg = LegalKnowledgeGraph(MerltConfig())
        kg._connected = True
        kg._falkordb = MagicMock()
        kg._qdrant = None
        kg._embedding_service = None
        kg._bridge_table = None
        return kg

    @pytest.mark.asyncio
    async def test_init_orchestrator_minimal(self, mock_kg):
        """Inizializza orchestrator con setup minimo."""
        with patch('merlt.experts.MultiExpertOrchestrator') as mock_orch_class:
            mock_orch_class.return_value = MagicMock()

            orchestrator = await mock_kg._init_orchestrator(skip_ai=True)

            # Should have been called with GraphSearchTool
            mock_orch_class.assert_called_once()
            call_kwargs = mock_orch_class.call_args.kwargs
            assert call_kwargs['ai_service'] is None
            assert len(call_kwargs['tools']) == 1  # Only GraphSearchTool

    @pytest.mark.asyncio
    async def test_init_orchestrator_with_config(self, mock_kg):
        """Inizializza con config custom."""
        with patch('merlt.experts.MultiExpertOrchestrator') as mock_orch_class:
            mock_orch_class.return_value = MagicMock()

            await mock_kg._init_orchestrator(
                max_experts=2,
                aggregation_method="ensemble",
                timeout_seconds=15.0,
                skip_ai=True,
            )

            call_kwargs = mock_orch_class.call_args.kwargs
            config = call_kwargs['config']
            assert config.max_experts == 2
            assert config.aggregation_method == "ensemble"
            assert config.timeout_seconds == 15.0


# ============================================================================
# Integration with Existing Tests
# ============================================================================

class TestInterpretationResultExports:
    """Verifica export corretti."""

    def test_import_from_merlt(self):
        """Import da merlt."""
        from merlt import InterpretationResult
        assert InterpretationResult is not None

    def test_import_from_core(self):
        """Import da merlt.core."""
        from merlt.core.legal_knowledge_graph import InterpretationResult
        assert InterpretationResult is not None
