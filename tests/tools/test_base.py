"""
Tests for Tool base classes.
"""

import pytest
from typing import List

from merlt.tools import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolChain,
)


class TestToolParameter:
    """Test per ToolParameter."""

    def test_create_simple(self):
        """Crea parametro semplice."""
        param = ToolParameter(
            name="query",
            param_type=ParameterType.STRING,
            description="Query di ricerca"
        )
        assert param.name == "query"
        assert param.param_type == ParameterType.STRING
        assert param.required is True

    def test_create_optional(self):
        """Crea parametro opzionale."""
        param = ToolParameter(
            name="top_k",
            param_type=ParameterType.INTEGER,
            description="Numero risultati",
            required=False,
            default=5
        )
        assert param.required is False
        assert param.default == 5

    def test_create_with_enum(self):
        """Crea parametro con enum."""
        param = ToolParameter(
            name="source_type",
            param_type=ParameterType.STRING,
            description="Tipo sorgente",
            enum=["norma", "massima", "dottrina"]
        )
        assert param.enum == ["norma", "massima", "dottrina"]

    def test_to_json_schema(self):
        """Converte in JSON schema."""
        param = ToolParameter(
            name="query",
            param_type=ParameterType.STRING,
            description="Query di ricerca"
        )
        schema = param.to_json_schema()

        assert schema["type"] == "string"
        assert schema["description"] == "Query di ricerca"

    def test_to_json_schema_with_enum(self):
        """JSON schema con enum."""
        param = ToolParameter(
            name="type",
            param_type=ParameterType.STRING,
            description="Tipo",
            enum=["a", "b"]
        )
        schema = param.to_json_schema()

        assert "enum" in schema
        assert schema["enum"] == ["a", "b"]


class TestToolResult:
    """Test per ToolResult."""

    def test_create_success(self):
        """Crea risultato positivo."""
        result = ToolResult(success=True, data={"items": [1, 2, 3]})
        assert result.success is True
        assert result.data == {"items": [1, 2, 3]}
        assert result.error is None

    def test_create_failure(self):
        """Crea risultato negativo."""
        result = ToolResult(success=False, error="Not found")
        assert result.success is False
        assert result.error == "Not found"

    def test_ok_factory(self):
        """Factory method ok()."""
        result = ToolResult.ok(
            data=[1, 2, 3],
            tool_name="test_tool",
            custom_meta="value"
        )
        assert result.success is True
        assert result.data == [1, 2, 3]
        assert result.tool_name == "test_tool"
        assert result.metadata["custom_meta"] == "value"

    def test_fail_factory(self):
        """Factory method fail()."""
        result = ToolResult.fail(
            error="Something went wrong",
            tool_name="test_tool"
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.tool_name == "test_tool"

    def test_timestamp_added(self):
        """Timestamp aggiunto automaticamente."""
        result = ToolResult(success=True, data={})
        assert "timestamp" in result.metadata


class MockTool(BaseTool):
    """Tool di test."""
    name = "mock_tool"
    description = "Tool di test per unit testing"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", ParameterType.STRING, "Query"),
            ToolParameter("limit", ParameterType.INTEGER, "Limit", required=False, default=10),
        ]

    async def execute(self, query: str, limit: int = 10) -> ToolResult:
        return ToolResult.ok(
            data={"query": query, "limit": limit, "results": []},
            tool_name=self.name
        )


class FailingTool(BaseTool):
    """Tool che fallisce sempre."""
    name = "failing_tool"
    description = "Tool che fallisce"

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    async def execute(self) -> ToolResult:
        raise ValueError("Intentional failure")


class TestBaseTool:
    """Test per BaseTool."""

    def test_init_valid(self):
        """Inizializza tool valido."""
        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "Tool di test per unit testing"

    def test_init_no_name(self):
        """Errore se manca nome."""
        class NoNameTool(BaseTool):
            description = "Test"

            @property
            def parameters(self):
                return []

            async def execute(self):
                pass

        with pytest.raises(ValueError, match="must have a name"):
            NoNameTool()

    def test_init_no_description(self):
        """Errore se manca descrizione."""
        class NoDescTool(BaseTool):
            name = "test"

            @property
            def parameters(self):
                return []

            async def execute(self):
                pass

        with pytest.raises(ValueError, match="must have a description"):
            NoDescTool()

    def test_validate_params_valid(self):
        """Validazione parametri validi."""
        tool = MockTool()
        error = tool.validate_params(query="test")
        assert error is None

    def test_validate_params_missing_required(self):
        """Errore per parametro obbligatorio mancante."""
        tool = MockTool()
        error = tool.validate_params()
        assert "Missing required parameter: query" in error

    def test_validate_params_unknown(self):
        """Errore per parametro sconosciuto."""
        tool = MockTool()
        error = tool.validate_params(query="test", unknown="value")
        assert "Unknown parameter: unknown" in error

    def test_get_schema(self):
        """Genera schema JSON."""
        tool = MockTool()
        schema = tool.get_schema()

        assert schema["name"] == "mock_tool"
        assert schema["description"] == "Tool di test per unit testing"
        assert "parameters" in schema
        assert "query" in schema["parameters"]["properties"]
        assert "query" in schema["parameters"]["required"]

    def test_repr(self):
        """Rappresentazione stringa."""
        tool = MockTool()
        assert "MockTool" in repr(tool)
        assert "mock_tool" in repr(tool)


class TestBaseToolAsync:
    """Test async per BaseTool."""

    @pytest.mark.asyncio
    async def test_execute(self):
        """Esegue tool."""
        tool = MockTool()
        result = await tool.execute(query="test", limit=5)

        assert result.success is True
        assert result.data["query"] == "test"
        assert result.data["limit"] == 5

    @pytest.mark.asyncio
    async def test_call_with_validation(self):
        """Esegue via __call__ con validazione."""
        tool = MockTool()
        result = await tool(query="test")

        assert result.success is True
        assert result.data["query"] == "test"

    @pytest.mark.asyncio
    async def test_call_invalid_params(self):
        """__call__ fallisce con parametri invalidi."""
        tool = MockTool()
        result = await tool()  # Missing required param

        assert result.success is False
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_call_catches_exception(self):
        """__call__ cattura eccezioni."""
        tool = FailingTool()
        result = await tool()

        assert result.success is False
        assert "Intentional failure" in result.error


class TestToolChain:
    """Test per ToolChain."""

    @pytest.mark.asyncio
    async def test_chain_success(self):
        """Esegue chain con successo."""
        tool1 = MockTool()

        class TransformTool(BaseTool):
            name = "transform"
            description = "Trasforma risultati"

            @property
            def parameters(self):
                # Parametri opzionali - la chain passa il dict del tool precedente
                return [
                    ToolParameter("query", ParameterType.STRING, "Query", required=False),
                    ToolParameter("limit", ParameterType.INTEGER, "Limit", required=False),
                    ToolParameter("results", ParameterType.ARRAY, "Results", required=False),
                ]

            async def execute(self, **kwargs):
                return ToolResult.ok(
                    data={"transformed": True, "received": kwargs},
                    tool_name=self.name
                )

        tool2 = TransformTool()
        chain = ToolChain([tool1, tool2])

        result = await chain.execute(query="test")

        assert result.success is True
        assert result.data["transformed"] is True
        assert result.data["received"]["query"] == "test"
        assert chain.name == "mock_tool -> transform"

    @pytest.mark.asyncio
    async def test_chain_failure_stops(self):
        """Chain si ferma al primo errore."""
        tool1 = FailingTool()
        tool2 = MockTool()

        chain = ToolChain([tool1, tool2])
        result = await chain.execute()

        assert result.success is False
        assert "Chain failed at failing_tool" in result.error
