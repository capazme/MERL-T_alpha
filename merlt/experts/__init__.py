"""
MERL-T Experts Module
=====================

Experts sono agenti interpretativi specializzati basati sui criteri delle Preleggi.

Mapping sui canoni ermeneutici (art. 12-14 disp. prel. c.c.):
- LiteralExpert: "significato proprio delle parole" (art. 12, I)
- SystemicExpert: "connessione di esse" + storico (art. 12, I + art. 14)
- PrinciplesExpert: "intenzione del legislatore" (art. 12, II)
- PrecedentExpert: Prassi applicativa giurisprudenziale

Architettura:
    Query → ExpertRouter → [Experts] → GatingNetwork → Response
                              ↓             ↓
                          Tools      Synthesizer

Ogni Expert:
- Estende BaseExpert
- Ha tools specifici per il proprio approccio
- Produce ExpertResponse strutturata con provenance

Esempio:
    >>> from merlt.experts import LiteralExpert, ExpertContext
    >>> from merlt.tools import SemanticSearchTool
    >>>
    >>> expert = LiteralExpert(
    ...     tools=[SemanticSearchTool(retriever, embeddings)],
    ...     ai_service=openrouter_service
    ... )
    >>>
    >>> context = ExpertContext(query_text="Cos'è la legittima difesa?")
    >>> response = await expert.analyze(context)
    >>> print(response.interpretation)
"""

from merlt.experts.base import (
    BaseExpert,
    ExpertWithTools,
    ExpertContext,
    ExpertResponse,
    LegalSource,
    ReasoningStep,
    ConfidenceFactors,
)
from merlt.experts.literal import LiteralExpert
from merlt.experts.systemic import SystemicExpert
from merlt.experts.principles import PrinciplesExpert
from merlt.experts.precedent import PrecedentExpert
from merlt.experts.router import ExpertRouter, RoutingDecision
from merlt.experts.gating import GatingNetwork, AggregatedResponse
from merlt.experts.orchestrator import MultiExpertOrchestrator, OrchestratorConfig
from merlt.experts.react_mixin import ReActMixin, ReActResult, ThoughtActionObservation

__all__ = [
    # Base classes
    "BaseExpert",
    "ExpertWithTools",
    # Data classes
    "ExpertContext",
    "ExpertResponse",
    "LegalSource",
    "ReasoningStep",
    "ConfidenceFactors",
    # Experts - 4 canoni ermeneutici delle Preleggi
    "LiteralExpert",      # Art. 12, I (significato proprio)
    "SystemicExpert",     # Art. 12, I (connessione) + Art. 14 (storico)
    "PrinciplesExpert",   # Art. 12, II (intenzione legislatore)
    "PrecedentExpert",    # Prassi applicativa
    # Routing & Orchestration
    "ExpertRouter",
    "RoutingDecision",
    "GatingNetwork",
    "AggregatedResponse",
    "MultiExpertOrchestrator",
    "OrchestratorConfig",
    # ReAct Pattern
    "ReActMixin",
    "ReActResult",
    "ThoughtActionObservation",
]
