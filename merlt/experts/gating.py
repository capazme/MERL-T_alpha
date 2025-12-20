"""
Gating Network
===============

Network per aggregare le risposte di più Expert.

Il GatingNetwork:
1. Riceve ExpertResponse da più Expert
2. Combina le interpretazioni usando pesi
3. Sintetizza una risposta finale unificata
4. Gestisce conflitti tra Expert

Strategie di aggregazione:
- weighted_average: Media pesata delle interpretazioni
- best_confidence: Usa solo l'expert con confidenza più alta
- consensus: Cerca consenso tra expert
- ensemble: Combina tutte le prospettive

Esempio:
    >>> gating = GatingNetwork()
    >>> responses = [literal_response, systemic_response, precedent_response]
    >>> weights = {"literal": 0.5, "systemic": 0.3, "precedent": 0.2}
    >>> final = await gating.aggregate(responses, weights)
"""

import structlog
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from merlt.experts.base import ExpertResponse, LegalSource, ReasoningStep, ConfidenceFactors

log = structlog.get_logger()


@dataclass
class AggregatedResponse:
    """
    Risposta aggregata da più Expert.

    Attributes:
        synthesis: Sintesi finale delle interpretazioni
        expert_contributions: Contributi di ogni expert
        combined_legal_basis: Fonti combinate
        combined_reasoning: Ragionamento combinato
        confidence: Confidenza aggregata
        conflicts: Eventuali conflitti tra expert
        aggregation_method: Metodo usato
        trace_id: ID per tracing
    """
    synthesis: str
    expert_contributions: Dict[str, Dict[str, Any]]
    combined_legal_basis: List[LegalSource] = field(default_factory=list)
    combined_reasoning: List[ReasoningStep] = field(default_factory=list)
    confidence: float = 0.5
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    conflicts: List[str] = field(default_factory=list)
    aggregation_method: str = "weighted_average"
    trace_id: str = ""
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario."""
        return {
            "synthesis": self.synthesis,
            "expert_contributions": self.expert_contributions,
            "combined_legal_basis": [lb.to_dict() for lb in self.combined_legal_basis],
            "combined_reasoning": [rs.to_dict() for rs in self.combined_reasoning],
            "confidence": self.confidence,
            "confidence_breakdown": self.confidence_breakdown,
            "conflicts": self.conflicts,
            "aggregation_method": self.aggregation_method,
            "trace_id": self.trace_id,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp
        }


class GatingNetwork:
    """
    Network per aggregare risposte da più Expert.

    Supporta diverse strategie di aggregazione:
    - weighted_average: Combina con pesi
    - best_confidence: Sceglie il migliore
    - consensus: Cerca punti comuni
    - ensemble: Mantiene tutte le prospettive

    Esempio:
        >>> gating = GatingNetwork(method="weighted_average")
        >>> responses = [resp1, resp2, resp3]
        >>> weights = {"literal": 0.5, "systemic": 0.3, "principles": 0.2}
        >>> result = await gating.aggregate(responses, weights)
    """

    def __init__(
        self,
        method: str = "weighted_average",
        ai_service: Any = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Inizializza GatingNetwork.

        Args:
            method: Metodo di aggregazione
            ai_service: Servizio AI per sintesi (opzionale)
            config: Configurazione aggiuntiva
        """
        self.method = method
        self.ai_service = ai_service
        self.config = config or {}

        log.info(f"GatingNetwork initialized", method=method)

    async def aggregate(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        trace_id: str = ""
    ) -> AggregatedResponse:
        """
        Aggrega le risposte degli Expert.

        Args:
            responses: Lista di ExpertResponse
            weights: Pesi per ogni expert_type
            trace_id: ID per tracing

        Returns:
            AggregatedResponse con sintesi
        """
        import time
        start_time = time.time()

        if not responses:
            return AggregatedResponse(
                synthesis="Nessuna risposta da aggregare",
                expert_contributions={},
                confidence=0.0,
                trace_id=trace_id
            )

        log.info(
            f"Aggregating {len(responses)} responses",
            method=self.method,
            trace_id=trace_id
        )

        # Normalizza pesi
        present_experts = {r.expert_type for r in responses}
        filtered_weights = {k: v for k, v in weights.items() if k in present_experts}
        total = sum(filtered_weights.values())
        if total > 0:
            normalized_weights = {k: v / total for k, v in filtered_weights.items()}
        else:
            normalized_weights = {k: 1.0 / len(present_experts) for k in present_experts}

        # Esegui aggregazione in base al metodo
        if self.method == "weighted_average":
            result = await self._aggregate_weighted(responses, normalized_weights, trace_id)
        elif self.method == "best_confidence":
            result = await self._aggregate_best(responses, trace_id)
        elif self.method == "consensus":
            result = await self._aggregate_consensus(responses, normalized_weights, trace_id)
        elif self.method == "ensemble":
            result = await self._aggregate_ensemble(responses, normalized_weights, trace_id)
        else:
            # Default to weighted average
            result = await self._aggregate_weighted(responses, normalized_weights, trace_id)

        result.execution_time_ms = (time.time() - start_time) * 1000
        result.trace_id = trace_id

        log.info(
            f"Aggregation completed",
            method=self.method,
            confidence=result.confidence,
            conflicts=len(result.conflicts)
        )

        return result

    async def _aggregate_weighted(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        trace_id: str
    ) -> AggregatedResponse:
        """Aggregazione con media pesata."""
        # Raccogli contributi
        contributions = {}
        for resp in responses:
            w = weights.get(resp.expert_type, 0.0)
            contributions[resp.expert_type] = {
                "interpretation": resp.interpretation,
                "confidence": resp.confidence,
                "weight": w,
                "weighted_confidence": resp.confidence * w
            }

        # Calcola confidenza aggregata
        weighted_confidence = sum(
            c["weighted_confidence"] for c in contributions.values()
        )
        confidence_breakdown = {
            exp: c["weighted_confidence"] for exp, c in contributions.items()
        }

        # Combina legal basis (deduplica per source_id)
        combined_basis = []
        seen_ids = set()
        for resp in sorted(responses, key=lambda r: weights.get(r.expert_type, 0), reverse=True):
            for lb in resp.legal_basis:
                if lb.source_id not in seen_ids:
                    combined_basis.append(lb)
                    seen_ids.add(lb.source_id)

        # Combina reasoning steps
        combined_reasoning = []
        step_num = 1
        for resp in sorted(responses, key=lambda r: weights.get(r.expert_type, 0), reverse=True):
            for rs in resp.reasoning_steps:
                combined_reasoning.append(ReasoningStep(
                    step_number=step_num,
                    description=f"[{resp.expert_type}] {rs.description}",
                    sources=rs.sources
                ))
                step_num += 1

        # Identifica conflitti
        conflicts = self._detect_conflicts(responses)

        # Genera sintesi
        if self.ai_service:
            synthesis = await self._synthesize_with_llm(responses, weights)
        else:
            synthesis = self._synthesize_simple(responses, weights)

        return AggregatedResponse(
            synthesis=synthesis,
            expert_contributions=contributions,
            combined_legal_basis=combined_basis[:10],  # Limita a 10
            combined_reasoning=combined_reasoning[:15],  # Limita a 15
            confidence=weighted_confidence,
            confidence_breakdown=confidence_breakdown,
            conflicts=conflicts,
            aggregation_method="weighted_average",
            trace_id=trace_id
        )

    async def _aggregate_best(
        self,
        responses: List[ExpertResponse],
        trace_id: str
    ) -> AggregatedResponse:
        """Usa solo l'expert con confidenza più alta."""
        best = max(responses, key=lambda r: r.confidence)

        contributions = {
            r.expert_type: {
                "interpretation": r.interpretation,
                "confidence": r.confidence,
                "selected": r.expert_type == best.expert_type
            }
            for r in responses
        }

        return AggregatedResponse(
            synthesis=best.interpretation,
            expert_contributions=contributions,
            combined_legal_basis=best.legal_basis,
            combined_reasoning=best.reasoning_steps,
            confidence=best.confidence,
            confidence_breakdown={best.expert_type: best.confidence},
            conflicts=[],
            aggregation_method="best_confidence",
            trace_id=trace_id
        )

    async def _aggregate_consensus(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        trace_id: str
    ) -> AggregatedResponse:
        """Cerca consenso tra expert."""
        # Cerca fonti citate da più expert
        source_counts = {}
        for resp in responses:
            for lb in resp.legal_basis:
                if lb.source_id not in source_counts:
                    source_counts[lb.source_id] = {"source": lb, "experts": [], "count": 0}
                source_counts[lb.source_id]["experts"].append(resp.expert_type)
                source_counts[lb.source_id]["count"] += 1

        # Fonti con consenso (citate da 2+ expert)
        consensus_sources = [
            s["source"] for s in source_counts.values()
            if s["count"] >= 2
        ]

        # Contributi
        contributions = {
            r.expert_type: {
                "interpretation": r.interpretation,
                "confidence": r.confidence,
                "weight": weights.get(r.expert_type, 0)
            }
            for r in responses
        }

        # Confidenza basata sul consenso
        if consensus_sources:
            consensus_confidence = min(
                len(consensus_sources) / max(len(source_counts), 1) + 0.3,
                1.0
            )
        else:
            consensus_confidence = 0.4

        # Sintesi focus sul consenso
        if self.ai_service:
            synthesis = await self._synthesize_with_llm(responses, weights, focus="consensus")
        else:
            synthesis = self._synthesize_consensus(responses, consensus_sources)

        return AggregatedResponse(
            synthesis=synthesis,
            expert_contributions=contributions,
            combined_legal_basis=consensus_sources[:10],
            combined_reasoning=[],
            confidence=consensus_confidence,
            confidence_breakdown={r.expert_type: r.confidence for r in responses},
            conflicts=self._detect_conflicts(responses),
            aggregation_method="consensus",
            trace_id=trace_id
        )

    async def _aggregate_ensemble(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        trace_id: str
    ) -> AggregatedResponse:
        """Mantiene tutte le prospettive come ensemble."""
        # Costruisci sintesi strutturata con tutte le prospettive
        contributions = {}
        sections = []

        for resp in sorted(responses, key=lambda r: weights.get(r.expert_type, 0), reverse=True):
            contributions[resp.expert_type] = {
                "interpretation": resp.interpretation,
                "confidence": resp.confidence,
                "weight": weights.get(resp.expert_type, 0),
                "limitations": resp.limitations
            }

            sections.append(f"## {resp.expert_type.upper()}\n{resp.interpretation}")

        synthesis = "\n\n".join(sections)

        # Combina tutte le fonti
        all_basis = []
        seen = set()
        for resp in responses:
            for lb in resp.legal_basis:
                if lb.source_id not in seen:
                    all_basis.append(lb)
                    seen.add(lb.source_id)

        # Confidenza media
        avg_confidence = sum(r.confidence for r in responses) / len(responses)

        return AggregatedResponse(
            synthesis=synthesis,
            expert_contributions=contributions,
            combined_legal_basis=all_basis[:15],
            combined_reasoning=[],
            confidence=avg_confidence,
            confidence_breakdown={r.expert_type: r.confidence for r in responses},
            conflicts=self._detect_conflicts(responses),
            aggregation_method="ensemble",
            trace_id=trace_id
        )

    def _detect_conflicts(self, responses: List[ExpertResponse]) -> List[str]:
        """Rileva conflitti tra interpretazioni."""
        conflicts = []

        # Contrasto di confidenza significativo
        if len(responses) >= 2:
            confidences = [r.confidence for r in responses]
            if max(confidences) - min(confidences) > 0.4:
                high = max(responses, key=lambda r: r.confidence)
                low = min(responses, key=lambda r: r.confidence)
                conflicts.append(
                    f"Divergenza significativa: {high.expert_type} ({high.confidence:.2f}) "
                    f"vs {low.expert_type} ({low.confidence:.2f})"
                )

        # Fonti contrastanti (difficile da rilevare senza NLP avanzato)
        # Per ora, segnaliamo solo se ci sono poche fonti comuni
        if len(responses) >= 2:
            source_sets = [
                {lb.source_id for lb in r.legal_basis}
                for r in responses
            ]
            if all(source_sets):
                common = source_sets[0].intersection(*source_sets[1:])
                total = source_sets[0].union(*source_sets[1:])
                if len(total) > 0 and len(common) / len(total) < 0.2:
                    conflicts.append("Fonti giuridiche poco sovrapposte tra expert")

        return conflicts

    def _synthesize_simple(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float]
    ) -> str:
        """Sintesi semplice senza LLM."""
        sections = ["# Sintesi Multi-Expert\n"]

        # Ordina per peso
        sorted_responses = sorted(
            responses,
            key=lambda r: weights.get(r.expert_type, 0),
            reverse=True
        )

        for resp in sorted_responses:
            w = weights.get(resp.expert_type, 0)
            sections.append(f"## {resp.expert_type.title()} (peso: {w:.2f}, confidenza: {resp.confidence:.2f})")
            # Prendi le prime 500 chars dell'interpretazione
            interp = resp.interpretation[:500]
            if len(resp.interpretation) > 500:
                interp += "..."
            sections.append(interp)
            sections.append("")

        sections.append("\n*Nota: Sintesi generata senza AI - combinazione meccanica delle interpretazioni*")

        return "\n".join(sections)

    def _synthesize_consensus(
        self,
        responses: List[ExpertResponse],
        consensus_sources: List[LegalSource]
    ) -> str:
        """Sintesi focalizzata sul consenso."""
        sections = ["# Punti di Consenso\n"]

        if consensus_sources:
            sections.append("## Fonti su cui gli Expert concordano:")
            for lb in consensus_sources[:5]:
                sections.append(f"- {lb.citation}: {lb.excerpt[:200]}...")
        else:
            sections.append("Nessuna fonte citata da più Expert.")

        sections.append("\n## Interpretazioni:")
        for resp in responses:
            sections.append(f"- **{resp.expert_type}**: {resp.interpretation[:300]}...")

        return "\n".join(sections)

    async def _synthesize_with_llm(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        focus: str = "balanced"
    ) -> str:
        """Sintesi con LLM."""
        if not self.ai_service:
            return self._synthesize_simple(responses, weights)

        prompt = self._build_synthesis_prompt(responses, weights, focus)

        try:
            result = await self.ai_service.generate_response_async(
                prompt=prompt,
                model=self.config.get("model", "google/gemini-2.5-flash"),
                temperature=0.3
            )

            if isinstance(result, dict):
                return result.get("content", str(result))
            return str(result)

        except Exception as e:
            log.error(f"LLM synthesis failed: {e}")
            return self._synthesize_simple(responses, weights)

    def _build_synthesis_prompt(
        self,
        responses: List[ExpertResponse],
        weights: Dict[str, float],
        focus: str
    ) -> str:
        """Costruisce prompt per sintesi LLM."""
        sections = [
            "Sei un giurista esperto. Sintetizza le seguenti interpretazioni "
            "da diversi approcci ermeneutici in una risposta coerente e completa.\n"
        ]

        if focus == "consensus":
            sections.append("FOCUS: Evidenzia i punti di accordo tra gli expert.\n")

        for resp in sorted(responses, key=lambda r: weights.get(r.expert_type, 0), reverse=True):
            w = weights.get(resp.expert_type, 0)
            sections.append(f"## {resp.expert_type.upper()} (peso: {w:.2f})")
            sections.append(f"Confidenza: {resp.confidence:.2f}")
            sections.append(f"Interpretazione: {resp.interpretation}")
            if resp.legal_basis:
                sections.append("Fonti: " + ", ".join(lb.citation for lb in resp.legal_basis[:3]))
            sections.append("")

        sections.append(
            "\nProduci una SINTESI in italiano che:\n"
            "1. Integri le diverse prospettive\n"
            "2. Evidenzi eventuali divergenze\n"
            "3. Citi le fonti più rilevanti\n"
            "4. Sia chiara e utilizzabile"
        )

        return "\n".join(sections)
