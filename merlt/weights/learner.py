"""
Weight Learner
===============

Aggiornamento pesi via RLCF feedback loop.

Il WeightLearner:
1. Riceve feedback con authority score
2. Calcola gradiente basato su correlazione feedback-performance
3. Aggiorna pesi rispettando bounds
4. Persiste tramite WeightStore

Formula: w_new = w_old + η * authority * gradient
Dove:
    - η: learning rate
    - authority: peso del feedback (da RLCF AuthorityModule)
    - gradient: direzione di aggiornamento
"""

import structlog
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from merlt.weights.config import (
    WeightConfig,
    WeightCategory,
    LearnableWeight,
    WeightUpdate,
)
from merlt.weights.store import WeightStore

log = structlog.get_logger()


@dataclass
class LearnerConfig:
    """
    Configurazione per WeightLearner.

    Attributes:
        default_learning_rate: Learning rate default per pesi senza rate specifico
        min_authority_threshold: Authority minima per applicare update
        momentum: Momentum per smooth updates
        clip_gradient: Max gradient magnitude
    """
    default_learning_rate: float = 0.01
    min_authority_threshold: float = 0.3
    momentum: float = 0.9
    clip_gradient: float = 0.1


@dataclass
class RLCFFeedback:
    """
    Feedback da RLCF per aggiornamento pesi.

    Attributes:
        query_id: ID della query originale
        user_id: ID dell'utente che ha dato feedback
        authority: Authority score dell'utente [0-1]
        relevance_scores: Score di rilevanza per risultati
        expected_ranking: Ranking atteso (ground truth)
        actual_ranking: Ranking prodotto dal sistema
        task_type: Tipo di task (retrieval, qa, classification)
    """
    query_id: str
    user_id: str
    authority: float
    relevance_scores: Dict[str, float]
    expected_ranking: Optional[list] = None
    actual_ranking: Optional[list] = None
    task_type: str = "retrieval"
    timestamp: Optional[str] = None


class WeightLearner:
    """
    Aggiorna pesi basandosi su RLCF feedback.

    Il learner implementa un semplice gradient update:
    w_new = w_old + η * authority * gradient

    Dove gradient e' calcolato dalla correlazione tra:
    - Ranking atteso vs ranking ottenuto
    - Relevance scores dei risultati
    - Tipo di query e expert performance

    Esempio:
        >>> learner = WeightLearner(store)
        >>> feedback = RLCFFeedback(
        ...     query_id="q001",
        ...     user_id="user123",
        ...     authority=0.8,
        ...     relevance_scores={"result1": 0.9, "result2": 0.3}
        ... )
        >>> new_config = await learner.update_from_feedback(
        ...     category="retrieval",
        ...     feedback=feedback
        ... )
    """

    def __init__(
        self,
        store: WeightStore,
        config: Optional[LearnerConfig] = None
    ):
        """
        Inizializza WeightLearner.

        Args:
            store: WeightStore per persistenza
            config: Configurazione learner
        """
        self.store = store
        self.config = config or LearnerConfig()
        self._momentum_buffer: Dict[str, float] = {}

        log.info(
            "WeightLearner initialized",
            learning_rate=self.config.default_learning_rate,
            min_authority=self.config.min_authority_threshold
        )

    async def update_from_feedback(
        self,
        category: str,
        feedback: RLCFFeedback,
        experiment_id: Optional[str] = None
    ) -> WeightConfig:
        """
        Aggiorna pesi basandosi su feedback.

        Args:
            category: Categoria di pesi da aggiornare
            feedback: Feedback da RLCF
            experiment_id: ID esperimento (per tracking)

        Returns:
            WeightConfig aggiornata
        """
        # Verifica authority threshold
        if feedback.authority < self.config.min_authority_threshold:
            log.debug(
                "Feedback authority too low, skipping update",
                authority=feedback.authority,
                threshold=self.config.min_authority_threshold
            )
            current = await self.store.get_weights(experiment_id=experiment_id)
            return current

        # Carica pesi correnti
        current = await self.store.get_weights(experiment_id=experiment_id)

        # Calcola gradiente
        gradient = self._compute_gradient(category, feedback, current)

        # Applica update
        updated = self._apply_update(category, current, gradient, feedback.authority)

        # Salva se experiment tracking attivo
        if experiment_id:
            await self.store.save_weights(
                config=updated,
                experiment_id=experiment_id,
                metrics={"feedback_authority": feedback.authority}
            )

        log.info(
            "Weights updated from feedback",
            category=category,
            authority=feedback.authority,
            gradient_norm=sum(abs(v) for v in gradient.values())
        )

        return updated

    def _compute_gradient(
        self,
        category: str,
        feedback: RLCFFeedback,
        current: WeightConfig
    ) -> Dict[str, float]:
        """
        Calcola gradiente per update.

        Il gradiente e' basato sulla differenza tra ranking atteso e ottenuto,
        pesata per la rilevanza dei risultati.
        """
        gradient = {}

        if category == "retrieval":
            gradient = self._compute_retrieval_gradient(feedback, current)
        elif category == "expert_traversal":
            gradient = self._compute_traversal_gradient(feedback, current)
        elif category == "gating":
            gradient = self._compute_gating_gradient(feedback, current)
        else:
            log.warning(f"Unknown category for gradient: {category}")

        # Clip gradient
        for key in gradient:
            gradient[key] = max(
                -self.config.clip_gradient,
                min(self.config.clip_gradient, gradient[key])
            )

        return gradient

    def _compute_retrieval_gradient(
        self,
        feedback: RLCFFeedback,
        current: WeightConfig
    ) -> Dict[str, float]:
        """
        Calcola gradiente per pesi retrieval.

        Se i risultati graph-based sono piu' rilevanti, aumenta (1-alpha).
        Se i risultati semantic sono piu' rilevanti, aumenta alpha.
        """
        gradient = {"alpha": 0.0}

        if not feedback.relevance_scores:
            return gradient

        # Calcola media rilevanza
        avg_relevance = sum(feedback.relevance_scores.values()) / len(feedback.relevance_scores)

        # Euristica semplice: se rilevanza alta, mantieni; se bassa, cambia
        if avg_relevance < 0.5:
            # Risultati scarsi, prova a cambiare direzione
            current_alpha = current.get_retrieval_alpha()
            if current_alpha > 0.5:
                gradient["alpha"] = -0.01  # Riduci semantic
            else:
                gradient["alpha"] = 0.01   # Aumenta semantic

        return gradient

    def _compute_traversal_gradient(
        self,
        feedback: RLCFFeedback,
        current: WeightConfig
    ) -> Dict[str, float]:
        """
        Calcola gradiente per pesi expert traversal.

        Basato su quali tipi di relazione hanno portato a risultati rilevanti.
        """
        # TODO: Implementare quando abbiamo tracking dettagliato delle relazioni
        return {}

    def _compute_gating_gradient(
        self,
        feedback: RLCFFeedback,
        current: WeightConfig
    ) -> Dict[str, float]:
        """
        Calcola gradiente per pesi gating.

        Aumenta prior degli expert che hanno performato bene.
        """
        # TODO: Implementare quando abbiamo output per-expert
        return {}

    def _apply_update(
        self,
        category: str,
        current: WeightConfig,
        gradient: Dict[str, float],
        authority: float
    ) -> WeightConfig:
        """
        Applica update ai pesi rispettando bounds.
        """
        # Deep copy per non modificare originale
        import copy
        updated = copy.deepcopy(current)

        if category == "retrieval" and "alpha" in gradient:
            # Update alpha
            old_alpha = updated.retrieval.alpha.default
            lr = updated.retrieval.alpha.learning_rate
            new_alpha = old_alpha + lr * authority * gradient["alpha"]

            # Clip to bounds
            min_val, max_val = updated.retrieval.alpha.bounds
            new_alpha = max(min_val, min(max_val, new_alpha))

            updated.retrieval.alpha.default = new_alpha

            log.debug(
                "Alpha updated",
                old=old_alpha,
                new=new_alpha,
                gradient=gradient["alpha"]
            )

        updated.updated_at = datetime.now().isoformat()
        return updated

    async def batch_update(
        self,
        category: str,
        feedbacks: list,
        experiment_id: Optional[str] = None
    ) -> WeightConfig:
        """
        Applica batch di feedback in una volta.

        Utile per training offline o bulk updates.
        """
        current = await self.store.get_weights(experiment_id=experiment_id)

        for feedback in feedbacks:
            current = await self.update_from_feedback(
                category=category,
                feedback=feedback,
                experiment_id=experiment_id
            )

        return current

    def reset_momentum(self) -> None:
        """Reset momentum buffer."""
        self._momentum_buffer.clear()
        log.debug("Momentum buffer reset")
