"""
Orchestration Configuration Loader
===================================

Pydantic models for loading and validating orchestration_config.yaml

Features:
- Type-safe configuration with validation
- Environment variable expansion (${VAR:-default})
- Hot-reloadable configuration
- Easy experimentation with different scenarios

Usage:
    from backend.orchestration.config.orchestration_config import load_orchestration_config

    config = load_orchestration_config()

    # Access router config
    print(config.llm_router.model)  # google/gemini-2.5-flash

    # Check if expert enabled
    if config.reasoning_experts.literal_interpreter.enabled:
        ...
"""

import os
import re
from typing import Dict, Any, List, Optional, Literal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


# ==============================================
# LLM Router Configuration
# ==============================================

class LLMRouterConfig(BaseModel):
    """LLM Router configuration"""
    provider: str = Field(default="openrouter")
    model: str = Field(default="google/gemini-2.5-flash")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0)
    timeout_seconds: int = Field(default=10, gt=0)

    prompt_template: str = Field(default="router_v1")
    structured_output: bool = Field(default=True)
    fallback_strategy: str = Field(default="default_plan")

    log_decisions: bool = Field(default=True)
    log_rationale: bool = Field(default=True)


# ==============================================
# Retrieval Agents Configuration
# ==============================================

class KGAgentConfig(BaseModel):
    """KG Agent (Neo4j) configuration"""
    enabled: bool = Field(default=True)
    max_results: int = Field(default=50, gt=0)
    task_types: List[str] = Field(default_factory=lambda: [
        "expand_related_concepts",
        "hierarchical_traversal",
        "jurisprudence_lookup",
        "temporal_evolution"
    ])
    cypher_timeout_ms: int = Field(default=3000, gt=0)


class APIAgentSourceConfig(BaseModel):
    """Configuration for a single API source"""
    enabled: bool = Field(default=True)
    base_url: str


class APIAgentConfig(BaseModel):
    """API Agent configuration"""
    enabled: bool = Field(default=True)
    max_results: int = Field(default=20, gt=0)
    cache_ttl_seconds: int = Field(default=86400, gt=0)
    sources: Dict[str, APIAgentSourceConfig] = Field(default_factory=dict)
    timeout_per_source_seconds: int = Field(default=3, gt=0)


class VectorDBAgentConfig(BaseModel):
    """VectorDB Agent (Qdrant) configuration"""
    enabled: bool = Field(default=True)
    max_results: int = Field(default=10, gt=0)
    search_patterns: List[str] = Field(default_factory=lambda: [
        "semantic", "hybrid", "filtered", "reranked"
    ])
    default_pattern: str = Field(default="hybrid")
    embedding_model: str = Field(default="local")  # local or voyage
    rerank_top_k: int = Field(default=5, gt=0)


class RetrievalAgentsConfig(BaseModel):
    """Configuration for all retrieval agents"""
    execution_mode: Literal["parallel", "sequential"] = Field(default="parallel")
    timeout_per_agent_seconds: int = Field(default=5, gt=0)

    kg_agent: KGAgentConfig = Field(default_factory=KGAgentConfig)
    api_agent: APIAgentConfig = Field(default_factory=APIAgentConfig)
    vectordb_agent: VectorDBAgentConfig = Field(default_factory=VectorDBAgentConfig)


# ==============================================
# Reasoning Experts Configuration
# ==============================================

class ExpertActivationCriteria(BaseModel):
    """Criteria for activating an expert"""
    intents: List[str] = Field(default_factory=list)
    complexity: List[str] = Field(default_factory=list)
    requires_interpretation: Optional[bool] = None
    requires_balancing: Optional[bool] = None
    requires_case_law: Optional[bool] = None
    constitutional_issue: Optional[bool] = None


class ReasoningExpertConfig(BaseModel):
    """Configuration for a single reasoning expert"""
    enabled: bool = Field(default=True)
    provider: str = Field(default="openrouter")
    model: str = Field(default="google/gemini-2.5-flash")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0)
    prompt_template: str
    epistemology: str
    activation_criteria: ExpertActivationCriteria = Field(
        default_factory=ExpertActivationCriteria
    )


class ReasoningExpertsConfig(BaseModel):
    """Configuration for all reasoning experts"""
    execution_mode: Literal["parallel", "sequential"] = Field(default="parallel")
    timeout_per_expert_seconds: int = Field(default=10, gt=0)

    literal_interpreter: ReasoningExpertConfig
    systemic_teleological: ReasoningExpertConfig
    principles_balancer: ReasoningExpertConfig
    precedent_analyst: ReasoningExpertConfig


# ==============================================
# Synthesizer Configuration
# ==============================================

class ConvergentSynthesisConfig(BaseModel):
    """Convergent synthesis configuration"""
    min_consensus_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    source_attribution: bool = Field(default=True)
    confidence_weighting: bool = Field(default=True)


class DivergentSynthesisConfig(BaseModel):
    """Divergent synthesis configuration"""
    preserve_all_perspectives: bool = Field(default=True)
    conflict_highlighting: bool = Field(default=True)
    epistemic_humility: bool = Field(default=True)


class SynthesizerConfig(BaseModel):
    """Synthesizer configuration"""
    provider: str = Field(default="openrouter")
    model: str = Field(default="google/gemini-2.5-flash")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=3000, gt=0)
    timeout_seconds: int = Field(default=8, gt=0)

    default_mode: Literal["convergent", "divergent"] = Field(default="convergent")
    mode_selection_strategy: Literal["llm", "rule_based", "fixed"] = Field(default="llm")

    convergent: ConvergentSynthesisConfig = Field(default_factory=ConvergentSynthesisConfig)
    divergent: DivergentSynthesisConfig = Field(default_factory=DivergentSynthesisConfig)


# ==============================================
# Iteration Configuration
# ==============================================

class StopCriteriaConfig(BaseModel):
    """Stop criteria for iteration controller"""
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    expert_consensus_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    quality_evaluation: bool = Field(default=True)
    quality_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    max_iterations_reached: bool = Field(default=True)
    timeout_exceeded: bool = Field(default=True)
    no_improvement: bool = Field(default=True)


class IterationStrategyConfig(BaseModel):
    """Iteration strategy configuration"""
    refine_on_low_confidence: bool = Field(default=True)
    refine_on_disagreement: bool = Field(default=True)
    refine_on_missing_info: bool = Field(default=True)


class IterationConfig(BaseModel):
    """Iteration controller configuration"""
    enabled: bool = Field(default=True)
    max_iterations: int = Field(default=3, ge=1, le=10)
    timeout_per_iteration_seconds: int = Field(default=30, gt=0)

    stop_criteria: StopCriteriaConfig = Field(default_factory=StopCriteriaConfig)
    iteration_strategy: IterationStrategyConfig = Field(default_factory=IterationStrategyConfig)


# ==============================================
# Embeddings Configuration
# ==============================================

class LocalEmbeddingsConfig(BaseModel):
    """Local embeddings (E5) configuration"""
    model_name: str = Field(default="sentence-transformers/multilingual-e5-large")
    device: Literal["cpu", "cuda"] = Field(default="cpu")
    batch_size: int = Field(default=32, gt=0)
    normalize_embeddings: bool = Field(default=True)


class VoyageEmbeddingsConfig(BaseModel):
    """Voyage AI embeddings configuration"""
    enabled: bool = Field(default=False)
    api_key: str = Field(default="")
    model: str = Field(default="voyage-multilingual-2")
    input_type: Literal["document", "query"] = Field(default="document")


class EmbeddingsConfig(BaseModel):
    """Embeddings configuration"""
    provider: Literal["local", "voyage"] = Field(default="local")
    local: LocalEmbeddingsConfig = Field(default_factory=LocalEmbeddingsConfig)
    voyage: VoyageEmbeddingsConfig = Field(default_factory=VoyageEmbeddingsConfig)


# ==============================================
# Workflow Configuration
# ==============================================

class ParallelExecutionConfig(BaseModel):
    """Parallel execution configuration"""
    agents: bool = Field(default=True)
    experts: bool = Field(default=True)


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration"""
    retry_on_failure: bool = Field(default=True)
    max_retries: int = Field(default=2, ge=0)
    fallback_to_degraded: bool = Field(default=True)


class WorkflowConfig(BaseModel):
    """LangGraph workflow configuration"""
    state_persistence: bool = Field(default=False)
    trace_execution: bool = Field(default=True)
    parallel_execution: ParallelExecutionConfig = Field(default_factory=ParallelExecutionConfig)
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)


# ==============================================
# Performance Configuration
# ==============================================

class TargetLatenciesConfig(BaseModel):
    """Target latencies for components (seconds)"""
    router: float = Field(default=2.0, gt=0)
    kg_agent: float = Field(default=0.1, gt=0)
    api_agent: float = Field(default=0.2, gt=0)
    vectordb_agent: float = Field(default=0.3, gt=0)
    expert: float = Field(default=3.0, gt=0)
    synthesizer: float = Field(default=2.0, gt=0)
    total_single_iteration: float = Field(default=10.0, gt=0)


class PerformanceConfig(BaseModel):
    """Performance monitoring configuration"""
    target_latencies: TargetLatenciesConfig = Field(default_factory=TargetLatenciesConfig)
    track_metrics: bool = Field(default=True)
    log_traces: bool = Field(default=True)
    alert_on_timeout: bool = Field(default=True)


# ==============================================
# Main Orchestration Configuration
# ==============================================

class OrchestrationConfig(BaseModel):
    """Complete orchestration configuration"""
    llm_router: LLMRouterConfig = Field(default_factory=LLMRouterConfig)
    retrieval_agents: RetrievalAgentsConfig = Field(default_factory=RetrievalAgentsConfig)
    reasoning_experts: ReasoningExpertsConfig
    synthesizer: SynthesizerConfig = Field(default_factory=SynthesizerConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)


# ==============================================
# Configuration Loading Functions
# ==============================================

def _expand_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand environment variables in configuration.

    Supports syntax:
    - ${VAR} - Environment variable (error if not set)
    - ${VAR:-default} - Environment variable with default value

    Example:
        model: ${ROUTER_MODEL:-google/gemini-2.5-flash}
        → If ROUTER_MODEL not set, uses google/gemini-2.5-flash
    """
    env_var_pattern = re.compile(r'\$\{([^}^{]+)\}')

    def expand_value(value: Any) -> Any:
        if isinstance(value, str):
            def replace_env_var(match):
                var_expr = match.group(1)

                # Check for default value syntax: VAR:-default
                if ':-' in var_expr:
                    var_name, default_value = var_expr.split(':-', 1)
                    return os.environ.get(var_name.strip(), default_value)
                else:
                    var_name = var_expr.strip()
                    if var_name in os.environ:
                        return os.environ[var_name]
                    else:
                        # No default, error
                        raise ValueError(f"Environment variable '{var_name}' not set and no default provided")

            return env_var_pattern.sub(replace_env_var, value)

        elif isinstance(value, dict):
            return {k: expand_value(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [expand_value(item) for item in value]

        else:
            return value

    return expand_value(config_dict)


def load_orchestration_config(
    config_path: Optional[Path] = None
) -> OrchestrationConfig:
    """
    Load orchestration configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        OrchestrationConfig instance

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config validation fails
    """
    if config_path is None:
        # Default path: backend/orchestration/config/orchestration_config.yaml
        config_path = Path(__file__).parent / "orchestration_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)

    # Expand environment variables
    config_dict = _expand_env_vars(config_dict)

    # Validate and create Pydantic model
    config = OrchestrationConfig(**config_dict)

    return config


# Global config cache
_global_config: Optional[OrchestrationConfig] = None


def get_orchestration_config() -> OrchestrationConfig:
    """
    Get the global orchestration configuration (cached).

    Returns:
        OrchestrationConfig instance
    """
    global _global_config

    if _global_config is None:
        _global_config = load_orchestration_config()

    return _global_config


def reload_orchestration_config() -> OrchestrationConfig:
    """
    Reload orchestration configuration from disk.

    Useful for hot-reloading during development.

    Returns:
        Fresh OrchestrationConfig instance
    """
    global _global_config
    _global_config = load_orchestration_config()
    return _global_config


# ==============================================
# Exports
# ==============================================

__all__ = [
    # Main config
    "OrchestrationConfig",

    # Loading functions
    "load_orchestration_config",
    "get_orchestration_config",
    "reload_orchestration_config",

    # Sub-configurations (for type hints)
    "LLMRouterConfig",
    "RetrievalAgentsConfig",
    "ReasoningExpertsConfig",
    "SynthesizerConfig",
    "IterationConfig",
    "EmbeddingsConfig",
    "WorkflowConfig",
    "PerformanceConfig",
]
