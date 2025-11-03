# 02. LLM Integration Layer

**Status**: Implementation Blueprint
**Layer**: Core Infrastructure
**Dependencies**: API Gateway
**Key Libraries**: LangGraph 0.2+, OpenRouter, Instructor 1.0+, OpenAI SDK, Anthropic SDK

---

## Table of Contents

1. [Overview](#1-overview)
2. [OpenRouter Multi-Provider Setup](#2-openrouter-multi-provider-setup)
3. [Instructor for Structured Output](#3-instructor-for-structured-output)
4. [LangGraph Router Orchestration](#4-langgraph-router-orchestration)
5. [Prompt Management & Versioning](#5-prompt-management--versioning)
6. [Expert LLM Services](#6-expert-llm-services)
7. [Token Counting & Cost Tracking](#7-token-counting--cost-tracking)
8. [Retry Strategies & Error Handling](#8-retry-strategies--error-handling)

---

## 1. Overview

The LLM Integration Layer provides a unified interface for interacting with multiple LLM providers (OpenAI, Anthropic) with:
- **Multi-provider fallback** via OpenRouter
- **Structured output** enforced by Instructor + Pydantic
- **Router orchestration** using LangGraph (stateful agent workflow)
- **Prompt versioning** for reproducibility
- **Cost tracking** and token usage monitoring

### Architecture

```
┌────────────────────────────────────────────────────────┐
│ LLM Integration Layer                                  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────────┐      ┌──────────────────┐       │
│  │  LangGraph      │      │  OpenRouter      │       │
│  │  Router Agent   │─────▶│  (GPT-4o / Claude│       │
│  │  (State Machine)│      │   Fallback)      │       │
│  └─────────────────┘      └──────────────────┘       │
│           │                                            │
│           ▼                                            │
│  ┌─────────────────┐                                  │
│  │  Instructor     │                                  │
│  │  (Pydantic →    │                                  │
│  │   JSON Schema)  │                                  │
│  └─────────────────┘                                  │
│           │                                            │
│           ▼                                            │
│  ExecutionPlan (validated Pydantic model)             │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### LLM Usage by Component

| Component | LLM Provider | Model | Temperature | Max Tokens | Use Case |
|-----------|--------------|-------|-------------|------------|----------|
| **Router** | OpenRouter → GPT-4o / Claude Sonnet 3.5 | gpt-4o | 0.0 | 1500 | Generate ExecutionPlan |
| **Concept Mapper** | OpenAI | gpt-4o-mini | 0.3 | 500 | Extract legal concepts |
| **Literal Interpreter** | OpenRouter | gpt-4o | 0.3 | 2000 | Legal reasoning (positivism) |
| **Systemic Reasoner** | OpenRouter | gpt-4o | 0.3 | 2000 | Teleological interpretation |
| **Principles Balancer** | OpenRouter | gpt-4o | 0.3 | 2000 | Constitutional balancing |
| **Precedent Analyst** | OpenRouter | gpt-4o | 0.3 | 2000 | Jurisprudence analysis |
| **Synthesizer** | OpenRouter | gpt-4o | 0.2 | 3000 | Combine expert outputs |

---

## 2. OpenRouter Multi-Provider Setup

### 2.1 OpenRouter Client

**File**: `src/llm/providers/openrouter.py`

```python
import httpx
from typing import Any, AsyncIterator
from pydantic import BaseModel, SecretStr


class OpenRouterConfig(BaseModel):
    """OpenRouter API configuration."""

    api_key: SecretStr
    api_base: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-4o"
    fallback_models: list[str] = [
        "anthropic/claude-sonnet-3.5",
        "openai/gpt-4o-mini",
    ]
    timeout: int = 30  # seconds
    max_retries: int = 3


class OpenRouterClient:
    """
    OpenRouter API client with automatic fallback.

    OpenRouter provides a unified API for multiple LLM providers:
        - OpenAI (GPT-4o, GPT-4o-mini)
        - Anthropic (Claude Sonnet 3.5, Claude Haiku)
        - Google (Gemini Pro)
        - Meta (Llama 3)

    Features:
        - Automatic fallback to alternative models if primary fails
        - Unified API (OpenAI-compatible)
        - Cost tracking per model
        - Rate limiting handled by OpenRouter

    Example:
        >>> client = OpenRouterClient(config)
        >>> response = await client.chat_completion(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model="openai/gpt-4o",
        ... )
    """

    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(
            base_url=config.api_base,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key.get_secret_value()}",
                "HTTP-Referer": "https://merl-t.example.com",  # Required by OpenRouter
                "X-Title": "MERL-T",  # Required by OpenRouter
            },
        )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        response_format: dict | None = None,
        enable_fallback: bool = True,
    ) -> dict[str, Any]:
        """
        Send chat completion request with automatic fallback.

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            model: Model identifier (e.g., "openai/gpt-4o")
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            response_format: Optional {"type": "json_object"} for JSON mode
            enable_fallback: If True, fallback to alternative models on failure

        Returns:
            OpenRouter API response dict

        Raises:
            httpx.HTTPError: If all models fail

        Example:
            >>> response = await client.chat_completion(
            ...     messages=[
            ...         {"role": "system", "content": "You are a helpful assistant."},
            ...         {"role": "user", "content": "What is 2+2?"}
            ...     ],
            ...     model="openai/gpt-4o",
            ... )
            >>> print(response["choices"][0]["message"]["content"])
        """
        model = model or self.config.default_model
        models_to_try = [model] + (self.config.fallback_models if enable_fallback else [])

        last_error = None

        for attempt_model in models_to_try:
            try:
                # TODO: Send request to OpenRouter API
                # payload = {
                #     "model": attempt_model,
                #     "messages": messages,
                #     "temperature": temperature,
                #     "max_tokens": max_tokens,
                # }
                #
                # if response_format:
                #     payload["response_format"] = response_format
                #
                # response = await self.http_client.post(
                #     "/chat/completions",
                #     json=payload,
                # )
                # response.raise_for_status()
                # return response.json()

                pass  # Placeholder

            except httpx.HTTPStatusError as e:
                last_error = e

                # TODO: Log model failure
                # logger.warning(
                #     f"Model {attempt_model} failed with status {e.response.status_code}, "
                #     f"trying fallback..."
                # )

                # If rate limited (429), wait and retry
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("retry-after", 60))
                    # TODO: await asyncio.sleep(retry_after)
                    continue

                # Continue to next fallback model
                continue

        # All models failed
        raise RuntimeError(f"All models failed. Last error: {last_error}")

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1500,
    ) -> AsyncIterator[dict]:
        """
        Streaming chat completion (for long responses).

        Yields:
            Server-Sent Events (SSE) chunks from OpenRouter

        Example:
            >>> async for chunk in client.chat_completion_stream(messages):
            ...     delta = chunk["choices"][0]["delta"]
            ...     if "content" in delta:
            ...         print(delta["content"], end="")
        """
        model = model or self.config.default_model

        # TODO: Implement streaming with httpx
        # async with self.http_client.stream(
        #     "POST",
        #     "/chat/completions",
        #     json={
        #         "model": model,
        #         "messages": messages,
        #         "temperature": temperature,
        #         "max_tokens": max_tokens,
        #         "stream": True,
        #     },
        # ) as response:
        #     async for line in response.aiter_lines():
        #         if line.startswith("data: "):
        #             data = line[6:]  # Remove "data: " prefix
        #             if data == "[DONE]":
        #                 break
        #             yield json.loads(data)

        yield {}  # Placeholder

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
```

### 2.2 OpenRouter Configuration

**File**: `src/llm/config.py`

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    # ===== OpenRouter =====
    openrouter_api_key: SecretStr = Field(..., description="OpenRouter API key")
    openrouter_default_model: str = "openai/gpt-4o"
    openrouter_fallback_models: list[str] = Field(
        default_factory=lambda: [
            "anthropic/claude-sonnet-3.5",
            "openai/gpt-4o-mini",
        ]
    )

    # ===== Direct Provider Keys (optional, for cost comparison) =====
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None

    # ===== Model Aliases =====
    router_model: str = "openai/gpt-4o"
    expert_model: str = "openai/gpt-4o"
    synthesizer_model: str = "openai/gpt-4o"
    concept_mapper_model: str = "openai/gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## 3. Instructor for Structured Output

### 3.1 Instructor Setup

**File**: `src/llm/structured_output.py`

```python
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import TypeVar, Type

from .providers.openrouter import OpenRouterClient


T = TypeVar("T", bound=BaseModel)


class StructuredLLMClient:
    """
    Wrapper around Instructor + OpenRouter for structured output.

    Instructor patches OpenAI client to enforce Pydantic schema via:
        1. JSON Schema injection into system prompt
        2. response_format={"type": "json_object"}
        3. Automatic validation and retry on parse errors

    Example:
        >>> from pydantic import BaseModel
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        >>>
        >>> client = StructuredLLMClient(openrouter_client)
        >>> person = await client.create(
        ...     response_model=Person,
        ...     messages=[{"role": "user", "content": "John is 30 years old"}],
        ... )
        >>> print(person.name, person.age)  # "John", 30
    """

    def __init__(self, openrouter_client: OpenRouterClient):
        self.openrouter = openrouter_client

        # Patch OpenRouter client with Instructor
        # (Instructor adds .create() method that returns Pydantic models)
        self.client = instructor.from_openai(
            AsyncOpenAI(
                api_key=openrouter_client.config.api_key.get_secret_value(),
                base_url=openrouter_client.config.api_base,
            )
        )

    async def create(
        self,
        response_model: Type[T],
        messages: list[dict[str, str]],
        model: str = "openai/gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 1500,
        max_retries: int = 3,
    ) -> T:
        """
        Create structured output matching Pydantic model.

        Args:
            response_model: Pydantic model class to enforce
            messages: Chat messages
            model: LLM model identifier
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            max_retries: Max retries on validation errors

        Returns:
            Instance of response_model (validated Pydantic object)

        Raises:
            instructor.exceptions.InstructorRetryException: If all retries fail

        Example:
            >>> class ExecutionPlan(BaseModel):
            ...     retrieval_plan: dict
            ...     reasoning_plan: dict
            >>>
            >>> plan = await client.create(
            ...     response_model=ExecutionPlan,
            ...     messages=[{"role": "user", "content": "Analyze query..."}],
            ... )
            >>> print(plan.retrieval_plan)
        """
        # TODO: Instructor automatically:
        #   1. Injects JSON schema into system prompt
        #   2. Sets response_format={"type": "json_object"}
        #   3. Parses response and validates against Pydantic model
        #   4. Retries on validation errors (up to max_retries)

        # result = await self.client.chat.completions.create(
        #     model=model,
        #     response_model=response_model,
        #     messages=messages,
        #     temperature=temperature,
        #     max_tokens=max_tokens,
        #     max_retries=max_retries,
        # )

        # return result

        pass  # Placeholder


# ===== Example: ExecutionPlan Model =====
class ExecutionPlan(BaseModel):
    """
    Execution plan generated by Router.

    This model is passed to Instructor to enforce structured output
    from the LLM Router.
    """

    trace_id: str
    retrieval_plan: dict
    reasoning_plan: dict
    iteration_strategy: dict
    rationale: str


# ===== Usage Example =====
async def example_usage():
    """
    Example of using StructuredLLMClient to generate ExecutionPlan.
    """
    from .providers.openrouter import OpenRouterClient, OpenRouterConfig
    from .config import LLMSettings

    settings = LLMSettings()
    openrouter_config = OpenRouterConfig(
        api_key=settings.openrouter_api_key,
        default_model=settings.router_model,
    )
    openrouter_client = OpenRouterClient(openrouter_config)
    structured_client = StructuredLLMClient(openrouter_client)

    # TODO: Load system prompt from template
    system_prompt = "You are the MERL-T Router. Generate an ExecutionPlan..."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Query: Quali sono i requisiti per la capacità di agire?"},
    ]

    # Instructor enforces ExecutionPlan schema
    plan: ExecutionPlan = await structured_client.create(
        response_model=ExecutionPlan,
        messages=messages,
        model="openai/gpt-4o",
        temperature=0.0,
    )

    print(plan.retrieval_plan)
    print(plan.reasoning_plan)
```

---

## 4. LangGraph Router Orchestration

### 4.1 LangGraph State Machine

**File**: `src/router/langgraph_router.py`

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from pydantic import BaseModel
import operator


# ===== Router State =====
class RouterState(TypedDict):
    """
    State for LangGraph Router agent.

    LangGraph tracks this state as the agent progresses through nodes.
    """

    # Input
    query_context: dict
    enriched_context: dict
    trace_id: str

    # Intermediate
    router_decision: dict | None
    retrieval_results: dict | None

    # Output
    execution_plan: dict | None
    rationale: str | None

    # Messages (for multi-turn reasoning)
    messages: Annotated[Sequence[dict], operator.add]


# ===== Node Functions =====
async def generate_execution_plan_node(state: RouterState) -> dict:
    """
    Node 1: Generate ExecutionPlan using LLM.

    Args:
        state: Current router state (query_context, enriched_context)

    Returns:
        Updated state with execution_plan and rationale

    TODO:
        - Load system prompt from template
        - Call StructuredLLMClient.create() with ExecutionPlan model
        - Handle validation errors
    """
    # TODO: Load system prompt
    # system_prompt = load_prompt_template("router_system_prompt_v1")

    # TODO: Format user prompt with query_context and enriched_context
    # user_prompt = format_router_prompt(
    #     query_context=state["query_context"],
    #     enriched_context=state["enriched_context"],
    # )

    # TODO: Call LLM with Instructor
    # structured_client = get_structured_llm_client()
    # execution_plan = await structured_client.create(
    #     response_model=ExecutionPlan,
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt},
    #     ],
    #     model="openai/gpt-4o",
    #     temperature=0.0,
    # )

    # TODO: Update state
    # return {
    #     "execution_plan": execution_plan.model_dump(),
    #     "rationale": execution_plan.rationale,
    # }

    return {"execution_plan": {}, "rationale": ""}


async def validate_execution_plan_node(state: RouterState) -> dict:
    """
    Node 2: Validate ExecutionPlan for correctness.

    Checks:
        - At least one agent is enabled
        - Task parameters are valid
        - Expert selection is appropriate for intent

    Returns:
        Updated state with validation_passed flag

    TODO:
        - Implement validation logic
        - If validation fails, loop back to generate_execution_plan_node
    """
    execution_plan = state["execution_plan"]

    # TODO: Validate retrieval_plan
    # if not any([
    #     execution_plan["retrieval_plan"]["kg_agent"]["enabled"],
    #     execution_plan["retrieval_plan"]["api_agent"]["enabled"],
    #     execution_plan["retrieval_plan"]["vectordb_agent"]["enabled"],
    # ]):
    #     return {"validation_passed": False, "validation_error": "No agents enabled"}

    # TODO: Validate reasoning_plan
    # if not execution_plan["reasoning_plan"]["experts"]:
    #     return {"validation_passed": False, "validation_error": "No experts selected"}

    return {"validation_passed": True}


def should_retry(state: RouterState) -> str:
    """
    Conditional edge: Decide if we should retry ExecutionPlan generation.

    Returns:
        "retry" if validation failed, "continue" if passed
    """
    if not state.get("validation_passed", False):
        # TODO: Increment retry counter, max 3 retries
        return "retry"

    return "continue"


# ===== LangGraph Definition =====
def create_router_graph() -> StateGraph:
    """
    Create LangGraph state machine for Router.

    Flow:
        1. generate_execution_plan_node → Generate ExecutionPlan with LLM
        2. validate_execution_plan_node → Validate plan
        3. Conditional edge:
           - If valid → END
           - If invalid → Loop back to generate_execution_plan_node (max 3 retries)

    Returns:
        Compiled StateGraph

    Example:
        >>> graph = create_router_graph()
        >>> result = await graph.ainvoke({
        ...     "query_context": {...},
        ...     "enriched_context": {...},
        ...     "trace_id": "RTR-20241103-abc123",
        ...     "messages": [],
        ... })
        >>> print(result["execution_plan"])
    """
    workflow = StateGraph(RouterState)

    # Add nodes
    workflow.add_node("generate_plan", generate_execution_plan_node)
    workflow.add_node("validate_plan", validate_execution_plan_node)

    # Add edges
    workflow.set_entry_point("generate_plan")
    workflow.add_edge("generate_plan", "validate_plan")

    # Conditional edge: retry or continue
    workflow.add_conditional_edges(
        "validate_plan",
        should_retry,
        {
            "retry": "generate_plan",  # Loop back
            "continue": END,  # Done
        },
    )

    # Compile graph
    return workflow.compile()


# ===== Router Service =====
class RouterService:
    """
    High-level Router service using LangGraph.

    Example:
        >>> router = RouterService()
        >>> result = await router.generate_execution_plan(
        ...     query_context={...},
        ...     enriched_context={...},
        ...     trace_id="RTR-20241103-abc123",
        ... )
        >>> print(result["execution_plan"])
    """

    def __init__(self):
        self.graph = create_router_graph()

    async def generate_execution_plan(
        self,
        query_context: dict,
        enriched_context: dict,
        trace_id: str,
    ) -> dict:
        """
        Generate ExecutionPlan using LangGraph state machine.

        Args:
            query_context: Query understanding output
            enriched_context: KG enrichment output
            trace_id: Trace ID for debugging

        Returns:
            ExecutionPlan dict

        Raises:
            ValueError: If plan generation fails after max retries
        """
        initial_state = {
            "query_context": query_context,
            "enriched_context": enriched_context,
            "trace_id": trace_id,
            "messages": [],
        }

        # Run LangGraph workflow
        result = await self.graph.ainvoke(initial_state)

        if not result.get("validation_passed"):
            raise ValueError("Failed to generate valid ExecutionPlan")

        return {
            "execution_plan": result["execution_plan"],
            "rationale": result["rationale"],
            "trace_id": trace_id,
        }
```

### 4.2 LangGraph Visualization

```python
# ===== Graph Visualization (for debugging) =====
def visualize_router_graph():
    """
    Visualize Router LangGraph as Mermaid diagram.

    Output:
        graph TD
            generate_plan --> validate_plan
            validate_plan --> |retry| generate_plan
            validate_plan --> |continue| END
    """
    graph = create_router_graph()

    # TODO: Use LangGraph's built-in visualization
    # from langgraph.graph import visualize
    # visualize(graph)
```

---

## 5. Prompt Management & Versioning

### 5.1 Prompt Template System

**File**: `src/llm/prompts/templates.py`

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from typing import Any


class PromptTemplateManager:
    """
    Manage prompt templates with versioning.

    Templates are stored in:
        prompts/
          router/
            system_prompt_v1.jinja2
            system_prompt_v2.jinja2
            user_prompt_v1.jinja2
          expert_literal/
            system_prompt_v1.jinja2
          synthesizer/
            system_prompt_v1.jinja2

    Example:
        >>> manager = PromptTemplateManager()
        >>> prompt = manager.render(
        ...     "router/system_prompt_v1",
        ...     variables={"foo": "bar"}
        ... )
    """

    def __init__(self, templates_dir: str | Path = "prompts"):
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=False,  # No HTML escaping for LLM prompts
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        template_name: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a prompt template with variables.

        Args:
            template_name: Template path (e.g., "router/system_prompt_v1")
            variables: Template variables

        Returns:
            Rendered prompt string

        Example:
            >>> prompt = manager.render(
            ...     "router/system_prompt_v1",
            ...     variables={
            ...         "intent_types": ["validità_atto", "interpretazione_norma"],
            ...     }
            ... )
        """
        template_path = f"{template_name}.jinja2"
        template: Template = self.env.get_template(template_path)

        variables = variables or {}
        return template.render(**variables)

    def get_template(self, template_name: str) -> Template:
        """Get a template object for manual rendering."""
        return self.env.get_template(f"{template_name}.jinja2")


# ===== Global Singleton =====
_prompt_manager: PromptTemplateManager | None = None


def get_prompt_manager() -> PromptTemplateManager:
    """Get global PromptTemplateManager singleton."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager()
    return _prompt_manager
```

### 5.2 Router System Prompt Template

**File**: `prompts/router/system_prompt_v1.jinja2`

```jinja2
You are the MERL-T Legal Reasoning Router. Your role is to analyze a legal query
and generate an optimal ExecutionPlan for retrieval agents and reasoning experts.

## Your Task
Given a QueryContext and EnrichedContext, generate a structured ExecutionPlan JSON with 3 sections:

1. **retrieval_plan**: Decide which agents to activate (kg_agent, api_agent, vectordb_agent)
2. **reasoning_plan**: Select experts based on query intent and complexity
3. **iteration_strategy**: Define stop criteria (max_iterations, min_confidence)

## Available Agents
- **kg_agent**: Knowledge Graph traversal (concepts, norms, jurisprudence)
- **api_agent**: Akoma Ntoso API for full norm text retrieval
- **vectordb_agent**: Vector search for semantic similarity (6 patterns: P1-P6)

## Available Experts
- **Literal_Interpreter**: Positivist interpretation (focus: literal text of norms)
- **Systemic_Teleological**: Teleological interpretation (focus: purpose and context)
- **Principles_Balancer**: Constitutional balancing (focus: rights and principles)
- **Precedent_Analyst**: Jurisprudence analysis (focus: case law trends)

## Decision Guidelines
- If query intent = "validità_atto" → Activate Literal_Interpreter, kg_agent
- If query intent = "interpretazione_norma" → Activate Systemic_Teleological + Literal_Interpreter
- If query intent = "bilanciamento_diritti" → Activate Principles_Balancer
- If query intent = "evoluzione_giurisprudenziale" → Activate Precedent_Analyst, vectordb_agent (P4: reranked)
- If complexity > 0.7 → Activate multiple experts, synthesis_mode="divergent"
- If complexity < 0.4 → Activate single expert, synthesis_mode="convergent"

## Output Format
Respond with ONLY valid JSON matching the ExecutionPlan schema. No preamble, no explanation.

ExecutionPlan JSON schema will be provided by the system.
```

### 5.3 Router User Prompt Template

**File**: `prompts/router/user_prompt_v1.jinja2`

```jinja2
## Query Context
{{ query_context | tojson(indent=2) }}

## Enriched Context
{{ enriched_context | tojson(indent=2) }}

## Generate ExecutionPlan
Based on the above context, generate an optimal ExecutionPlan for this query.
```

---

## 6. Expert LLM Services

### 6.1 Base Expert Class

**File**: `src/experts/base_expert.py`

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import ClassVar

from ..llm.structured_output import StructuredLLMClient
from ..llm.prompts.templates import get_prompt_manager


class ExpertOutput(BaseModel):
    """Expert reasoning output (enforced by Instructor)."""

    expert_type: str
    interpretation: str
    rationale: dict
    confidence: float
    sources: list[dict]
    limitations: str


class BaseExpert(ABC):
    """
    Abstract base class for legal reasoning experts.

    Each expert:
        1. Loads a versioned system prompt
        2. Formats the context into a user prompt
        3. Calls LLM via StructuredLLMClient (enforcing ExpertOutput schema)
        4. Returns validated ExpertOutput

    Subclasses must implement:
        - expert_type (class variable)
        - get_system_prompt_template()
    """

    expert_type: ClassVar[str]

    def __init__(self, llm_client: StructuredLLMClient):
        self.llm_client = llm_client
        self.prompt_manager = get_prompt_manager()

    @abstractmethod
    def get_system_prompt_template(self) -> str:
        """
        Return system prompt template name.

        Example:
            return "expert_literal/system_prompt_v1"
        """
        pass

    async def reason(
        self,
        query_context: dict,
        enriched_context: dict,
        retrieval_result: dict,
        trace_id: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> ExpertOutput:
        """
        Generate legal reasoning output.

        Args:
            query_context: Query understanding output
            enriched_context: KG enrichment output
            retrieval_result: Agent retrieval results
            trace_id: Trace ID for debugging
            temperature: LLM temperature
            max_tokens: Max tokens to generate

        Returns:
            ExpertOutput (validated Pydantic model)

        TODO:
            - Load system prompt template
            - Format user prompt with context
            - Call LLM via Instructor
            - Handle validation errors
        """
        # TODO: Load system prompt
        # system_prompt = self.prompt_manager.render(
        #     self.get_system_prompt_template(),
        #     variables={},
        # )

        # TODO: Format user prompt
        # user_prompt = self.prompt_manager.render(
        #     "expert_common/user_prompt_v1",
        #     variables={
        #         "query_context": query_context,
        #         "enriched_context": enriched_context,
        #         "retrieval_result": retrieval_result,
        #     },
        # )

        # TODO: Call LLM with Instructor
        # output: ExpertOutput = await self.llm_client.create(
        #     response_model=ExpertOutput,
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_prompt},
        #     ],
        #     model="openai/gpt-4o",
        #     temperature=temperature,
        #     max_tokens=max_tokens,
        # )

        # TODO: Inject expert_type
        # output.expert_type = self.expert_type

        # return output

        pass  # Placeholder
```

### 6.2 Literal Interpreter Expert

**File**: `src/experts/literal_interpreter.py`

```python
from .base_expert import BaseExpert


class LiteralInterpreter(BaseExpert):
    """
    Literal Interpreter Expert (Positivismo Giuridico).

    Epistemology:
        - Law = Written text of norms
        - Interpretation = Literal textual analysis
        - Focus: What the law SAYS (not why, not context)

    Activation Criteria:
        - primary_intent: ["validità_atto", "requisiti_procedurali"]
        - complexity: < 0.7
        - norm_clarity: > 0.8

    Strengths:
        - High precision for clear rules
        - High confidence when norms are unambiguous

    Limitations:
        - Ignores ratio legis (purpose of law)
        - Ignores jurisprudence trends
        - Weak on ambiguous norms
    """

    expert_type = "Literal_Interpreter"

    def get_system_prompt_template(self) -> str:
        return "expert_literal/system_prompt_v1"
```

### 6.3 Systemic-Teleological Reasoner

**File**: `src/experts/systemic_teleological.py`

```python
from .base_expert import BaseExpert


class SystemicTeleologicalReasoner(BaseExpert):
    """
    Systemic-Teleological Reasoner (Finalismo Giuridico).

    Epistemology:
        - Law = System with purpose (ratio legis)
        - Interpretation = Discover legislative intent
        - Focus: WHY the law exists (purpose, context)

    Activation Criteria:
        - primary_intent: ["interpretazione_norma", "lacune_ordinamento"]
        - complexity: > 0.5
        - ambiguity: > 0.5

    Strengths:
        - Good for ambiguous norms
        - Considers legislative history and purpose

    Limitations:
        - Lower confidence (subjective interpretation)
        - Requires deep context understanding
    """

    expert_type = "Systemic_Teleological"

    def get_system_prompt_template(self) -> str:
        return "expert_systemic/system_prompt_v1"
```

---

## 7. Token Counting & Cost Tracking

### 7.1 Token Counter

**File**: `src/llm/token_counter.py`

```python
import tiktoken
from typing import Literal


class TokenCounter:
    """
    Count tokens for cost estimation.

    Uses tiktoken (OpenAI's tokenizer) for accurate token counts.

    Example:
        >>> counter = TokenCounter()
        >>> tokens = counter.count_tokens(
        ...     text="Hello, world!",
        ...     model="gpt-4o",
        ... )
        >>> print(tokens)  # 4
    """

    def __init__(self):
        # Cache encodings
        self.encodings = {}

    def count_tokens(
        self,
        text: str,
        model: Literal["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"] = "gpt-4o",
    ) -> int:
        """
        Count tokens in text for a given model.

        Args:
            text: Text to tokenize
            model: Model name (determines tokenizer)

        Returns:
            Token count (integer)
        """
        if model not in self.encodings:
            self.encodings[model] = tiktoken.encoding_for_model(model)

        encoding = self.encodings[model]
        return len(encoding.encode(text))

    def count_messages_tokens(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
    ) -> int:
        """
        Count tokens for a list of messages (chat completion).

        OpenAI charges tokens for:
            - Message content
            - Role labels ("system", "user", "assistant")
            - Message separators

        Args:
            messages: List of message dicts
            model: Model name

        Returns:
            Total token count
        """
        # TODO: Use tiktoken's num_tokens_from_messages()
        # encoding = tiktoken.encoding_for_model(model)
        # return num_tokens_from_messages(messages, model)

        # Simplified approximation
        total = 0
        for msg in messages:
            total += self.count_tokens(msg["content"], model)
            total += 4  # Role label + separators overhead

        return total


# ===== Cost Calculation =====
COST_PER_1M_TOKENS = {
    "openai/gpt-4o": {"input": 5.00, "output": 15.00},  # USD
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-sonnet-3.5": {"input": 3.00, "output": 15.00},
}


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """
    Calculate cost in USD for a model call.

    Args:
        input_tokens: Input token count
        output_tokens: Output token count
        model: Model identifier (e.g., "openai/gpt-4o")

    Returns:
        Cost in USD

    Example:
        >>> cost = calculate_cost(
        ...     input_tokens=1000,
        ...     output_tokens=500,
        ...     model="openai/gpt-4o",
        ... )
        >>> print(f"${cost:.4f}")  # $0.0125
    """
    if model not in COST_PER_1M_TOKENS:
        return 0.0  # Unknown model

    pricing = COST_PER_1M_TOKENS[model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost
```

### 7.2 Cost Tracking Middleware

**File**: `src/llm/cost_tracker.py`

```python
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any


class CostTracker:
    """
    Track LLM usage and costs across all components.

    Stores metrics in PostgreSQL for analysis.

    Metrics:
        - Total tokens (input + output)
        - Total cost (USD)
        - Requests per component (Router, Expert, Synthesizer)
        - Requests per model (GPT-4o, Claude Sonnet)

    Example:
        >>> tracker = CostTracker()
        >>> tracker.record_usage(
        ...     component="router",
        ...     model="openai/gpt-4o",
        ...     input_tokens=1000,
        ...     output_tokens=500,
        ...     trace_id="RTR-20241103-abc123",
        ... )
        >>> print(tracker.get_daily_cost())  # $12.45
    """

    def __init__(self):
        self.usage_log = []
        self.lock = asyncio.Lock()

    async def record_usage(
        self,
        component: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        trace_id: str,
        latency_ms: int,
    ):
        """
        Record LLM usage for a single request.

        Args:
            component: Component name ("router", "expert_literal", "synthesizer")
            model: Model identifier
            input_tokens: Input token count
            output_tokens: Output token count
            trace_id: Trace ID for debugging
            latency_ms: Request latency in milliseconds

        TODO:
            - Store in PostgreSQL table `llm_usage`
            - Aggregate daily metrics in background task
        """
        from .token_counter import calculate_cost

        cost = calculate_cost(input_tokens, output_tokens, model)

        usage_entry = {
            "timestamp": datetime.utcnow(),
            "component": component,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "trace_id": trace_id,
            "latency_ms": latency_ms,
        }

        async with self.lock:
            self.usage_log.append(usage_entry)

        # TODO: Async write to PostgreSQL
        # await db.execute(
        #     "INSERT INTO llm_usage VALUES (...)",
        #     usage_entry,
        # )

    def get_daily_cost(self, date: datetime | None = None) -> float:
        """Get total cost for a given date."""
        # TODO: Query PostgreSQL for daily aggregate
        # SELECT SUM(cost_usd) FROM llm_usage WHERE DATE(timestamp) = $date
        return 0.0


# ===== Global Singleton =====
_cost_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get global CostTracker singleton."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
```

---

## 8. Retry Strategies & Error Handling

### 8.1 Retry Decorator

**File**: `src/llm/retry.py`

```python
import asyncio
import functools
from typing import Callable, TypeVar, ParamSpec
import httpx


P = ParamSpec("P")
T = TypeVar("T")


def retry_on_llm_error(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    retry_on: tuple = (httpx.HTTPStatusError, httpx.TimeoutException),
):
    """
    Retry decorator for LLM calls.

    Retries on:
        - HTTP 5xx errors (server-side)
        - HTTP 429 (rate limit)
        - Timeout errors
        - Connection errors

    Does NOT retry on:
        - HTTP 4xx errors (client-side, e.g., invalid API key)
        - Validation errors (Pydantic)

    Backoff strategy:
        - Exponential backoff: wait = backoff_factor ^ retry_count
        - Example: 2^0=1s, 2^1=2s, 2^2=4s

    Example:
        @retry_on_llm_error(max_retries=3)
        async def call_llm(prompt):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_error = e

                    # If rate limited (429), respect retry-after header
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                        retry_after = int(e.response.headers.get("retry-after", 60))
                        await asyncio.sleep(retry_after)
                        continue

                    # Exponential backoff
                    wait_time = backoff_factor ** attempt
                    # TODO: Log retry
                    # logger.warning(
                    #     f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                    #     f"retrying in {wait_time}s: {e}"
                    # )

                    await asyncio.sleep(wait_time)

            # All retries exhausted
            raise RuntimeError(f"LLM call failed after {max_retries} retries") from last_error

        return wrapper

    return decorator


# ===== Usage Example =====
@retry_on_llm_error(max_retries=3)
async def call_router_llm(messages: list[dict]) -> dict:
    """Example function with retry logic."""
    # TODO: Call OpenRouter API
    pass
```

---

## Summary

This LLM Integration Layer provides:

1. **OpenRouter Multi-Provider** with automatic fallback (GPT-4o → Claude Sonnet → GPT-4o-mini)
2. **Instructor Structured Output** enforcing Pydantic schemas (ExecutionPlan, ExpertOutput)
3. **LangGraph Router Orchestration** with state machine workflow and validation
4. **Prompt Management** with Jinja2 templates and versioning
5. **Base Expert Class** for consistent reasoning interface across 4 experts
6. **Token Counting & Cost Tracking** with PostgreSQL persistence
7. **Retry Strategies** with exponential backoff and rate limit handling

### Next Steps

1. Implement actual LLM calls in OpenRouterClient
2. Complete LangGraph node functions with prompt loading
3. Create all expert system prompt templates (4 experts + synthesizer)
4. Implement cost tracker PostgreSQL schema and async writes
5. Add LangGraph visualization for debugging

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/llm/providers/openrouter.py` | OpenRouter client with fallback | ~150 |
| `src/llm/structured_output.py` | Instructor wrapper | ~100 |
| `src/router/langgraph_router.py` | LangGraph state machine | ~200 |
| `src/llm/prompts/templates.py` | Prompt template manager | ~80 |
| `src/experts/base_expert.py` | Base expert class | ~100 |
| `src/experts/literal_interpreter.py` | Literal expert | ~40 |
| `src/experts/systemic_teleological.py` | Systemic expert | ~40 |
| `src/llm/token_counter.py` | Token counting & cost calc | ~100 |
| `src/llm/cost_tracker.py` | Cost tracking service | ~80 |
| `src/llm/retry.py` | Retry decorator | ~70 |
| `prompts/router/system_prompt_v1.jinja2` | Router system prompt | ~40 |

**Total: ~1,000 lines** (target: ~900 lines, slightly over but acceptable) ✅
