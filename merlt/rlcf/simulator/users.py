"""
Profili utente sintetici per simulazione RLCF.

Questo modulo definisce diversi profili di utenti simulati, ognuno con:
- Authority baseline basata su credenziali simulate
- Bias di valutazione per ogni dimensione
- Livello di rumore nelle valutazioni
- Evoluzione dell'authority nel tempo

I profili sono progettati per simulare una community realistica con:
- Esperti rigorosi (professori, giudici)
- Specialisti di dominio (avvocati praticanti)
- Studenti (feedback più generoso)
- Rumore casuale (utenti non qualificati)
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np


# Profili utente predefiniti basati su archetipi realistici
PROFILES: Dict[str, Dict[str, Any]] = {
    "strict_expert": {
        "baseline_authority": 0.85,
        "credentials": {
            "academic_degree": "PhD",
            "years_experience": 15,
            "specialization": "diritto civile",
            "publications": 25,
        },
        "evaluation_bias": {
            "accuracy": 0.0,      # Nessun bias, valutazione oggettiva
            "clarity": -0.1,      # Leggermente critico sulla chiarezza
            "utility": 0.0,
            "reasoning": -0.05,   # Standard elevati sul ragionamento
        },
        "noise_level": 0.05,      # Valutazioni molto consistenti
        "description": "Professore universitario, valutazione rigorosa e precisa",
        "feedback_rate": 0.9,     # Alta partecipazione
    },
    "lenient_student": {
        "baseline_authority": 0.25,
        "credentials": {
            "academic_degree": "Bachelor",
            "years_experience": 0,
            "specialization": None,
            "publications": 0,
        },
        "evaluation_bias": {
            "accuracy": 0.2,      # Tende a sovrastimare l'accuratezza
            "clarity": 0.15,      # Apprezza risposte chiare
            "utility": 0.1,
            "reasoning": 0.1,
        },
        "noise_level": 0.20,      # Valutazioni più variabili
        "description": "Studente di giurisprudenza, tende a sovrastimare",
        "feedback_rate": 0.7,
    },
    "domain_specialist": {
        "baseline_authority": 0.70,
        "credentials": {
            "academic_degree": "Master",
            "years_experience": 8,
            "specialization": "contratti",
            "bar_admission": True,
        },
        "evaluation_bias": {
            "accuracy": 0.0,
            "clarity": 0.0,
            "utility": -0.05,     # Esigente sull'utilità pratica
            "reasoning": 0.0,
        },
        "noise_level": 0.08,
        "description": "Avvocato specializzato, preciso nel suo dominio",
        "feedback_rate": 0.6,     # Partecipazione moderata (impegnato)
    },
    "random_noise": {
        "baseline_authority": 0.10,
        "credentials": {},
        "evaluation_bias": {
            "accuracy": 0.0,
            "clarity": 0.0,
            "utility": 0.0,
            "reasoning": 0.0,
        },
        "noise_level": 0.40,      # Alta variabilità (feedback inaffidabile)
        "description": "Utente casuale, feedback inaffidabile",
        "feedback_rate": 0.3,
    },
    "senior_magistrate": {
        "baseline_authority": 0.90,
        "credentials": {
            "academic_degree": "PhD",
            "years_experience": 25,
            "specialization": "procedura civile",
            "judicial_role": "Consigliere Cassazione",
        },
        "evaluation_bias": {
            "accuracy": -0.05,    # Molto esigente
            "clarity": 0.0,
            "utility": 0.0,
            "reasoning": -0.1,    # Standard altissimi sul ragionamento
        },
        "noise_level": 0.03,
        "description": "Magistrato senior, valutazione autorevole",
        "feedback_rate": 0.4,     # Bassa partecipazione (molto impegnato)
    },
}


@dataclass
class SyntheticUser:
    """
    Rappresenta un utente simulato con caratteristiche specifiche.

    Attributes:
        user_id: Identificatore univoco dell'utente
        profile_type: Tipo di profilo (da PROFILES)
        baseline_authority: Authority iniziale basata su credenziali
        current_authority: Authority attuale (evolve con feedback)
        evaluation_bias: Bias per dimensione di valutazione
        noise_level: Deviazione standard del rumore gaussiano
        credentials: Credenziali simulate
        feedback_history: Storico dei feedback forniti
        track_record: Punteggio track record (evolve nel tempo)
        _parent_pool: Riferimento al pool genitore (per RNG isolato)
    """

    user_id: int
    profile_type: str
    baseline_authority: float
    current_authority: float
    evaluation_bias: Dict[str, float]
    noise_level: float
    credentials: Dict[str, Any]
    description: str
    feedback_rate: float = 0.7
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    track_record: float = field(init=False)  # Inizializzato a baseline_authority
    quality_scores: List[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    # Riferimento al pool genitore (per RNG isolato)
    _parent_pool: Optional["UserPool"] = field(default=None, repr=False)

    def __post_init__(self):
        """Inizializza track_record a baseline_authority per coerenza."""
        self.track_record = self.baseline_authority

    def apply_bias(self, base_score: float, dimension: str) -> float:
        """
        Applica il bias del profilo a un punteggio base.

        Args:
            base_score: Punteggio oggettivo (0-1 o 1-5)
            dimension: Dimensione di valutazione (accuracy, clarity, etc.)

        Returns:
            Punteggio con bias applicato
        """
        bias = self.evaluation_bias.get(dimension, 0.0)
        return base_score + bias

    def add_noise(self, score: float, scale: float = 1.0) -> float:
        """
        Aggiunge rumore gaussiano al punteggio.

        Args:
            score: Punteggio da perturbare
            scale: Moltiplicatore per il noise_level

        Returns:
            Punteggio con rumore
        """
        noise = np.random.normal(0, self.noise_level * scale)
        return score + noise

    def should_provide_feedback(self) -> bool:
        """
        Determina se l'utente fornirà feedback (basato su feedback_rate).

        Usa il RNG isolato del pool per evitare "zone morte" del generatore
        globale quando il seed viene consumato sequenzialmente.
        """
        if self._parent_pool is not None and hasattr(self._parent_pool, '_feedback_rng'):
            return self._parent_pool._feedback_rng.random() < self.feedback_rate
        # Fallback a RNG globale (retrocompatibilità)
        return random.random() < self.feedback_rate

    def record_feedback(
        self,
        feedback: Dict[str, Any],
        quality_score: float,
        feedback_accuracy: Optional[float] = None,
        authority_config: Optional["AuthorityModelConfig"] = None
    ):
        """
        Registra un feedback fornito e aggiorna il track record.

        Args:
            feedback: Dati del feedback
            quality_score: Qualità della risposta (0-1) - usato per metriche sistema
            feedback_accuracy: Accuratezza del feedback utente (0-1) - usato per authority.
                              Se None, usa quality_score per retrocompatibilità.
            authority_config: Configurazione modello authority (opzionale).
                            Se None, usa valori di default.

        Note:
            - quality_score: misura quanto era buona la RISPOSTA del sistema
            - feedback_accuracy: misura quanto era ACCURATO il feedback dell'utente
              (cioè quanto il rating utente era vicino al ground truth)

            Separare queste metriche permette di premiare gli esperti che danno
            feedback accurati, anche quando valutano negativamente risposte scadenti.
        """
        # Import locale per evitare dipendenza circolare
        from merlt.rlcf.simulator.config import AuthorityModelConfig

        # Se feedback_accuracy non fornito, usa quality_score (retrocompatibilità)
        accuracy_for_authority = feedback_accuracy if feedback_accuracy is not None else quality_score

        self.feedback_history.append({
            **feedback,
            "quality_score": quality_score,
            "feedback_accuracy": accuracy_for_authority,
            "timestamp": datetime.now().isoformat(),
        })
        self.quality_scores.append(quality_score)

        # Usa config passata o defaults
        cfg = authority_config or AuthorityModelConfig()

        # Aggiorna track record con exponential smoothing
        # IMPORTANTE: usa feedback_accuracy, NON quality_score!
        # Questo premia utenti che danno feedback accurati.
        self.track_record = (
            (1 - cfg.lambda_factor) * self.track_record +
            cfg.lambda_factor * accuracy_for_authority
        )

        # Aggiorna authority con formula configurabile:
        # A = w_b*Baseline + w_t*TrackRecord + w_a*FeedbackAccuracy
        self.current_authority = (
            cfg.weight_baseline * self.baseline_authority +
            cfg.weight_track_record * self.track_record +
            cfg.weight_quality * accuracy_for_authority  # Rinominare in config?
        )

    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche dell'utente."""
        return {
            "user_id": self.user_id,
            "profile_type": self.profile_type,
            "baseline_authority": self.baseline_authority,
            "current_authority": self.current_authority,
            "track_record": self.track_record,
            "feedback_count": len(self.feedback_history),
            "avg_quality": np.mean(self.quality_scores) if self.quality_scores else 0.0,
            "authority_delta": self.current_authority - self.baseline_authority,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializza l'utente in dizionario."""
        return {
            "user_id": self.user_id,
            "profile_type": self.profile_type,
            "baseline_authority": self.baseline_authority,
            "current_authority": self.current_authority,
            "evaluation_bias": self.evaluation_bias,
            "noise_level": self.noise_level,
            "credentials": self.credentials,
            "description": self.description,
            "feedback_rate": self.feedback_rate,
            "track_record": self.track_record,
            "feedback_count": len(self.feedback_history),
            "created_at": self.created_at,
        }


@dataclass
class UserPool:
    """
    Pool di utenti sintetici per la simulazione.

    Gestisce la creazione, selezione e tracking degli utenti.

    Utilizza un RNG isolato per le decisioni di feedback per evitare
    che il consumo sequenziale del seed globale causi "zone morte"
    dove tutti i valori random sono alti.
    """

    users: List[SyntheticUser] = field(default_factory=list)
    distribution: Dict[str, int] = field(default_factory=dict)
    random_seed: Optional[int] = None
    # RNG indipendente per decisioni feedback (evita zone morte)
    _feedback_rng: random.Random = field(init=False, repr=False, default=None)

    def __post_init__(self):
        if self.random_seed is not None:
            random.seed(self.random_seed)
            np.random.seed(self.random_seed)

        # Crea RNG isolato con seed derivato (offset +1000 per separazione)
        feedback_seed = (self.random_seed + 1000) if self.random_seed else None
        self._feedback_rng = random.Random(feedback_seed)

        # Collega ogni utente esistente al pool
        for user in self.users:
            user._parent_pool = self

    def add_user(self, user: SyntheticUser):
        """Aggiunge un utente al pool e lo collega al RNG isolato."""
        user._parent_pool = self  # Collega utente al pool per RNG isolato
        self.users.append(user)
        profile = user.profile_type
        self.distribution[profile] = self.distribution.get(profile, 0) + 1

    def get_random_user(self) -> SyntheticUser:
        """Seleziona un utente casuale dal pool."""
        return random.choice(self.users)

    def get_users_by_profile(self, profile_type: str) -> List[SyntheticUser]:
        """Restituisce tutti gli utenti di un certo profilo."""
        return [u for u in self.users if u.profile_type == profile_type]

    def get_available_evaluators(self) -> List[SyntheticUser]:
        """
        Restituisce utenti che forniranno feedback (basato su feedback_rate).
        """
        return [u for u in self.users if u.should_provide_feedback()]

    def get_pool_stats(self) -> Dict[str, Any]:
        """Statistiche aggregate del pool."""
        if not self.users:
            return {"total_users": 0}

        authorities = [u.current_authority for u in self.users]
        track_records = [u.track_record for u in self.users]
        feedback_counts = [len(u.feedback_history) for u in self.users]

        return {
            "total_users": len(self.users),
            "distribution": self.distribution,
            "authority": {
                "mean": np.mean(authorities),
                "std": np.std(authorities),
                "min": np.min(authorities),
                "max": np.max(authorities),
            },
            "track_record": {
                "mean": np.mean(track_records),
                "std": np.std(track_records),
            },
            "feedback": {
                "total": sum(feedback_counts),
                "per_user_mean": np.mean(feedback_counts),
            },
            "by_profile": {
                profile: {
                    "count": len(users := self.get_users_by_profile(profile)),
                    "avg_authority": np.mean([u.current_authority for u in users]) if users else 0,
                }
                for profile in self.distribution.keys()
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializza il pool in dizionario."""
        return {
            "users": [u.to_dict() for u in self.users],
            "distribution": self.distribution,
            "stats": self.get_pool_stats(),
        }


def create_user_pool(
    distribution: Dict[str, int],
    random_seed: Optional[int] = 42
) -> UserPool:
    """
    Crea un pool di utenti sintetici secondo la distribuzione specificata.

    Args:
        distribution: Dizionario {profile_type: count}
                     Es: {"strict_expert": 3, "lenient_student": 8}
        random_seed: Seed per riproducibilità

    Returns:
        UserPool con gli utenti creati

    Example:
        >>> pool = create_user_pool({
        ...     "strict_expert": 3,
        ...     "domain_specialist": 5,
        ...     "lenient_student": 8,
        ...     "random_noise": 4
        ... })
        >>> print(f"Total users: {len(pool.users)}")
        Total users: 20
    """
    pool = UserPool(random_seed=random_seed)
    user_id = 1

    for profile_type, count in distribution.items():
        if profile_type not in PROFILES:
            raise ValueError(f"Profilo sconosciuto: {profile_type}. "
                           f"Profili validi: {list(PROFILES.keys())}")

        profile = PROFILES[profile_type]

        for _ in range(count):
            # Aggiungi leggera variazione all'authority baseline
            authority_variation = np.random.normal(0, 0.05)
            baseline_authority = np.clip(
                profile["baseline_authority"] + authority_variation,
                0.0, 1.0
            )

            user = SyntheticUser(
                user_id=user_id,
                profile_type=profile_type,
                baseline_authority=baseline_authority,
                current_authority=baseline_authority,  # Inizialmente uguale
                evaluation_bias=profile["evaluation_bias"].copy(),
                noise_level=profile["noise_level"],
                credentials=profile["credentials"].copy(),
                description=profile["description"],
                feedback_rate=profile.get("feedback_rate", 0.7),
            )

            pool.add_user(user)
            user_id += 1

    return pool


def create_user_from_profile(
    profile_type: str,
    user_id: int,
    override: Optional[Dict[str, Any]] = None
) -> SyntheticUser:
    """
    Crea un singolo utente da un profilo con possibili override.

    Args:
        profile_type: Tipo di profilo
        user_id: ID da assegnare
        override: Valori da sovrascrivere

    Returns:
        SyntheticUser configurato
    """
    if profile_type not in PROFILES:
        raise ValueError(f"Profilo sconosciuto: {profile_type}")

    profile = PROFILES[profile_type].copy()
    if override:
        profile.update(override)

    return SyntheticUser(
        user_id=user_id,
        profile_type=profile_type,
        baseline_authority=profile["baseline_authority"],
        current_authority=profile["baseline_authority"],
        evaluation_bias=profile["evaluation_bias"].copy(),
        noise_level=profile["noise_level"],
        credentials=profile.get("credentials", {}),
        description=profile.get("description", ""),
        feedback_rate=profile.get("feedback_rate", 0.7),
    )
