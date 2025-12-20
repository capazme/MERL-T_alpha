"""
Tests for Tool Registry.
"""

import pytest
from typing import List

from merlt.tools import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolRegistry,
    get_tool_registry,
    register_tool,
)


class SampleTool(BaseTool):
    """Tool di esempio per test."""
    name = "sample_tool"
    description = "Tool di esempio"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", ParameterType.STRING, "Query di ricerca"),
        ]

    async def execute(self, query: str) -> ToolResult:
        return ToolResult.ok(data={"query": query}, tool_name=self.name)


class AnotherTool(BaseTool):
    """Altro tool di esempio."""
    name = "another_tool"
    description = "Altro tool"

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    async def execute(self) -> ToolResult:
        return ToolResult.ok(data={"status": "ok"}, tool_name=self.name)


class TestToolRegistry:
    """Test per ToolRegistry."""

    def test_init(self):
        """Crea registry vuoto."""
        registry = ToolRegistry()
        assert len(registry) == 0

    def test_register_tool(self):
        """Registra un tool."""
        registry = ToolRegistry()
        tool = SampleTool()

        registry.register(tool)

        assert "sample_tool" in registry
        assert len(registry) == 1

    def test_register_with_category(self):
        """Registra tool con categoria."""
        registry = ToolRegistry()
        tool = SampleTool()

        registry.register(tool, category="search")

        assert "search" in registry.list_categories()
        assert "sample_tool" in registry.list(category="search")

    def test_register_duplicate_fails(self):
        """Errore se tool già registrato."""
        registry = ToolRegistry()
        tool = SampleTool()

        registry.register(tool)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool)

    def test_get_tool(self):
        """Ottiene tool per nome."""
        registry = ToolRegistry()
        tool = SampleTool()
        registry.register(tool)

        result = registry.get("sample_tool")

        assert result is tool

    def test_get_nonexistent(self):
        """None per tool inesistente."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_get_required(self):
        """get_required per tool esistente."""
        registry = ToolRegistry()
        tool = SampleTool()
        registry.register(tool)

        result = registry.get_required("sample_tool")
        assert result is tool

    def test_get_required_missing(self):
        """Errore per tool mancante con get_required."""
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.get_required("nonexistent")

    def test_list_all(self):
        """Lista tutti i tools."""
        registry = ToolRegistry()
        registry.register(SampleTool())
        registry.register(AnotherTool())

        tools = registry.list()

        assert len(tools) == 2
        assert "sample_tool" in tools
        assert "another_tool" in tools

    def test_list_by_category(self):
        """Lista tools per categoria."""
        registry = ToolRegistry()
        registry.register(SampleTool(), category="search")
        registry.register(AnotherTool(), category="utility")

        search_tools = registry.list(category="search")
        utility_tools = registry.list(category="utility")

        assert search_tools == ["sample_tool"]
        assert utility_tools == ["another_tool"]

    def test_list_empty_category(self):
        """Lista vuota per categoria inesistente."""
        registry = ToolRegistry()
        assert registry.list(category="nonexistent") == []

    def test_unregister(self):
        """Rimuove tool."""
        registry = ToolRegistry()
        registry.register(SampleTool())

        assert registry.unregister("sample_tool") is True
        assert "sample_tool" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent(self):
        """False per tool inesistente."""
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_unregister_removes_from_category(self):
        """Unregister rimuove da categoria."""
        registry = ToolRegistry()
        registry.register(SampleTool(), category="search")

        registry.unregister("sample_tool")

        assert "sample_tool" not in registry.list(category="search")

    def test_get_all(self):
        """Ottiene istanze di tutti i tools."""
        registry = ToolRegistry()
        tool1 = SampleTool()
        tool2 = AnotherTool()
        registry.register(tool1)
        registry.register(tool2)

        all_tools = registry.get_all()

        assert len(all_tools) == 2
        assert tool1 in all_tools
        assert tool2 in all_tools

    def test_get_all_by_category(self):
        """Ottiene tools per categoria."""
        registry = ToolRegistry()
        tool1 = SampleTool()
        tool2 = AnotherTool()
        registry.register(tool1, category="search")
        registry.register(tool2, category="utility")

        search_tools = registry.get_all(category="search")

        assert len(search_tools) == 1
        assert tool1 in search_tools

    def test_get_schema(self):
        """Ottiene schema di un tool."""
        registry = ToolRegistry()
        registry.register(SampleTool())

        schema = registry.get_schema("sample_tool")

        assert schema["name"] == "sample_tool"
        assert "parameters" in schema

    def test_get_schema_nonexistent(self):
        """None per schema di tool inesistente."""
        registry = ToolRegistry()
        assert registry.get_schema("nonexistent") is None

    def test_get_all_schemas(self):
        """Ottiene tutti gli schemi."""
        registry = ToolRegistry()
        registry.register(SampleTool())
        registry.register(AnotherTool())

        schemas = registry.get_all_schemas()

        assert len(schemas) == 2
        names = [s["name"] for s in schemas]
        assert "sample_tool" in names
        assert "another_tool" in names

    def test_iter(self):
        """Itera sui nomi dei tools."""
        registry = ToolRegistry()
        registry.register(SampleTool())
        registry.register(AnotherTool())

        names = list(registry)

        assert len(names) == 2

    def test_contains(self):
        """Operatore in per verificare esistenza."""
        registry = ToolRegistry()
        registry.register(SampleTool())

        assert "sample_tool" in registry
        assert "nonexistent" not in registry


class TestToolRegistryAsync:
    """Test async per ToolRegistry."""

    @pytest.mark.asyncio
    async def test_execute(self):
        """Esegue tool tramite registry."""
        registry = ToolRegistry()
        registry.register(SampleTool())

        result = await registry.execute("sample_tool", query="test")

        assert result.success is True
        assert result.data["query"] == "test"

    @pytest.mark.asyncio
    async def test_execute_nonexistent(self):
        """Errore per tool inesistente."""
        registry = ToolRegistry()

        result = await registry.execute("nonexistent")

        assert result.success is False
        assert "not found" in result.error


class TestSingletonRegistry:
    """Test per singleton registry."""

    def test_get_tool_registry_singleton(self):
        """get_tool_registry ritorna sempre la stessa istanza."""
        # Reset singleton per test isolato
        import merlt.tools.registry as reg_module
        reg_module._default_registry = None

        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

        # Cleanup
        reg_module._default_registry = None

    def test_register_tool_helper(self):
        """Helper register_tool usa singleton."""
        import merlt.tools.registry as reg_module
        reg_module._default_registry = None

        tool = SampleTool()
        register_tool(tool, category="test")

        registry = get_tool_registry()
        assert "sample_tool" in registry

        # Cleanup
        reg_module._default_registry = None
