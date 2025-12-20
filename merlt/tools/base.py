"""
Tool Base Classes
==================

Classi base per i tools del sistema Expert.

I tools sono funzioni atomiche che gli Expert possono invocare per:
- Cercare nel knowledge graph
- Recuperare documenti
- Calcolare termini/prescrizioni
- Navigare relazioni

Architettura:
    Expert -> seleziona Tool -> esegue -> ToolResult
              (via ToolRegistry)

Ogni tool:
- Ha un nome e descrizione (per LLM function calling)
- Dichiara parametri tipizzati
- Ritorna ToolResult con dati strutturati
"""

import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime

log = structlog.get_logger()


class ParameterType(str, Enum):
    """Tipi supportati per parametri tool."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """
    Definizione di un parametro per un tool.

    Usato per generare schema JSON per LLM function calling.

    Attributes:
        name: Nome del parametro
        param_type: Tipo del parametro
        description: Descrizione (in italiano per LLM)
        required: Se il parametro e' obbligatorio
        default: Valore default se non fornito
        enum: Valori ammessi (per enum)
    """
    name: str
    param_type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Converte in JSON Schema per function calling."""
        schema = {
            "type": self.param_type.value,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class ToolResult:
    """
    Risultato dell'esecuzione di un tool.

    Attributes:
        success: Se l'esecuzione e' andata a buon fine
        data: Dati risultanti (struttura dipende dal tool)
        error: Messaggio di errore se success=False
        metadata: Metadati aggiuntivi (timing, source, etc.)
        tool_name: Nome del tool che ha prodotto il risultato
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_name: Optional[str] = None

    def __post_init__(self):
        """Aggiunge timestamp se non presente."""
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = datetime.now().isoformat()

    @classmethod
    def ok(cls, data: Any, tool_name: str = None, **metadata) -> "ToolResult":
        """Factory method per risultato positivo."""
        return cls(
            success=True,
            data=data,
            tool_name=tool_name,
            metadata=metadata
        )

    @classmethod
    def fail(cls, error: str, tool_name: str = None, **metadata) -> "ToolResult":
        """Factory method per risultato negativo."""
        return cls(
            success=False,
            error=error,
            tool_name=tool_name,
            metadata=metadata
        )


class BaseTool(ABC):
    """
    Classe base astratta per tutti i tools.

    Ogni tool deve implementare:
    - name: Nome univoco del tool
    - description: Descrizione per LLM (in italiano)
    - parameters: Lista di ToolParameter
    - execute(): Logica di esecuzione

    Esempio:
        >>> class SemanticSearchTool(BaseTool):
        ...     name = "semantic_search"
        ...     description = "Cerca nel knowledge graph per similarita' semantica"
        ...
        ...     @property
        ...     def parameters(self) -> List[ToolParameter]:
        ...         return [
        ...             ToolParameter("query", ParameterType.STRING, "Query di ricerca"),
        ...             ToolParameter("top_k", ParameterType.INTEGER, "Numero risultati", required=False, default=5),
        ...         ]
        ...
        ...     async def execute(self, query: str, top_k: int = 5) -> ToolResult:
        ...         results = await self.retriever.search(query, top_k)
        ...         return ToolResult.ok(results, tool_name=self.name)
    """

    # Sottoclassi devono definire questi attributi
    name: str = ""
    description: str = ""

    def __init__(self):
        """Inizializza il tool."""
        if not self.name:
            raise ValueError("Tool must have a name")
        if not self.description:
            raise ValueError("Tool must have a description")

        log.debug(f"Tool initialized: {self.name}")

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """
        Lista dei parametri accettati dal tool.

        Returns:
            Lista di ToolParameter che definiscono l'interfaccia
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Esegue il tool con i parametri forniti.

        Args:
            **kwargs: Parametri come definiti in self.parameters

        Returns:
            ToolResult con i dati o errore
        """
        pass

    def validate_params(self, **kwargs) -> Optional[str]:
        """
        Valida i parametri prima dell'esecuzione.

        Returns:
            None se valido, messaggio di errore altrimenti
        """
        param_names = {p.name for p in self.parameters}
        required_params = {p.name for p in self.parameters if p.required}

        # Check required params
        for param in required_params:
            if param not in kwargs or kwargs[param] is None:
                return f"Missing required parameter: {param}"

        # Check unknown params
        for param in kwargs:
            if param not in param_names:
                return f"Unknown parameter: {param}"

        return None

    async def __call__(self, **kwargs) -> ToolResult:
        """
        Esegue il tool con validazione.

        Shortcut per validate + execute.
        """
        error = self.validate_params(**kwargs)
        if error:
            return ToolResult.fail(error, tool_name=self.name)

        try:
            return await self.execute(**kwargs)
        except Exception as e:
            log.error(f"Tool {self.name} failed", error=str(e))
            return ToolResult.fail(str(e), tool_name=self.name)

    def get_schema(self) -> Dict[str, Any]:
        """
        Genera schema JSON per LLM function calling.

        Compatibile con OpenAI/Anthropic function calling format.
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"


class ToolChain:
    """
    Catena di tools da eseguire in sequenza.

    Utile per operazioni multi-step dove l'output di un tool
    alimenta l'input del successivo.

    Esempio:
        >>> chain = ToolChain([search_tool, retrieve_tool, summarize_tool])
        >>> result = await chain.execute(query="legittima difesa")
    """

    def __init__(self, tools: List[BaseTool]):
        """
        Inizializza la chain.

        Args:
            tools: Lista ordinata di tools da eseguire
        """
        self.tools = tools
        self.name = " -> ".join(t.name for t in tools)

    async def execute(self, **initial_kwargs) -> ToolResult:
        """
        Esegue la chain passando output come input.

        Args:
            **initial_kwargs: Parametri per il primo tool

        Returns:
            ToolResult finale o primo errore
        """
        current_kwargs = initial_kwargs
        results = []

        for tool in self.tools:
            result = await tool(**current_kwargs)
            results.append(result)

            if not result.success:
                return ToolResult.fail(
                    f"Chain failed at {tool.name}: {result.error}",
                    tool_name=self.name,
                    partial_results=results
                )

            # Pass data as input to next tool
            if isinstance(result.data, dict):
                current_kwargs = result.data
            else:
                current_kwargs = {"input": result.data}

        return ToolResult.ok(
            data=results[-1].data if results else None,
            tool_name=self.name,
            chain_results=results
        )
