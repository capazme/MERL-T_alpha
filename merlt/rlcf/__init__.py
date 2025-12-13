"""
MERL-T RLCF Framework
=====================

Reinforcement Learning from Collective Feedback per ricerca giuridica.

Componenti:
- authority: Funzioni per calcolo autorevolezza fonte
- aggregation: AggregationEngine per aggregazione feedback
- ai_service: OpenRouterService per AI responses
- models: SQLAlchemy models per RLCF data
- metrics: MetricsTracker per tracking LLM calls e costi
- validation: Modelli per validazione knowledge graph

Esempio:
    from merlt.rlcf.ai_service import OpenRouterService
    from merlt.rlcf.metrics import get_metrics
    from merlt.rlcf.validation import ValidationIssue, IssueType

    # AI Service
    service = OpenRouterService()
    response = await service.generate(prompt="...")

    # Metrics tracking
    metrics = get_metrics()
    metrics.record_llm_call(model="gpt-4", tokens_in=100, ...)

    # Validation
    issue = ValidationIssue(
        issue_id="dup-1",
        issue_type=IssueType.DUPLICATE,
        ...
    )

Note:
    Il modulo è in fase di sviluppo. Alcuni componenti richiedono
    configurazione database (SQLAlchemy) per funzionare completamente.
"""

# Lazy imports to avoid circular dependencies and allow partial module use
# Import specific components as needed:
#   from merlt.rlcf.ai_service import OpenRouterService
#   from merlt.rlcf.aggregation import AggregationEngine
#   from merlt.rlcf.metrics import get_metrics
#   from merlt.rlcf.validation import ValidationIssue

__all__ = [
    "ai_service",
    "aggregation",
    "authority",
    "models",
    "metrics",
    "validation",
]
