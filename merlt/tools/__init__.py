"""
MERL-T Tools Module
====================

Tools sono funzioni atomiche che gli Expert possono invocare per:
- Cercare nel knowledge graph (SemanticSearchTool, GraphSearchTool)
- Recuperare documenti (ArticleRetrieveTool, DottrinaRetrieveTool)
- Calcolare termini/prescrizioni (TerminiTool, PrescrizioneTool)
- Navigare relazioni (TraverseTool, PathFindTool)

Ogni tool:
- Implementa BaseTool
- Ha schema JSON per LLM function calling
- E' registrato in ToolRegistry

Esempio:
    >>> from merlt.tools import get_tool_registry, SemanticSearchTool
    >>>
    >>> # Registra tool
    >>> registry = get_tool_registry()
    >>> registry.register(SemanticSearchTool(retriever))
    >>>
    >>> # Usa tool
    >>> tool = registry.get("semantic_search")
    >>> result = await tool(query="contratto", top_k=5)
    >>> print(result.data)
"""

from merlt.tools.base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolChain,
)
from merlt.tools.registry import (
    ToolRegistry,
    get_tool_registry,
    register_tool,
)
from merlt.tools.search import (
    SemanticSearchTool,
    GraphSearchTool,
    SearchResultItem,
)

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ParameterType",
    "ToolChain",
    # Registry
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    # Search tools
    "SemanticSearchTool",
    "GraphSearchTool",
    "SearchResultItem",
]
