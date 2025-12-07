"""
MERL-T RLCF Framework
=====================

Reinforcement Learning from Collective Feedback per ricerca giuridica.

Componenti:
- authority: Funzioni per calcolo autorevolezza fonte
- aggregation: AggregationEngine per aggregazione feedback
- ai_service: OpenRouterService per AI responses
- models: SQLAlchemy models per RLCF data

Esempio:
    from merlt.rlcf.ai_service import OpenRouterService

    service = OpenRouterService()
    response = await service.generate(prompt="...")

Note:
    Il modulo è in fase di sviluppo. Alcuni componenti richiedono
    configurazione database (SQLAlchemy) per funzionare completamente.
"""

# Lazy imports to avoid circular dependencies and allow partial module use
# Import specific components as needed:
#   from merlt.rlcf.ai_service import OpenRouterService
#   from merlt.rlcf.aggregation import AggregationEngine

__all__ = [
    "ai_service",
    "aggregation",
    "authority",
    "models",
]
