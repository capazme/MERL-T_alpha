"""
Multi-Expert Orchestrator
==========================

Orchestratore centrale per il sistema multi-expert.

Il MultiExpertOrchestrator coordina:
1. ExpertRouter: Selezione degli Expert
2. Expert: Esecuzione parallela/sequenziale
3. GatingNetwork: Aggregazione delle risposte

Pipeline completa:
    Query → Router → [Experts in parallelo] → GatingNetwork → Response

Esempio:
    >>> from merlt.experts import MultiExpertOrchestrator
    >>>
    >>> orchestrator = MultiExpertOrchestrator(ai_service=openrouter)
    >>> response = await orchestrator.process("Cos'è la legittima difesa?")
    >>> print(response.synthesis)
"""

import structlog
import asyncio
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass
from datetime import datetime

from merlt.experts.base import BaseExpert, ExpertContext, ExpertResponse
from merlt.experts.router import ExpertRouter, RoutingDecision
from merlt.experts.gating import GatingNetwork, AggregatedResponse
from merlt.experts.literal import LiteralExpert
from merlt.experts.systemic import SystemicExpert
from merlt.experts.principles import PrinciplesExpert
from merlt.experts.precedent import PrecedentExpert
from merlt.tools import BaseTool

log = structlog.get_logger()


@dataclass
class OrchestratorConfig:
    """
    Configurazione dell'orchestratore.

    Attributes:
        selection_threshold: Soglia minima per selezionare un expert
        max_experts: Numero massimo di expert da invocare
        parallel_execution: Se eseguire in parallelo
        aggregation_method: Metodo di aggregazione (weighted_average, best, ensemble)
        timeout_seconds: Timeout per ogni expert
    """
    selection_threshold: float = 0.2
    max_experts: int = 4
    parallel_execution: bool = True
    aggregation_method: str = "weighted_average"
    timeout_seconds: float = 30.0


class MultiExpertOrchestrator:
    """
    Orchestratore per il sistema multi-expert interpretativo.

    Coordina il flusso completo:
    1. Riceve una query
    2. Il Router decide quali Expert invocare
    3. Gli Expert analizzano in parallelo
    4. Il GatingNetwork aggrega le risposte
    5. Ritorna una risposta unificata

    Esempio:
        >>> # Setup base
        >>> orchestrator = MultiExpertOrchestrator()
        >>> response = await orchestrator.process("Art. 52 c.p.")
        >>>
        >>> # Con AI service e tools
        >>> tools = [SemanticSearchTool(...), GraphSearchTool(...)]
        >>> orchestrator = MultiExpertOrchestrator(
        ...     tools=tools,
        ...     ai_service=openrouter_service,
        ...     config=OrchestratorConfig(max_experts=3)
        ... )
        >>> response = await orchestrator.process(
        ...     query="Interpretazione della legittima difesa",
        ...     entities={"norm_references": ["urn:norma:cp:art52"]}
        ... )
    """

    # Mapping tipo -> classe Expert
    EXPERT_CLASSES: Dict[str, Type[BaseExpert]] = {
        "literal": LiteralExpert,
        "systemic": SystemicExpert,
        "principles": PrinciplesExpert,
        "precedent": PrecedentExpert,
    }

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        ai_service: Any = None,
        config: Optional[OrchestratorConfig] = None,
        router: Optional[ExpertRouter] = None,
        gating: Optional[GatingNetwork] = None
    ):
        """
        Inizializza l'orchestratore.

        Args:
            tools: Tools condivisi da tutti gli Expert
            ai_service: Servizio AI per LLM
            config: Configurazione orchestratore
            router: Router personalizzato (opzionale)
            gating: GatingNetwork personalizzato (opzionale)
        """
        self.tools = tools or []
        self.ai_service = ai_service
        self.config = config or OrchestratorConfig()

        # Inizializza componenti
        self.router = router or ExpertRouter()
        self.gating = gating or GatingNetwork(
            method=self.config.aggregation_method,
            ai_service=ai_service
        )

        # Inizializza Expert
        self._experts: Dict[str, BaseExpert] = {}
        self._init_experts()

        log.info(
            "MultiExpertOrchestrator initialized",
            experts=list(self._experts.keys()),
            tools=len(self.tools),
            has_ai=ai_service is not None
        )

    def _init_experts(self):
        """Inizializza tutti gli Expert."""
        for expert_type, expert_class in self.EXPERT_CLASSES.items():
            self._experts[expert_type] = expert_class(
                tools=self.tools,
                ai_service=self.ai_service
            )

    async def process(
        self,
        query: str,
        entities: Optional[Dict[str, List[str]]] = None,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AggregatedResponse:
        """
        Processa una query attraverso il sistema multi-expert.

        Args:
            query: Query in linguaggio naturale
            entities: Entità estratte (norm_references, legal_concepts)
            retrieved_chunks: Chunks già recuperati
            metadata: Metadati aggiuntivi

        Returns:
            AggregatedResponse con sintesi finale
        """
        import time
        start_time = time.time()

        trace_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        log.info(f"Processing query", query=query[:50], trace_id=trace_id)

        # Step 1: Costruisci context
        context = ExpertContext(
            query_text=query,
            entities=entities or {},
            retrieved_chunks=retrieved_chunks or [],
            metadata=metadata or {},
            trace_id=trace_id
        )

        # Step 2: Routing
        routing_decision = await self.router.route(context)

        log.info(
            f"Routing decision",
            query_type=routing_decision.query_type,
            weights=routing_decision.expert_weights
        )

        # Step 3: Seleziona Expert
        selected_experts = routing_decision.get_selected_experts(
            threshold=self.config.selection_threshold
        )[:self.config.max_experts]

        if not selected_experts:
            # Fallback: usa tutti gli expert con peso uguale
            selected_experts = [(exp, 1.0 / len(self._experts)) for exp in self._experts.keys()]

        log.info(f"Selected experts", experts=[e[0] for e in selected_experts])

        # Step 4: Esegui Expert
        if self.config.parallel_execution:
            responses = await self._run_experts_parallel(selected_experts, context)
        else:
            responses = await self._run_experts_sequential(selected_experts, context)

        # Step 5: Aggrega risposte
        weights = {exp: w for exp, w in selected_experts}
        aggregated = await self.gating.aggregate(responses, weights, trace_id)

        # Aggiungi metriche
        aggregated.execution_time_ms = (time.time() - start_time) * 1000

        log.info(
            f"Query processed",
            trace_id=trace_id,
            experts_run=len(responses),
            confidence=aggregated.confidence,
            time_ms=aggregated.execution_time_ms
        )

        return aggregated

    async def _run_experts_parallel(
        self,
        selected_experts: List[tuple],
        context: ExpertContext
    ) -> List[ExpertResponse]:
        """Esegue Expert in parallelo."""
        async def run_with_timeout(expert_type: str) -> Optional[ExpertResponse]:
            expert = self._experts.get(expert_type)
            if not expert:
                return None

            try:
                return await asyncio.wait_for(
                    expert.analyze(context),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                log.warning(f"Expert {expert_type} timed out")
                return ExpertResponse(
                    expert_type=expert_type,
                    interpretation=f"Timeout durante l'analisi",
                    confidence=0.0,
                    limitations="Timeout",
                    trace_id=context.trace_id
                )
            except Exception as e:
                log.error(f"Expert {expert_type} failed: {e}")
                return ExpertResponse(
                    expert_type=expert_type,
                    interpretation=f"Errore: {str(e)}",
                    confidence=0.0,
                    limitations=str(e),
                    trace_id=context.trace_id
                )

        tasks = [run_with_timeout(exp) for exp, _ in selected_experts]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    async def _run_experts_sequential(
        self,
        selected_experts: List[tuple],
        context: ExpertContext
    ) -> List[ExpertResponse]:
        """Esegue Expert in sequenza."""
        responses = []

        for expert_type, _ in selected_experts:
            expert = self._experts.get(expert_type)
            if not expert:
                continue

            try:
                response = await asyncio.wait_for(
                    expert.analyze(context),
                    timeout=self.config.timeout_seconds
                )
                responses.append(response)
            except asyncio.TimeoutError:
                log.warning(f"Expert {expert_type} timed out")
                responses.append(ExpertResponse(
                    expert_type=expert_type,
                    interpretation="Timeout",
                    confidence=0.0,
                    trace_id=context.trace_id
                ))
            except Exception as e:
                log.error(f"Expert {expert_type} failed: {e}")

        return responses

    async def process_with_routing(
        self,
        query: str,
        **kwargs
    ) -> tuple:
        """
        Processa e ritorna anche la decisione di routing.

        Returns:
            Tuple (AggregatedResponse, RoutingDecision)
        """
        context = ExpertContext(
            query_text=query,
            entities=kwargs.get("entities", {}),
            retrieved_chunks=kwargs.get("retrieved_chunks", []),
            metadata=kwargs.get("metadata", {}),
            trace_id=datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )

        routing_decision = await self.router.route(context)
        response = await self.process(query, **kwargs)

        return response, routing_decision

    def get_expert(self, expert_type: str) -> Optional[BaseExpert]:
        """Ottiene un Expert per tipo."""
        return self._experts.get(expert_type)

    def list_experts(self) -> List[str]:
        """Lista gli Expert disponibili."""
        return list(self._experts.keys())

    async def run_single_expert(
        self,
        expert_type: str,
        query: str,
        **kwargs
    ) -> ExpertResponse:
        """
        Esegue un singolo Expert specifico.

        Utile per testing o quando si vuole bypassare il routing.
        """
        expert = self._experts.get(expert_type)
        if not expert:
            return ExpertResponse(
                expert_type=expert_type,
                interpretation=f"Expert '{expert_type}' non trovato",
                confidence=0.0
            )

        context = ExpertContext(
            query_text=query,
            entities=kwargs.get("entities", {}),
            retrieved_chunks=kwargs.get("retrieved_chunks", []),
            metadata=kwargs.get("metadata", {}),
            trace_id=datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )

        return await expert.analyze(context)
