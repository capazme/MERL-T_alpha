"""
Tests for Search Tools.
"""

import pytest
from typing import List
from uuid import UUID, uuid4
from dataclasses import dataclass

from merlt.tools import (
    SemanticSearchTool,
    GraphSearchTool,
    SearchResultItem,
    ToolResult,
)


# Mock classes for testing
@dataclass
class MockRetrievalResult:
    """Mock del risultato di retrieval."""
    chunk_id: UUID
    text: str
    similarity_score: float
    graph_score: float
    final_score: float
    linked_nodes: List[dict]
    metadata: dict


class MockRetriever:
    """Mock di GraphAwareRetriever."""

    def __init__(self, results: List[MockRetrievalResult] = None):
        self.results = results or []
        self.last_call = None

    async def retrieve(
        self,
        query_embedding: List[float],
        context_nodes: List[str] = None,
        expert_type: str = None,
        top_k: int = 10
    ) -> List[MockRetrievalResult]:
        self.last_call = {
            "query_embedding": query_embedding,
            "context_nodes": context_nodes,
            "expert_type": expert_type,
            "top_k": top_k
        }
        return self.results[:top_k]


class MockEmbeddings:
    """Mock di EmbeddingService."""

    def encode_query(self, text: str) -> List[float]:
        # Ritorna un vettore finto
        return [0.1] * 1024


class MockGraphDB:
    """Mock di FalkorDBClient."""

    def __init__(self, query_results: List[dict] = None):
        self.query_results = query_results or []
        self.last_query = None

    async def execute_query(self, query: str, params: dict) -> List[dict]:
        self.last_query = {"query": query, "params": params}
        return self.query_results


class TestSearchResultItem:
    """Test per SearchResultItem."""

    def test_create(self):
        """Crea SearchResultItem."""
        item = SearchResultItem(
            chunk_id="abc123",
            text="Testo di esempio",
            similarity_score=0.85,
            graph_score=0.70,
            final_score=0.80,
            linked_nodes=[{"urn": "urn:norma:cc:art1"}],
            metadata={"source": "test"}
        )
        assert item.chunk_id == "abc123"
        assert item.final_score == 0.80

    def test_to_dict(self):
        """Converte in dizionario."""
        item = SearchResultItem(
            chunk_id="abc123",
            text="Testo",
            similarity_score=0.85,
            graph_score=0.70,
            final_score=0.80,
            linked_nodes=[],
            metadata={}
        )
        d = item.to_dict()

        assert d["chunk_id"] == "abc123"
        assert d["similarity_score"] == 0.85
        assert "final_score" in d


class TestSemanticSearchTool:
    """Test per SemanticSearchTool."""

    def test_init(self):
        """Inizializza tool."""
        tool = SemanticSearchTool()
        assert tool.name == "semantic_search"
        assert "knowledge graph" in tool.description.lower()

    def test_init_with_dependencies(self):
        """Inizializza con dipendenze."""
        retriever = MockRetriever()
        embeddings = MockEmbeddings()

        tool = SemanticSearchTool(
            retriever=retriever,
            embeddings=embeddings,
            default_top_k=5,
            default_expert_type="LiteralExpert"
        )

        assert tool.retriever is retriever
        assert tool.embeddings is embeddings
        assert tool.default_top_k == 5

    def test_parameters(self):
        """Verifica parametri definiti."""
        tool = SemanticSearchTool()
        params = {p.name: p for p in tool.parameters}

        assert "query" in params
        assert params["query"].required is True

        assert "top_k" in params
        assert params["top_k"].required is False

        assert "expert_type" in params
        assert params["expert_type"].enum is not None

    def test_get_schema(self):
        """Genera schema JSON."""
        tool = SemanticSearchTool()
        schema = tool.get_schema()

        assert schema["name"] == "semantic_search"
        assert "parameters" in schema
        assert "query" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_no_embeddings(self):
        """Errore se manca EmbeddingService."""
        tool = SemanticSearchTool(retriever=MockRetriever())
        result = await tool(query="test")

        assert result.success is False
        assert "EmbeddingService" in result.error

    @pytest.mark.asyncio
    async def test_execute_no_retriever(self):
        """Errore se manca Retriever."""
        tool = SemanticSearchTool(embeddings=MockEmbeddings())
        result = await tool(query="test")

        assert result.success is False
        assert "Retriever" in result.error

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Esegue ricerca con successo."""
        mock_results = [
            MockRetrievalResult(
                chunk_id=uuid4(),
                text="Art. 1453 c.c. - La risoluzione del contratto...",
                similarity_score=0.85,
                graph_score=0.70,
                final_score=0.80,
                linked_nodes=[{"graph_node_urn": "urn:norma:cc:art1453"}],
                metadata={"source": "codice_civile"}
            ),
            MockRetrievalResult(
                chunk_id=uuid4(),
                text="Art. 1454 c.c. - Diffida ad adempiere...",
                similarity_score=0.75,
                graph_score=0.65,
                final_score=0.72,
                linked_nodes=[{"graph_node_urn": "urn:norma:cc:art1454"}],
                metadata={"source": "codice_civile"}
            )
        ]

        retriever = MockRetriever(results=mock_results)
        embeddings = MockEmbeddings()
        tool = SemanticSearchTool(retriever=retriever, embeddings=embeddings)

        result = await tool(query="risoluzione contratto", top_k=5)

        assert result.success is True
        assert result.data["total"] == 2
        assert len(result.data["results"]) == 2
        assert result.data["results"][0]["final_score"] == 0.80

    @pytest.mark.asyncio
    async def test_execute_with_expert_type(self):
        """Passa expert_type al retriever."""
        retriever = MockRetriever(results=[])
        embeddings = MockEmbeddings()
        tool = SemanticSearchTool(retriever=retriever, embeddings=embeddings)

        await tool(query="test", expert_type="LiteralExpert")

        assert retriever.last_call["expert_type"] == "LiteralExpert"

    @pytest.mark.asyncio
    async def test_execute_with_context_nodes(self):
        """Passa context_nodes al retriever."""
        retriever = MockRetriever(results=[])
        embeddings = MockEmbeddings()
        tool = SemanticSearchTool(retriever=retriever, embeddings=embeddings)

        await tool(
            query="test",
            context_nodes=["urn:norma:cc:art1453"]
        )

        assert retriever.last_call["context_nodes"] == ["urn:norma:cc:art1453"]

    @pytest.mark.asyncio
    async def test_execute_min_score_filter(self):
        """Filtra risultati per min_score."""
        mock_results = [
            MockRetrievalResult(
                chunk_id=uuid4(),
                text="High score result",
                similarity_score=0.90,
                graph_score=0.85,
                final_score=0.88,
                linked_nodes=[],
                metadata={}
            ),
            MockRetrievalResult(
                chunk_id=uuid4(),
                text="Low score result",
                similarity_score=0.40,
                graph_score=0.30,
                final_score=0.35,
                linked_nodes=[],
                metadata={}
            )
        ]

        retriever = MockRetriever(results=mock_results)
        embeddings = MockEmbeddings()
        tool = SemanticSearchTool(retriever=retriever, embeddings=embeddings)

        result = await tool(query="test", min_score=0.5)

        assert result.success is True
        assert result.data["total"] == 1
        assert result.data["results"][0]["final_score"] == 0.88

    @pytest.mark.asyncio
    async def test_execute_default_expert_type(self):
        """Usa default_expert_type se non specificato."""
        retriever = MockRetriever(results=[])
        embeddings = MockEmbeddings()
        tool = SemanticSearchTool(
            retriever=retriever,
            embeddings=embeddings,
            default_expert_type="SystemicExpert"
        )

        await tool(query="test")

        assert retriever.last_call["expert_type"] == "SystemicExpert"


class TestGraphSearchTool:
    """Test per GraphSearchTool."""

    def test_init(self):
        """Inizializza tool."""
        tool = GraphSearchTool()
        assert tool.name == "graph_search"
        assert "traversal" in tool.description.lower()

    def test_init_with_dependencies(self):
        """Inizializza con dipendenze."""
        graph_db = MockGraphDB()
        tool = GraphSearchTool(graph_db=graph_db, default_max_hops=3)

        assert tool.graph_db is graph_db
        assert tool.default_max_hops == 3

    def test_parameters(self):
        """Verifica parametri definiti."""
        tool = GraphSearchTool()
        params = {p.name: p for p in tool.parameters}

        assert "start_node" in params
        assert params["start_node"].required is True

        assert "max_hops" in params
        assert params["max_hops"].required is False

        assert "direction" in params
        assert params["direction"].enum is not None

    def test_get_schema(self):
        """Genera schema JSON."""
        tool = GraphSearchTool()
        schema = tool.get_schema()

        assert schema["name"] == "graph_search"
        assert "parameters" in schema
        assert "start_node" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_no_graph_db(self):
        """Errore se manca FalkorDB."""
        tool = GraphSearchTool()
        result = await tool(start_node="urn:norma:cp:art52")

        assert result.success is False
        assert "FalkorDB" in result.error

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Esegue traversal con successo."""
        mock_results = [
            {
                "node": {"URN": "urn:concetto:legittima_difesa", "_type": "ConcettoGiuridico"},
                "rel": {"type": "disciplina"}
            },
            {
                "node": {"URN": "urn:norma:cp:art55", "_type": "Norma"},
                "rel": {"type": "cita"}
            }
        ]

        graph_db = MockGraphDB(query_results=mock_results)
        tool = GraphSearchTool(graph_db=graph_db)

        result = await tool(
            start_node="urn:norma:cp:art52",
            relation_types=["disciplina", "cita"],
            max_hops=2
        )

        assert result.success is True
        assert result.data["total_nodes"] == 2
        assert result.data["total_edges"] == 2

    @pytest.mark.asyncio
    async def test_execute_with_direction(self):
        """Verifica direzione nel query."""
        graph_db = MockGraphDB(query_results=[])
        tool = GraphSearchTool(graph_db=graph_db)

        await tool(
            start_node="urn:norma:cp:art52",
            direction="incoming"
        )

        # Verifica che la query contenga la direzione corretta
        assert graph_db.last_query is not None
        assert "<-" in graph_db.last_query["query"]

    @pytest.mark.asyncio
    async def test_execute_with_target_type(self):
        """Verifica filtro target type."""
        graph_db = MockGraphDB(query_results=[])
        tool = GraphSearchTool(graph_db=graph_db)

        await tool(
            start_node="urn:norma:cp:art52",
            target_type="ConcettoGiuridico"
        )

        # Verifica che la query contenga il filtro
        assert graph_db.last_query is not None
        assert "ConcettoGiuridico" in graph_db.last_query["query"]

    def test_build_traversal_query_outgoing(self):
        """Query per direzione outgoing."""
        tool = GraphSearchTool()
        query, params = tool._build_traversal_query(
            start_node="urn:test",
            max_hops=2,
            direction="outgoing"
        )

        assert "->" in query
        assert params["start_urn"] == "urn:test"

    def test_build_traversal_query_incoming(self):
        """Query per direzione incoming."""
        tool = GraphSearchTool()
        query, params = tool._build_traversal_query(
            start_node="urn:test",
            max_hops=2,
            direction="incoming"
        )

        assert "<-" in query

    def test_build_traversal_query_both(self):
        """Query per direzione both."""
        tool = GraphSearchTool()
        query, params = tool._build_traversal_query(
            start_node="urn:test",
            max_hops=2,
            direction="both"
        )

        # Neither -> nor <- specifically, just generic
        assert "-[r*" in query

    def test_build_traversal_query_with_relations(self):
        """Query con tipi relazione specifici."""
        tool = GraphSearchTool()
        query, params = tool._build_traversal_query(
            start_node="urn:test",
            relation_types=["disciplina", "cita"],
            max_hops=2
        )

        assert "disciplina|cita" in query

    def test_node_to_dict(self):
        """Converte nodo in dizionario."""
        tool = GraphSearchTool()

        node = {"URN": "urn:test", "_type": "Norma", "titolo": "Test"}
        result = tool._node_to_dict(node)

        assert result["urn"] == "urn:test"
        assert result["type"] == "Norma"
        assert "titolo" in result["properties"]

    def test_edge_to_dict(self):
        """Converte edge in dizionario."""
        tool = GraphSearchTool()

        edge = {"type": "disciplina", "weight": 0.9}
        result = tool._edge_to_dict(edge)

        assert result["type"] == "disciplina"
        assert "properties" in result
