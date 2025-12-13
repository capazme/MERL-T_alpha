"""
Enrichment Models
=================

Dataclass per la pipeline di enrichment.

Contenuti:
- EntityType: Enum dei tipi di entità estraibili
- EnrichmentContent: Contenuto da processare (fonte)
- ExtractedEntity: Entità estratta da LLM
- ExtractedRelation: Relazione estratta da LLM
- LinkedEntity: Entità dopo linking/dedup
- EnrichmentResult: Risultato finale pipeline
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(Enum):
    """Tipi di entità estraibili dal knowledge graph."""

    # Entità core (priorità 1)
    CONCETTO = "concetto"
    PRINCIPIO = "principio"
    DEFINIZIONE = "definizione"

    # Entità soggetti (priorità 2)
    SOGGETTO = "soggetto"
    RUOLO = "ruolo"
    MODALITA = "modalita"

    # Entità fatti e atti (priorità 3)
    FATTO = "fatto"
    ATTO = "atto"
    PROCEDURA = "procedura"
    TERMINE = "termine"
    EFFETTO = "effetto"
    RESPONSABILITA = "responsabilita"
    RIMEDIO = "rimedio"

    # Entità avanzate (priorità 4)
    SANZIONE = "sanzione"
    CASO = "caso"
    ECCEZIONE = "eccezione"
    CLAUSOLA = "clausola"


class RelationType(Enum):
    """
    Tipi di relazioni estraibili.

    Allineato allo schema LKIF-compliant con 65+ relazioni.
    Vedi config/schema.yaml per la definizione completa.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI STRUTTURALI (backbone)
    # ─────────────────────────────────────────────────────────────────────────
    CONTIENE = "CONTIENE"  # Norma contiene Comma
    MODIFICA = "MODIFICA"  # Norma modifica altra Norma
    CITA = "CITA"  # Norma cita altra Norma

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI SEMANTICHE (Norma → Entità)
    # ─────────────────────────────────────────────────────────────────────────
    DISCIPLINA = "DISCIPLINA"  # Norma disciplina un Concetto
    ESPRIME_PRINCIPIO = "ESPRIME_PRINCIPIO"  # Norma esprime/fonda un Principio
    DEFINISCE = "DEFINISCE"  # Norma definisce un termine
    PREVEDE = "PREVEDE"  # Norma prevede un Effetto/Sanzione
    STABILISCE_TERMINE = "STABILISCE_TERMINE"  # Norma stabilisce un Termine
    REGOLA_PROCEDURA = "REGOLA_PROCEDURA"  # Norma regola una Procedura
    ATTRIBUISCE = "ATTRIBUISCE"  # Norma attribuisce Modalità a Soggetto

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI GERARCHICHE (Entità → Entità)
    # ─────────────────────────────────────────────────────────────────────────
    SPECIES = "SPECIES"  # Concetto è sottotipo di altro Concetto
    GENUS = "GENUS"  # Concetto è supertipo di altro Concetto
    IMPLICA = "IMPLICA"  # Concetto implica altro Concetto
    ESCLUDE = "ESCLUDE"  # Concetto esclude altro Concetto

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI TRA PRINCIPI
    # ─────────────────────────────────────────────────────────────────────────
    BILANCIA_CON = "BILANCIA_CON"  # Principio in tensione con altro Principio
    DEROGA = "DEROGA"  # Principio deroga altro Principio
    SPECIFICA = "SPECIFICA"  # Principio specifica altro Principio

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI CAUSALI
    # ─────────────────────────────────────────────────────────────────────────
    CAUSA = "CAUSA"  # Fatto/Atto causa Effetto
    PRESUPPONE = "PRESUPPONE"  # Effetto presuppone Fatto
    GENERA = "GENERA"  # Responsabilità genera Obbligo di risarcimento

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI SOGGETTIVE
    # ─────────────────────────────────────────────────────────────────────────
    TITOLARE_DI = "TITOLARE_DI"  # Soggetto è titolare di Diritto/Obbligo
    CONTROPARTE = "CONTROPARTE"  # Soggetto è controparte di altro Soggetto
    ASSUME_RUOLO = "ASSUME_RUOLO"  # Soggetto assume Ruolo in contesto

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI PROCEDURALI
    # ─────────────────────────────────────────────────────────────────────────
    FASE_DI = "FASE_DI"  # Atto è fase di Procedura
    PRECEDE = "PRECEDE"  # Fase precede altra Fase
    ATTIVA = "ATTIVA"  # Fatto attiva Termine

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI DOTTRINA/GIURISPRUDENZA
    # ─────────────────────────────────────────────────────────────────────────
    COMMENTA = "COMMENTA"  # Dottrina commenta Norma
    SPIEGA = "SPIEGA"  # Dottrina spiega Concetto/Principio
    INTERPRETA = "INTERPRETA"  # AttoGiudiziario interpreta Norma
    APPLICA = "APPLICA"  # AttoGiudiziario/Caso applica Principio
    ILLUSTRA = "ILLUSTRA"  # Caso illustra Concetto

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI RIMEDI
    # ─────────────────────────────────────────────────────────────────────────
    TUTELA = "TUTELA"  # Rimedio tutela Diritto
    REAGISCE_A = "REAGISCE_A"  # Rimedio reagisce a Violazione
    ECCEZIONE_A = "ECCEZIONE_A"  # Eccezione deroga Regola

    # ─────────────────────────────────────────────────────────────────────────
    # RELAZIONI GENERICHE (fallback)
    # ─────────────────────────────────────────────────────────────────────────
    CORRELATO = "CORRELATO"  # Relazione generica


@dataclass
class EnrichmentContent:
    """
    Contenuto da processare per estrazione entità.

    Rappresenta un chunk di testo proveniente da una fonte
    (Brocardi, manuale, etc.) pronto per l'estrazione LLM.

    Attributes:
        id: Identificativo unico (es. "brocardi:1337:spiegazione")
        text: Testo da cui estrarre entità
        article_refs: URN degli articoli citati/correlati
        source: Nome della fonte (es. "brocardi", "manuale:Torrente")
        content_type: Tipo di contenuto (spiegazione, ratio, capitolo)
        metadata: Metadata aggiuntivi dalla fonte
    """
    id: str
    text: str
    article_refs: List[str]
    source: str
    content_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedEntity:
    """
    Entità estratta da LLM.

    Rappresenta un concetto, principio o definizione identificato
    dall'LLM nel testo di input.

    Attributes:
        nome: Nome dell'entità (es. "buona fede")
        tipo: Tipo di entità (concetto, principio, definizione)
        descrizione: Descrizione/definizione estratta
        articoli_correlati: Articoli del codice menzionati
        ambito: Ambito giuridico (es. "diritto_civile", "obbligazioni")
        fonte: Fonte da cui è stata estratta
        confidence: Confidenza dell'estrazione (0.0-1.0)
        raw_context: Contesto originale da cui è stata estratta
    """
    nome: str
    tipo: EntityType
    descrizione: str = ""
    articoli_correlati: List[str] = field(default_factory=list)
    ambito: str = "diritto_civile"
    fonte: str = ""
    confidence: float = 1.0
    raw_context: str = ""

    @property
    def normalized_nome(self) -> str:
        """Nome normalizzato per deduplicazione."""
        return self.nome.lower().strip().replace(" ", "_")

    @property
    def node_id(self) -> str:
        """ID del nodo nel grafo."""
        return f"{self.tipo.value}:{self.normalized_nome}"


@dataclass
class ExtractedRelation:
    """
    Relazione estratta da LLM.

    Rappresenta una relazione tra entità o tra entità e norme
    identificata dall'LLM.

    Attributes:
        source_id: ID dell'entità/nodo sorgente
        target_id: ID dell'entità/nodo target
        relation_type: Tipo di relazione
        fonte: Fonte da cui è stata estratta
        confidence: Confidenza dell'estrazione
    """
    source_id: str
    target_id: str
    relation_type: RelationType
    fonte: str = ""
    confidence: float = 1.0


@dataclass
class LinkedEntity:
    """
    Entità dopo il processo di linking/dedup.

    Contiene le informazioni finali pronte per la scrittura
    nel grafo, incluso il flag se è nuova o merge.

    Attributes:
        entity: Entità estratta originale
        node_id: ID finale del nodo nel grafo
        is_new: True se è un nuovo nodo, False se merge
        merged_from: Lista fonti se è un merge
        final_descrizione: Descrizione finale (dopo merge)
    """
    entity: ExtractedEntity
    node_id: str
    is_new: bool = True
    merged_from: List[str] = field(default_factory=list)
    final_descrizione: str = ""

    def __post_init__(self):
        if not self.final_descrizione:
            self.final_descrizione = self.entity.descrizione


@dataclass
class EnrichmentStats:
    """
    Statistiche di un'esecuzione di enrichment.

    Traccia tutte le 17 tipologie di entità estraibili più Dottrina.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Contatori per tipo (created/merged)
    # ─────────────────────────────────────────────────────────────────────────

    # Core (priorità 1)
    concepts_created: int = 0
    concepts_merged: int = 0
    principles_created: int = 0
    principles_merged: int = 0
    definitions_created: int = 0
    definitions_merged: int = 0

    # Soggetti (priorità 2)
    subjects_created: int = 0
    subjects_merged: int = 0
    roles_created: int = 0
    roles_merged: int = 0
    modalities_created: int = 0
    modalities_merged: int = 0

    # Fatti e atti (priorità 3)
    facts_created: int = 0
    facts_merged: int = 0
    acts_created: int = 0
    acts_merged: int = 0
    procedures_created: int = 0
    procedures_merged: int = 0
    terms_created: int = 0
    terms_merged: int = 0
    effects_created: int = 0
    effects_merged: int = 0
    responsibilities_created: int = 0
    responsibilities_merged: int = 0
    remedies_created: int = 0
    remedies_merged: int = 0

    # Avanzati (priorità 4)
    sanctions_created: int = 0
    sanctions_merged: int = 0
    cases_created: int = 0
    cases_merged: int = 0
    exceptions_created: int = 0
    exceptions_merged: int = 0
    clauses_created: int = 0
    clauses_merged: int = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Relazioni e Dottrina
    # ─────────────────────────────────────────────────────────────────────────
    relations_created: int = 0
    dottrina_created: int = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Errori
    # ─────────────────────────────────────────────────────────────────────────
    extraction_errors: int = 0
    linking_errors: int = 0
    write_errors: int = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Mapping tipo → attributo (per update dinamico)
    # ─────────────────────────────────────────────────────────────────────────
    _TYPE_TO_ATTR: Dict[str, str] = field(default_factory=lambda: {
        "concetto": "concepts",
        "principio": "principles",
        "definizione": "definitions",
        "soggetto": "subjects",
        "ruolo": "roles",
        "modalita": "modalities",
        "fatto": "facts",
        "atto": "acts",
        "procedura": "procedures",
        "termine": "terms",
        "effetto": "effects",
        "responsabilita": "responsibilities",
        "rimedio": "remedies",
        "sanzione": "sanctions",
        "caso": "cases",
        "eccezione": "exceptions",
        "clausola": "clauses",
    }, repr=False)

    def increment(self, entity_type: str, created: bool = True) -> None:
        """
        Incrementa il contatore per un tipo di entità.

        Args:
            entity_type: Valore EntityType.value (es. "concetto")
            created: True per _created, False per _merged
        """
        attr_base = self._TYPE_TO_ATTR.get(entity_type)
        if attr_base:
            suffix = "_created" if created else "_merged"
            attr_name = f"{attr_base}{suffix}"
            current = getattr(self, attr_name, 0)
            setattr(self, attr_name, current + 1)

    @property
    def total_entities_created(self) -> int:
        """Totale entità create (tutte le tipologie)."""
        return (
            self.concepts_created +
            self.principles_created +
            self.definitions_created +
            self.subjects_created +
            self.roles_created +
            self.modalities_created +
            self.facts_created +
            self.acts_created +
            self.procedures_created +
            self.terms_created +
            self.effects_created +
            self.responsibilities_created +
            self.remedies_created +
            self.sanctions_created +
            self.cases_created +
            self.exceptions_created +
            self.clauses_created
        )

    @property
    def total_entities_merged(self) -> int:
        """Totale entità merge (dedup) (tutte le tipologie)."""
        return (
            self.concepts_merged +
            self.principles_merged +
            self.definitions_merged +
            self.subjects_merged +
            self.roles_merged +
            self.modalities_merged +
            self.facts_merged +
            self.acts_merged +
            self.procedures_merged +
            self.terms_merged +
            self.effects_merged +
            self.responsibilities_merged +
            self.remedies_merged +
            self.sanctions_merged +
            self.cases_merged +
            self.exceptions_merged +
            self.clauses_merged
        )

    @property
    def total_errors(self) -> int:
        """Totale errori."""
        return (
            self.extraction_errors +
            self.linking_errors +
            self.write_errors
        )

    def by_priority(self, priority: int) -> Dict[str, int]:
        """Restituisce contatori per priorità."""
        if priority == 1:
            return {
                "concetti": self.concepts_created,
                "principi": self.principles_created,
                "definizioni": self.definitions_created,
            }
        elif priority == 2:
            return {
                "soggetti": self.subjects_created,
                "ruoli": self.roles_created,
                "modalità": self.modalities_created,
            }
        elif priority == 3:
            return {
                "fatti": self.facts_created,
                "atti": self.acts_created,
                "procedure": self.procedures_created,
                "termini": self.terms_created,
                "effetti": self.effects_created,
                "responsabilità": self.responsibilities_created,
                "rimedi": self.remedies_created,
            }
        elif priority == 4:
            return {
                "sanzioni": self.sanctions_created,
                "casi": self.cases_created,
                "eccezioni": self.exceptions_created,
                "clausole": self.clauses_created,
            }
        return {}


@dataclass
class EnrichmentError:
    """Errore durante enrichment."""

    content_id: str
    phase: str  # "extraction", "linking", "writing"
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    recoverable: bool = True


@dataclass
class EnrichmentResult:
    """
    Risultato finale di una pipeline di enrichment.

    Contiene statistiche, errori e informazioni sulle entità create.

    Example:
        >>> result = await kg.enrich(config)
        >>> print(f"Creati {result.stats.total_entities_created} entità")
        >>> if result.errors:
        ...     print(f"Con {len(result.errors)} errori")
    """

    # Statistiche
    stats: EnrichmentStats = field(default_factory=EnrichmentStats)

    # Errori
    errors: List[EnrichmentError] = field(default_factory=list)

    # Tracking
    contents_processed: int = 0
    contents_skipped: int = 0  # Già processati (checkpoint)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Dettagli (per debug)
    entities_created: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True se completato senza errori critici."""
        return self.stats.total_errors == 0

    @property
    def duration_seconds(self) -> Optional[float]:
        """Durata in secondi."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_error(
        self,
        content_id: str,
        phase: str,
        error: Exception
    ) -> None:
        """Aggiungi un errore al risultato."""
        self.errors.append(EnrichmentError(
            content_id=content_id,
            phase=phase,
            error_type=type(error).__name__,
            error_message=str(error),
        ))

        # Aggiorna contatori
        if phase == "extraction":
            self.stats.extraction_errors += 1
        elif phase == "linking":
            self.stats.linking_errors += 1
        elif phase == "writing":
            self.stats.write_errors += 1

    def summary(self) -> str:
        """Restituisce un riepilogo testuale con tutte le 17 tipologie."""
        s = self.stats
        lines = [
            "═" * 60,
            "ENRICHMENT RESULT",
            "═" * 60,
            f"Contents processati: {self.contents_processed}",
            f"Contents skippati: {self.contents_skipped}",
            "",
            "─" * 60,
            "ENTITÀ CORE (priorità 1):",
            f"  Concetti:    {s.concepts_created:>4} (+{s.concepts_merged} merge)",
            f"  Principi:    {s.principles_created:>4} (+{s.principles_merged} merge)",
            f"  Definizioni: {s.definitions_created:>4} (+{s.definitions_merged} merge)",
            "",
            "SOGGETTI (priorità 2):",
            f"  Soggetti:    {s.subjects_created:>4} (+{s.subjects_merged} merge)",
            f"  Ruoli:       {s.roles_created:>4} (+{s.roles_merged} merge)",
            f"  Modalità:    {s.modalities_created:>4} (+{s.modalities_merged} merge)",
            "",
            "FATTI/ATTI (priorità 3):",
            f"  Fatti:       {s.facts_created:>4} (+{s.facts_merged} merge)",
            f"  Atti:        {s.acts_created:>4} (+{s.acts_merged} merge)",
            f"  Procedure:   {s.procedures_created:>4} (+{s.procedures_merged} merge)",
            f"  Termini:     {s.terms_created:>4} (+{s.terms_merged} merge)",
            f"  Effetti:     {s.effects_created:>4} (+{s.effects_merged} merge)",
            f"  Responsabil: {s.responsibilities_created:>4} (+{s.responsibilities_merged} merge)",
            f"  Rimedi:      {s.remedies_created:>4} (+{s.remedies_merged} merge)",
            "",
            "AVANZATE (priorità 4):",
            f"  Sanzioni:    {s.sanctions_created:>4} (+{s.sanctions_merged} merge)",
            f"  Casi:        {s.cases_created:>4} (+{s.cases_merged} merge)",
            f"  Eccezioni:   {s.exceptions_created:>4} (+{s.exceptions_merged} merge)",
            f"  Clausole:    {s.clauses_created:>4} (+{s.clauses_merged} merge)",
            "",
            "─" * 60,
            f"TOTALE ENTITÀ: {s.total_entities_created} create, {s.total_entities_merged} merge",
            f"Dottrina:      {s.dottrina_created}",
            f"Relazioni:     {s.relations_created}",
            "─" * 60,
        ]

        if self.errors:
            lines.extend([
                f"ERRORI: {len(self.errors)}",
                *[f"  - [{e.phase}] {e.content_id}: {e.error_message}"
                  for e in self.errors[:5]],
            ])
            if len(self.errors) > 5:
                lines.append(f"  ... e altri {len(self.errors) - 5}")
        else:
            lines.append("Nessun errore ✓")

        if self.duration_seconds:
            lines.append(f"\nDurata: {self.duration_seconds:.1f}s")

        lines.append("═" * 60)
        return "\n".join(lines)
