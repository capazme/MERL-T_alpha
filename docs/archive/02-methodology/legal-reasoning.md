# Legal Reasoning Framework

## Indice

1. [Introduzione](#introduzione)
2. [Architettura - Scenario: HYBRID + Iterative + Traced + RLCF](#architettura-scenario-14)
3. [Query Understanding](#query-understanding)
4. [KG Enrichment](#kg-enrichment)
5. [LLM Router](#llm-router)
6. [Retrieval Agents](#retrieval-agents)
7. [Reasoning Experts](#reasoning-experts)
8. [Iterative Loop](#iterative-loop)
9. [Synthesis](#synthesis)
10. [Traceability System](#traceability-system)
11. [RLCF Integration](#rlcf-integration)
12. [LangGraph Orchestration](#langgraph-orchestration)
13. [Complete Examples](#complete-examples)
14. [Bootstrap Strategy](#bootstrap-strategy)

---

## Introduzione

Questo documento descrive il **cuore dell'architettura MERL-T**: il sistema di ragionamento giuridico che orchestra il retrieval di informazioni e la generazione di risposte giuridicamente fondate.

### Obiettivi del Sistema

Il sistema di legal reasoning deve:

1. **Comprendere** query in linguaggio naturale italiano, estraendo concetti giuridici anche quando non esplicitamente menzionati
2. **Arricchire** la comprensione mappando concetti a norme rilevanti tramite il Knowledge Graph
3. **Pianificare** retrieval ottimale da fonti multiple (KG, API, VectorDB)
4. **Ragionare** usando metodologie giuridiche distinte e complementari
5. **Iterare** quando servono informazioni aggiuntive
6. **Sintetizzare** risposte coerenti e ben fondate
7. **Tracciare** ogni decisione per accountability
8. **Apprendere** da feedback della comunità (RLCF)

### Principi Architetturali

**Separazione delle Responsabilità**:
- **Retrieval Agents**: Recuperano dati da fonti diverse (tecnici, non ragionano)
- **Reasoning Experts**: Applicano metodologie giuridiche (ragionano, non recuperano dati)
- **Router**: Decide chi attivare e quando
- **Synthesizer**: Combina output multipli in risposta coerente

**Separazione KG vs API**:
- **Knowledge Graph** (Neo4j): SOLO metadata e relazioni (norme ↔ concetti, concetti ↔ concetti)
- **API** (Akoma Ntoso): SOLO testi completi delle norme (versione vigente o storica)
- **Motivazione**: La legislazione italiana conta centinaia di migliaia di norme. Memorizzare tutti i testi è impraticabile. Il KG connette concetti a norme, l'API recupera il testo dinamicamente garantendo versione ufficiale e aggiornata.

**Separazione Epistemologica degli Experts**:
- Esperti separati per **metodologia giuridica**, non per dominio (no "esperto civile" vs "esperto penale")
- Ogni esperto applica un approccio interpretativo diverso
- Cross-domain applicability: tutti gli esperti possono ragionare su qualsiasi materia

---

## Architettura

### Scenario: HYBRID + Iterative + Traced + RLCF

Lo **Scenario 14** è l'architettura completa che integra:

- **HYBRID**: Retrieval Agents (tecnici) + Reasoning Experts (giuridici) separati
- **Iterative**: Loop di retrieval con stop criteria apprese
- **Traced**: Traceability completa ad ogni step
- **RLCF**: Reinforcement Learning from Community Feedback integrato nativamente

### Flusso Architetturale Completo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                     │
│          "È valido un contratto firmato da un sedicenne?"               │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   ↓
┌───────────────────────────────────────────────────────────────────────────┐
│  [1] QUERY UNDERSTANDING                                                  │
│  ────────────────────────────────────────────────────────────────────    │
│  Componente ML-based per estrazione entità e concetti                    │
│                                                                           │
│  Input: "È valido un contratto firmato da un sedicenne?"                 │
│                                                                           │
│  Processing:                                                              │
│  • Entity Extraction (NER): "contratto", "sedicenne", "16 anni"         │
│  • Concept Mapping: "capacità_di_agire", "validità_contrattuale"        │
│  • Intent Classification: "validità_atto"                                │
│  • Temporal Extraction: "current" (nessun riferimento temporale)         │
│                                                                           │
│  Output:                                                                  │
│  {                                                                        │
│    "entities": {                                                          │
│      "legal_object": "contratto",                                        │
│      "person": {"age": 16, "type": "natural_person"},                   │
│      "action": "firma_contratto"                                         │
│    },                                                                     │
│    "concepts": [                                                          │
│      "capacità_di_agire",                                                │
│      "validità_contrattuale",                                            │
│      "minore_età"                                                        │
│    ],                                                                     │
│    "intent": "validità_atto",                                            │
│    "temporal_scope": "current",                                          │
│    "constraints": []                                                      │
│  }                                                                        │
│                                                                           │
│  ⚡ Trace Point: QU-001                                                  │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   ↓
┌───────────────────────────────────────────────────────────────────────────┐
│  [2] KG ENRICHMENT ★ STEP CRUCIALE                                       │
│  ────────────────────────────────────────────────────────────────────    │
│  Consulta il Knowledge Graph per mappare concetti → norme                │
│                                                                           │
│  Input: concepts from Query Understanding                                 │
│  - "capacità_di_agire"                                                   │
│  - "validità_contrattuale"                                               │
│  - "minore_età"                                                          │
│                                                                           │
│  Cypher Query 1: Map concepts to norms                                   │
│  ─────────────────────────────────────────                               │
│  MATCH (c:LegalConcept)<-[:REGULATES]-(a:Article)                        │
│  WHERE c.name IN ['capacità_di_agire', 'validità_contrattuale',         │
│                    'minore_età']                                         │
│  RETURN DISTINCT                                                          │
│    a.id AS norm_id,                                                       │
│    a.title AS norm_title,                                                │
│    a.hierarchy AS source,                                                │
│    c.name AS concept                                                      │
│  ORDER BY a.hierarchy DESC                                               │
│  LIMIT 20                                                                 │
│                                                                           │
│  Results:                                                                 │
│  ┌─────────────┬──────────────────────────┬────────────┬───────────────┐│
│  │ norm_id     │ norm_title               │ source     │ concept       ││
│  ├─────────────┼──────────────────────────┼────────────┼───────────────┤│
│  │ cc-art-2    │ Maggiore età             │ codice_civ │ capacità_agire││
│  │ cc-art-322  │ Annullabilità atti       │ codice_civ │ capacità_agire││
│  │ cc-art-1418 │ Cause di nullità         │ codice_civ │ validità_contr││
│  │ cc-art-1425 │ Annullabilità contratto  │ codice_civ │ validità_contr││
│  └─────────────┴──────────────────────────┴────────────┴───────────────┘│
│                                                                           │
│  Cypher Query 2: Find related concepts                                   │
│  ───────────────────────────────────────                                 │
│  MATCH (c1:LegalConcept)-[:RELATED_TO]-(c2:LegalConcept)                │
│  WHERE c1.name IN ['capacità_di_agire', 'validità_contrattuale']        │
│  RETURN DISTINCT c2.name, c2.description                                 │
│  LIMIT 10                                                                 │
│                                                                           │
│  Results:                                                                 │
│  - "emancipazione" (eccezione a capacità limitata)                       │
│  - "rappresentanza_legale" (sostituzione capacità)                       │
│  - "amministrazione_sostegno" (limitazione capacità adulto)              │
│                                                                           │
│  Cypher Query 3: Find relevant jurisprudence                             │
│  ────────────────────────────────────────────────                        │
│  MATCH (c:LegalConcept)<-[:APPLIES]-(j:Jurisprudence)                   │
│  WHERE c.name IN ['capacità_di_agire', 'validità_contrattuale']         │
│  RETURN j.id, j.court, j.date, j.massima                                 │
│  ORDER BY j.date DESC, j.authority_score DESC                            │
│  LIMIT 5                                                                  │
│                                                                           │
│  Results:                                                                 │
│  - Cass. 18210/2015: "Annullabilità atti minore senza rappresentanza"   │
│  - Cass. 3281/2019: "Rappresentanza genitoriale acquisto immobile"      │
│  - Cass. 12450/2018: "Ratifica atto minore al raggiungimento maggiore"  │
│                                                                           │
│  Output (enriched context):                                              │
│  {                                                                        │
│    "mapped_norms": [                                                      │
│      {"id": "cc-art-2", "title": "Maggiore età", "source": "cc"},       │
│      {"id": "cc-art-322", "title": "Annullabilità", "source": "cc"},    │
│      {"id": "cc-art-1418", "title": "Nullità", "source": "cc"},         │
│      {"id": "cc-art-1425", "title": "Annullabilità", "source": "cc"}    │
│    ],                                                                     │
│    "related_concepts": [                                                  │
│      {"name": "emancipazione", "norm_ref": "cc-art-390"},               │
│      {"name": "rappresentanza_legale", "norm_ref": "cc-art-320"}        │
│    ],                                                                     │
│    "jurisprudence_clusters": [                                            │
│      {"id": "Cass-18210-2015", "relevance": 0.92},                      │
│      {"id": "Cass-3281-2019", "relevance": 0.87}                        │
│    ],                                                                     │
│    "constitutional_refs": [],                                             │
│    "hierarchical_context": {                                              │
│      "codice_civile": ["cc-art-2", "cc-art-322", "cc-art-1418"]        │
│    }                                                                      │
│  }                                                                        │
│                                                                           │
│  ⚡ Trace Point: KGE-001                                                 │
│  ⏱ Performance: ~50ms (read-only graph queries, no LLM)                 │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   ↓
┌───────────────────────────────────────────────────────────────────────────┐
│  [3] LLM ROUTER                                                           │
│  ────────────────────────────────────────────────────────────────────    │
│  Pianifica retrieval e reasoning basandosi su enriched context           │
│                                                                           │
│  [... continua nella prossima sezione ...]                               │
└───────────────────────────────────────────────────────────────────────────┘
```

### Perché KG Enrichment è Cruciale

**Problema risolto**: Se l'utente chiede "È valido un contratto firmato da un sedicenne?" NON menziona esplicitamente le norme (Art. 2 c.c., Art. 322 c.c.). Il Router da solo non può "inventare" quali norme recuperare.

**Soluzione**: Il KG Enrichment fa da **ponte** tra concetti estratti dalla query e norme concrete presenti nel sistema giuridico:

1. **Query Understanding** estrae concetti giuridici impliciti ("capacità_di_agire", "validità_contrattuale")
2. **KG Enrichment** consulta il grafo per mappare quei concetti a norme concrete (Art. 2, Art. 322)
3. **Router** ora ha informazioni concrete per pianificare retrieval dettagliato

**Vantaggi**:
- ✅ Veloce (~50ms, solo query Cypher read-only, no LLM)
- ✅ Deterministico (stesso concept → stesse norme)
- ✅ Tracciabile (log completo delle query e risultati)
- ✅ Estendibile (quando KG cresce, enrichment migliora automaticamente)

---

## Query Understanding

### Overview

Il componente **Query Understanding** è responsabile di:

1. **Estrarre entità** dal testo della query (nomi, date, numeri, riferimenti normativi espliciti)
2. **Mappare concetti giuridici** anche quando impliciti
3. **Classificare intent** (cosa vuole l'utente: interpretazione, validità, conseguenze, ecc.)
4. **Estrarre vincoli temporali** (multivigenza, periodi specifici)

**Nota**: Per dettagli implementativi completi, vedere [query-understanding.md](./query-understanding.md). Qui forniamo overview funzionale nel contesto del legal reasoning.

### Architettura Adaptive & Self-Evolving

Il Query Understanding usa **architettura adattiva** che **evolve automaticamente** senza dizionari hardcodati:

```
┌────────────────────────────────────────────────────────────────┐
│               QUERY UNDERSTANDING PIPELINE                      │
└────────────────────────────────────────────────────────────────┘

Query Input: "È valido un contratto firmato da un sedicenne?"
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. ABBREVIATION EXPANSION (Auto-Learning)                       │
│ ──────────────────────────────────────────────────────────────│
│ Strategy: Auto-learning da corpus + feedback RLCF              │
│                                                                 │
│ Corpus-Extracted Dictionary (auto-updated):                    │
│   "c.c." → "codice civile" (freq: 15234, confidence: 0.98)    │
│   "TFR" → "Trattamento Fine Rapporto" (freq: 8932, conf: 0.95)│
│   "CCNL" → "Contratto Collettivo Nazionale Lavoro" (freq: ...) │
│                                                                 │
│ Feedback Loop:                                                  │
│   User correction → update dictionary + retrain extractor      │
│                                                                 │
│ Output: "È valido un contratto firmato da un sedicenne?"       │
│         (no abbreviations detected in this query)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ENTITY EXTRACTION (Legal NER)                                │
│ ──────────────────────────────────────────────────────────────│
│ Model: BERT fine-tuned on Italian legal corpus                 │
│                                                                 │
│ Entities Detected:                                              │
│   - "contratto" → LEGAL_OBJECT                                  │
│   - "sedicenne" → PERSON (age: 16, inferred)                    │
│   - "firmato" → ACTION                                          │
│                                                                 │
│ Output JSON:                                                    │
│ {                                                               │
│   "legal_object": "contratto",                                  │
│   "person": {"age": 16, "descriptor": "sedicenne"},            │
│   "action": "firma_contratto"                                   │
│ }                                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CONCEPT MAPPING (Hybrid: LLM + KG Validation)               │
│ ──────────────────────────────────────────────────────────────│
│ Strategy: ZERO dizionari hardcodati, 100% adaptive             │
│                                                                 │
│ Step 3.1: LLM Concept Extraction                               │
│ ────────────────────────────────────────────────────────────  │
│ Prompt to LLM:                                                  │
│   "Estrai concetti giuridici dalla query: 'È valido un        │
│    contratto firmato da un sedicenne?'                         │
│    Contesto: diritto civile italiano, focus su capacità e      │
│    validità."                                                   │
│                                                                 │
│ LLM Output (candidate concepts):                                │
│   ["capacità_di_agire", "validità_contrattuale",               │
│    "minore_età", "contratto", "annullabilità"]                 │
│                                                                 │
│ Step 3.2: KG Validation                                         │
│ ────────────────────────────────────────────────────────────  │
│ Query Neo4j KG:                                                 │
│   MATCH (c:LegalConcept)                                        │
│   WHERE c.name IN ["capacità_di_agire", ...]                   │
│   RETURN c                                                      │
│                                                                 │
│ Validation Result:                                              │
│   ✅ "capacità_di_agire" → EXISTS in KG                         │
│   ✅ "validità_contrattuale" → EXISTS in KG                     │
│   ✅ "minore_età" → EXISTS in KG                                │
│   ❌ "contratto" → Too generic, filter out                      │
│   ✅ "annullabilità" → EXISTS in KG                             │
│                                                                 │
│ Step 3.3: Self-Evolution (concetti nuovi)                      │
│ ────────────────────────────────────────────────────────────  │
│ IF concept NOT in KG:                                           │
│   1. Check if legitimate legal concept (LLM validation)        │
│   2. Mark for expert review (human-in-the-loop)                │
│   3. If validated → ADD to KG + connect to norms               │
│                                                                 │
│ Example: "diritto_oblio_digitale" (nuovo concetto 2014)        │
│   → LLM: "Yes, valid concept (GDPR Art. 17)"                   │
│   → Expert review: APPROVED                                     │
│   → KG update: CREATE (:LegalConcept {name: "diritto_oblio_digitale"})│
│   → Connects to: GDPR Art. 17, Corte UE C-131/12               │
│                                                                 │
│ Output Final Concepts:                                          │
│   ["capacità_di_agire", "validità_contrattuale",               │
│    "minore_età", "annullabilità"]                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. INTENT CLASSIFICATION (Multi-Label)                          │
│ ──────────────────────────────────────────────────────────────│
│ Model: BERT multi-label classifier                              │
│                                                                 │
│ Intents Detected:                                               │
│   - "validità_atto" (confidence: 0.92)                          │
│   - "conseguenze_giuridiche" (confidence: 0.34) ← sotto soglia │
│                                                                 │
│ Threshold: 0.5 → Only "validità_atto" selected                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. TEMPORAL EXTRACTION                                          │
│ ──────────────────────────────────────────────────────────────│
│ No temporal references in query                                 │
│ → Default: current law (vigente oggi)                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. COMPLEXITY SCORING                                           │
│ ──────────────────────────────────────────────────────────────│
│ Features:                                                       │
│   - Query length: 50 chars → 0.3                                │
│   - Entities count: 3 → 0.4                                     │
│   - Concepts count: 4 → 0.5                                     │
│   - Intent complexity: "validità_atto" → 0.6                    │
│                                                                 │
│ ML Model (Random Forest):                                       │
│   Weighted average → Complexity: 0.68                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ FINAL OUTPUT │
                    └──────────────┘
```

**Output JSON Strutturato**:
```json
{
  "original_query": "È valido un contratto firmato da un sedicenne?",
  "entities": {
    "legal_object": "contratto",
    "person": {
      "age": 16,
      "descriptor": "sedicenne"
    },
    "action": "firma_contratto"
  },
  "concepts": [
    {"name": "capacità_di_agire", "confidence": 0.92, "source": "llm_extracted"},
    {"name": "validità_contrattuale", "confidence": 0.88, "source": "llm_extracted"},
    {"name": "minore_età", "confidence": 0.85, "source": "llm_extracted"},
    {"name": "annullabilità", "confidence": 0.79, "source": "llm_extracted"}
  ],
  "intent": "validità_atto",
  "intent_confidence": 0.92,
  "temporal_scope": {
    "type": "current",
    "reference_date": "2025-01-02"
  },
  "complexity": 0.68,
  "trace_id": "QU_20250102_143022_abc"
}
```

### Adaptive Components Details

#### 1. Abbreviation Expansion (Auto-Learning da Corpus)

**Strategia**: Il sistema costruisce **automaticamente** un dizionario di abbreviazioni analizzando il corpus normativo.

**Pattern Extraction**:
```
Analisi corpus (Costituzione, Codici, Leggi):
  Pattern: "Termine Completo (SIGLA)" o "SIGLA (Termine Completo)"

  Esempi estratti:
  - "Codice Civile (c.c.)" → sigla: "c.c.", espansione: "Codice Civile", freq: 15234
  - "Trattamento di Fine Rapporto (TFR)" → sigla: "TFR", espansione: "Trattamento di Fine Rapporto", freq: 8932
  - "Contratto Collettivo Nazionale di Lavoro (CCNL)" → freq: 6721
```

**Auto-Update via Feedback RLCF**:
```
Scenario: User query "Il TFR va pagato entro quanto?"

  Step 1: Sistema espande "TFR" → "Trattamento Fine Rapporto" (confidence 0.95)
  Step 2: User feedback: "Espansione corretta"
  Step 3: RLCF signal → +1 reward → confidence aumenta a 0.96

  Step 1 alternativo: Sistema sbaglia "CCNL" → "Codice Civile Nazionale Lavoro"
  Step 2: User feedback: "Sbagliato, è 'Contratto Collettivo Nazionale Lavoro'"
  Step 3: RLCF signal → -1 reward → dizionario aggiornato → retrain
```

**Dictionary Structure** (auto-generated):
```json
{
  "abbreviations": [
    {
      "sigla": "c.c.",
      "espansione": "Codice Civile",
      "freq_corpus": 15234,
      "confidence": 0.98,
      "last_updated": "2025-01-02",
      "feedback_count": 234
    },
    {
      "sigla": "TFR",
      "espansione": "Trattamento Fine Rapporto",
      "freq_corpus": 8932,
      "confidence": 0.95,
      "context_domain": "diritto_lavoro",
      "ambiguous": false
    },
    {
      "sigla": "CCNL",
      "espansione": "Contratto Collettivo Nazionale Lavoro",
      "freq_corpus": 6721,
      "confidence": 0.94,
      "feedback_corrections": 3
    }
  ]
}
```

#### 2. Concept Mapping (Hybrid LLM + KG Validation)

**NO dizionari hardcodati**. Il sistema usa **LLM per estrarre concetti candidati** + **KG per validare/filtrare**.

**Tabella: Colloquiale → Concetti Giuridici** (esempi generati da LLM):

| Query Colloquiale | LLM Concepts (candidati) | KG Validation | Final Concepts |
|-------------------|--------------------------|---------------|----------------|
| "Un sedicenne può comprare casa?" | `capacità_di_agire`, `acquisto_immobile`, `contratto_compravendita`, `minore_età`, `immobile` | ✅✅✅✅❌ (immobile too generic) | `capacità_di_agire`, `acquisto_immobile`, `contratto_compravendita`, `minore_età` |
| "È legale licenziare una donna incinta?" | `licenziamento`, `tutela_maternità`, `discriminazione_genere`, `giusta_causa`, `gravidanza` | ✅✅✅✅❌ | `licenziamento`, `tutela_maternità`, `discriminazione_genere`, `giusta_causa` |
| "Posso disdire contratto telefonico?" | `recesso_contrattuale`, `contratto_consumo`, `diritto_ripensamento`, `telecomunicazioni` | ✅✅✅❌ | `recesso_contrattuale`, `contratto_consumo`, `diritto_ripensamento` |

**Self-Evolution**: Quando LLM estrae concetto NON nel KG:

```
Example: Query su "diritto all'oblio digitale" (2014, concetto nuovo)

Step 1: LLM estrae "diritto_oblio_digitale"
Step 2: KG query → NOT FOUND
Step 3: LLM validation: "È un concetto giuridico legittimo? (GDPR Art. 17)"
        → LLM: "SÌ, concetto valido introdotto da GDPR 2016"
Step 4: Mark for expert review (human-in-the-loop)
Step 5: Expert approves → KG UPDATE
        CREATE (:LegalConcept {
          name: "diritto_oblio_digitale",
          introduced_date: "2016-05-24",
          source: "GDPR Art. 17"
        })
Step 6: Connect to norms:
        MATCH (c:LegalConcept {name: "diritto_oblio_digitale"}),
              (a:Article {id: "gdpr_art_17"})
        CREATE (a)-[:REGULATES]->(c)
```

**RLCF-Driven Expansion**: Quando user corregge concept mapping errato:

```
Scenario: Query "Il TFR spetta anche ai collaboratori?"

System Output (errato):
  concepts: ["TFR", "collaboratori", "subordinazione_lavoro"]

User Feedback: "Manca 'collaborazione_coordinata_continuativa'"

RLCF Signal:
  - Genera training example:
    (query: "TFR collaboratori", concepts_gold: [..., "collaborazione_coordinata_continuativa"])
  - Aggiorna LLM prompt con few-shot example
  - Next similar query → sistema include concetto corretto
```

#### 3. Intent Classification (Multi-Label BERT)

**Intents** (non hardcodati, apprendibili con RLCF):

| Intent | Descrizione | Esempi Query |
|--------|-------------|--------------|
| `validità_atto` | Validità/nullità/annullabilità | "È valido contratto minorenne?" |
| `interpretazione_norma` | Significato norma | "Cosa significa Art. 2043 c.c.?" |
| `conseguenze_giuridiche` | Effetti giuridici | "Cosa succede se non pago affitto?" |
| `requisiti_procedurali` | Requisiti formali | "Quali documenti servono per testamento?" |
| `bilanciamento_diritti` | Conflitto diritti | "Prevale libertà espressione o privacy?" |
| `evoluzione_giurisprudenziale` | Orientamento giudici | "Come interpreta Cassazione Art. X?" |
| `lacune_ordinamento` | Materia non regolata | "Chi è responsabile per danno da IA?" |

**RLCF Evolution**: Nuovi intent emergono da feedback:

```
Example: Dopo 6 mesi, molte query su "diritto digitale" senza intent specifico

RLCF Analysis:
  - Cluster di 150 query con intent="altro" (catch-all)
  - Pattern comune: "algoritmo", "IA", "dati personali", "cookies"
  - Proposta: Creare nuovo intent "conformità_digitale"

Human Review: APPROVED

System Update:
  - Aggiungi intent "conformità_digitale" al classifier
  - Ritraina BERT su 150 query annotate manualmente
  - Deploy nuovo modello v2.1
```

#### 4. Temporal Extraction (NER + Knowledge Base)

**Gestione Multivigenza** e riferimenti temporali impliciti:

| Query Temporal Reference | Tipo | Normalizzato | Source |
|--------------------------|------|--------------|--------|
| "Art. 2 c.c." (no data) | current | 2025-01-02 (oggi) | default |
| "Art. 2 c.c. nel 1990" | explicit_past | 1990-01-01 | NER |
| "Durante lockdown" | implicit_period | 2020-03-09 to 2020-05-18 | knowledge_base |
| "L. 194/1978 versione originale" | explicit_past | 1978-05-22 | NER + KB |

**Knowledge Base** per eventi impliciti:
```json
{
  "temporal_events": [
    {
      "name": "primo_lockdown",
      "aliases": ["lockdown", "primo lockdown covid", "chiusura 2020"],
      "start_date": "2020-03-09",
      "end_date": "2020-05-18",
      "source": "DPCM 9 marzo 2020"
    },
    {
      "name": "jobs_act_vigenza",
      "start_date": "2015-03-07",
      "source": "D.Lgs. 23/2015"
    }
  ]
}
```

#### 5. Complexity Scoring (ML Model)

**Features** per calcolo complessità (NO regole hardcoded):

```
ML Model: Random Forest Regression
Training Data: 500 query annotate con complexity manuale

Features:
  - query_length (chars)
  - entities_count
  - concepts_count
  - intent_complexity (learned weight per intent)
  - has_temporal_constraint (bool)
  - has_bilanciamento (bool)
  - avg_concept_specificity (es. "capacità_agire" più specifico di "contratto")

Output: Complexity score 0.0-1.0

Example:
  Query: "È valido contratto minorenne?"
  Features: {length: 50, entities: 3, concepts: 4, intent_complexity: 0.6, ...}
  → ML Model → Complexity: 0.68
```

### RLCF-Driven Continuous Evolution

**Feedback Loop Completo**:

```
┌─────────────────────────────────────────────────────────────┐
│ Week 1-N: PRODUCTION (Query Understanding in uso)           │
│ ─────────────────────────────────────────────────────────  │
│ - 500 query processate                                      │
│ - 200 feedback utenti (40% feedback rate)                   │
│   - 150 positive ("concept mapping corretto")              │
│   - 30 corrections ("manca concetto X")                     │
│   - 20 new abbreviations ("aggiungi sigla Y")               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Week N+1: TRAINING UPDATE                                   │
│ ─────────────────────────────────────────────────────────  │
│ 1. Abbreviation Dictionary Update:                          │
│    - Add 5 new abbreviations from corpus                    │
│    - Update confidence scores based on feedback             │
│                                                              │
│ 2. Concept Mapping LLM Prompt Enhancement:                  │
│    - Add 30 new few-shot examples from corrections          │
│    - Retrain prompt with RLCF signal                        │
│                                                              │
│ 3. KG Evolution:                                             │
│    - Add 3 new concepts validated by expert review          │
│    - Connect to 12 new norms                                │
│                                                              │
│ 4. Intent Classifier Retrain:                               │
│    - Fine-tune BERT on 200 new annotated queries            │
│    - Accuracy improvement: 85% → 87%                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Week N+1 Friday: A/B TEST                                   │
│ ─────────────────────────────────────────────────────────  │
│ - 10% traffic → new Query Understanding v2.1                │
│ - 90% traffic → stable v2.0                                 │
│ - Monitor: accuracy, latency, user satisfaction             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Week N+2: DEPLOY (if A/B positive)                          │
│ ─────────────────────────────────────────────────────────  │
│ - Gradual rollout: 10% → 50% → 100%                         │
│ - Version: v2.0 → v2.1                                       │
└─────────────────────────────────────────────────────────────┘
```

**Metriche Evolution** (esempio 6 mesi):

| Metrica | Fase 1 (Generic) | Fase 2 (Fine-tuned) | Fase 3 (RLCF Month 6) |
|---------|------------------|---------------------|----------------------|
| Concept Mapping Accuracy | 65% | 78% | 89% |
| Abbreviation Coverage | 120 sigles | 280 sigles | 520 sigles |
| Intent Classification Acc | 72% | 85% | 91% |
| KG Concepts Count | 450 | 680 | 1250 |
| User Satisfaction (QU) | 3.2/5 | 3.9/5 | 4.4/5 |

Questo output diventa input per **KG Enrichment**.

---

## KG Enrichment

### Overview

Il **KG Enrichment** è lo step architetturale che risolve il problema cruciale:

> "Come fa il Router a sapere quali norme recuperare se l'utente non le menziona esplicitamente nella query?"

**Risposta**: Consultando il Knowledge Graph per mappare i **concetti estratti** da Query Understanding alle **norme concrete** che li regolano.

### Responsabilità

1. **Concept-to-Norm Mapping**: Dato un insieme di concetti giuridici, trovare tutte le norme che li regolano
2. **Concept Expansion**: Trovare concetti correlati che potrebbero essere rilevanti
3. **Jurisprudence Discovery**: Identificare cluster di giurisprudenza rilevanti
4. **Hierarchical Context**: Capire gerarchia delle fonti (Costituzione > Legge > Regolamento)

### Architettura

```python
class KGEnrichmentEngine:
    """
    Arricchisce la comprensione della query consultando il Knowledge Graph

    Input: QueryUnderstanding (output di Query Understanding)
    Output: EnrichedContext (norme, concetti correlati, jurisprudence)

    Caratteristiche:
    - Read-only (nessuna modifica al grafo)
    - Veloce (~50ms per query tipica)
    - Deterministico (stessi concetti → stessi risultati)
    - No LLM (solo query Cypher)
    """

    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        self.query_templates = self._load_cypher_templates()

    def enrich(
        self,
        understanding: QueryUnderstanding
    ) -> EnrichedContext:
        """
        Arricchisce context consultando KG

        Args:
            understanding: Output di Query Understanding

        Returns:
            EnrichedContext con norme, concetti, jurisprudence
        """

        # Query parallele al grafo
        with self.driver.session() as session:
            # 1. Map concepts to norms
            mapped_norms = session.run(
                self.query_templates["concept_to_norm"],
                concepts=understanding.concepts
            ).data()

            # 2. Find related concepts
            related_concepts = session.run(
                self.query_templates["related_concepts"],
                concepts=understanding.concepts
            ).data()

            # 3. Find relevant jurisprudence
            jurisprudence = session.run(
                self.query_templates["relevant_jurisprudence"],
                concepts=understanding.concepts
            ).data()

            # 4. Get hierarchical context
            hierarchy = session.run(
                self.query_templates["hierarchical_context"],
                norm_ids=[n["norm_id"] for n in mapped_norms]
            ).data()

        return EnrichedContext(
            mapped_norms=self._process_norms(mapped_norms),
            related_concepts=self._process_concepts(related_concepts),
            jurisprudence_clusters=self._process_jurisprudence(jurisprudence),
            hierarchical_context=self._process_hierarchy(hierarchy),
            trace_id=f"KGE-{uuid.uuid4()}"
        )
```

### Cypher Query Templates

#### 1. Concept-to-Norm Mapping

**Obiettivo**: Trovare tutte le norme che regolano i concetti estratti.

```cypher
// Template: concept_to_norm
MATCH (c:LegalConcept)<-[:REGULATES]-(a:Article)
WHERE c.name IN $concepts
OPTIONAL MATCH (a)-[:MODIFIES|DEROGATES|INTEGRATES]->(related:Article)
RETURN DISTINCT
  a.id AS norm_id,
  a.title AS norm_title,
  a.hierarchy AS source,
  a.type AS norm_type,
  c.name AS regulates_concept,
  collect(DISTINCT related.id) AS related_norms
ORDER BY
  CASE a.hierarchy
    WHEN 'costituzione' THEN 1
    WHEN 'legge_costituzionale' THEN 2
    WHEN 'codice' THEN 3
    WHEN 'legge_ordinaria' THEN 4
    WHEN 'decreto_legislativo' THEN 5
    WHEN 'regolamento' THEN 6
    ELSE 99
  END,
  a.id
LIMIT 50
```

**Esempio di risultato**:
```python
[
    {
        "norm_id": "cc-art-2",
        "norm_title": "Maggiore età",
        "source": "codice_civile",
        "norm_type": "Article",
        "regulates_concept": "capacità_di_agire",
        "related_norms": []
    },
    {
        "norm_id": "cc-art-322",
        "norm_title": "Annullabilità degli atti compiuti dal minore",
        "source": "codice_civile",
        "norm_type": "Article",
        "regulates_concept": "capacità_di_agire",
        "related_norms": ["cc-art-320", "cc-art-394"]
    },
    {
        "norm_id": "cc-art-390",
        "norm_title": "Emancipazione",
        "source": "codice_civile",
        "norm_type": "Article",
        "regulates_concept": "capacità_di_agire",
        "related_norms": ["cc-art-391", "cc-art-394"]
    }
]
```

#### 2. Related Concepts Discovery

**Obiettivo**: Trovare concetti collegati che potrebbero essere rilevanti (es. se query menziona "capacità", trovare anche "emancipazione" come eccezione).

```cypher
// Template: related_concepts
MATCH (c1:LegalConcept)-[r:RELATED_TO|EXCEPTION_TO|PREREQUISITE_FOR]-(c2:LegalConcept)
WHERE c1.name IN $concepts
OPTIONAL MATCH (c2)<-[:REGULATES]-(norm:Article)
RETURN DISTINCT
  c2.name AS concept_name,
  c2.description AS concept_description,
  type(r) AS relationship_type,
  c1.name AS related_to_original,
  collect(DISTINCT norm.id)[0..3] AS sample_norms
LIMIT 20
```

**Esempio di risultato**:
```python
[
    {
        "concept_name": "emancipazione",
        "concept_description": "Acquisto anticipato della capacità di agire",
        "relationship_type": "EXCEPTION_TO",
        "related_to_original": "capacità_di_agire",
        "sample_norms": ["cc-art-390", "cc-art-391", "cc-art-394"]
    },
    {
        "concept_name": "rappresentanza_legale",
        "concept_description": "Sostituzione nella capacità di agire",
        "relationship_type": "RELATED_TO",
        "related_to_original": "capacità_di_agire",
        "sample_norms": ["cc-art-320", "cc-art-357"]
    },
    {
        "concept_name": "interdizione",
        "concept_description": "Limitazione capacità per infermità mentale",
        "relationship_type": "RELATED_TO",
        "related_to_original": "capacità_di_agire",
        "sample_norms": ["cc-art-414", "cc-art-418"]
    }
]
```

#### 3. Relevant Jurisprudence Discovery

**Obiettivo**: Trovare cluster di giurisprudenza che applicano i concetti estratti.

```cypher
// Template: relevant_jurisprudence
MATCH (c:LegalConcept)<-[:APPLIES]-(j:Jurisprudence)
WHERE c.name IN $concepts
WITH j, collect(DISTINCT c.name) AS applied_concepts
RETURN DISTINCT
  j.id AS jurisprudence_id,
  j.court AS court,
  j.date AS decision_date,
  j.massima AS massima,
  j.authority_score AS authority,
  applied_concepts
ORDER BY
  j.authority_score DESC,
  j.date DESC
LIMIT 10
```

**Esempio di risultato**:
```python
[
    {
        "jurisprudence_id": "Cass-18210-2015",
        "court": "Cassazione",
        "decision_date": "2015-09-14",
        "massima": "L'atto compiuto dal minore non emancipato è annullabile...",
        "authority": 0.92,
        "applied_concepts": ["capacità_di_agire", "annullabilità"]
    },
    {
        "jurisprudence_id": "Cass-3281-2019",
        "court": "Cassazione",
        "decision_date": "2019-02-07",
        "massima": "La rappresentanza legale dei genitori è necessaria...",
        "authority": 0.89,
        "applied_concepts": ["capacità_di_agire", "rappresentanza_legale"]
    }
]
```

#### 4. Hierarchical Context

**Obiettivo**: Capire la gerarchia delle fonti per le norme identificate.

```cypher
// Template: hierarchical_context
MATCH (lower:Article)
WHERE lower.id IN $norm_ids
OPTIONAL MATCH (lower)-[:IMPLEMENTS|DERIVES_FROM]->(higher:Norm)
OPTIONAL MATCH (constitutional:Norm {type: 'costituzione'})-[:PRINCIPLE_OF]->(lower)
RETURN DISTINCT
  lower.id AS norm_id,
  lower.hierarchy AS hierarchy_level,
  collect(DISTINCT higher.id) AS implements_norms,
  collect(DISTINCT constitutional.id) AS constitutional_basis
```

**Esempio di risultato**:
```python
[
    {
        "norm_id": "cc-art-2",
        "hierarchy_level": "codice_civile",
        "implements_norms": [],
        "constitutional_basis": ["cost-art-2"]  // Costituzione Art. 2
    },
    {
        "norm_id": "L-194-1978-art-9",
        "hierarchy_level": "legge_ordinaria",
        "implements_norms": [],
        "constitutional_basis": ["cost-art-2", "cost-art-32"]
    }
]
```

### Output Completo: EnrichedContext

**Esempio end-to-end**:

```python
# Input (da Query Understanding):
understanding = {
    "concepts": ["capacità_di_agire", "validità_contrattuale", "minore_età"],
    "entities": {"person": {"age": 16}},
    "intent": "validità_atto"
}

# Processing:
enriched = kg_enrichment.enrich(understanding)

# Output:
{
    "mapped_norms": [
        {
            "id": "cc-art-2",
            "title": "Maggiore età",
            "source": "codice_civile",
            "concept": "capacità_di_agire",
            "relevance_score": 1.0,
            "related_norms": []
        },
        {
            "id": "cc-art-322",
            "title": "Annullabilità atti minore",
            "source": "codice_civile",
            "concept": "capacità_di_agire",
            "relevance_score": 0.95,
            "related_norms": ["cc-art-320", "cc-art-394"]
        },
        {
            "id": "cc-art-1418",
            "title": "Cause di nullità del contratto",
            "source": "codice_civile",
            "concept": "validità_contrattuale",
            "relevance_score": 0.88,
            "related_norms": ["cc-art-1419", "cc-art-1421"]
        },
        {
            "id": "cc-art-1425",
            "title": "Cause di annullabilità del contratto",
            "source": "codice_civile",
            "concept": "validità_contrattuale",
            "relevance_score": 0.92,
            "related_norms": ["cc-art-1426", "cc-art-1441"]
        }
    ],

    "related_concepts": [
        {
            "name": "emancipazione",
            "description": "Acquisto anticipato capacità",
            "relationship": "EXCEPTION_TO",
            "norm_refs": ["cc-art-390", "cc-art-391"],
            "relevance_score": 0.75
        },
        {
            "name": "rappresentanza_legale",
            "description": "Sostituzione capacità genitore",
            "relationship": "RELATED_TO",
            "norm_refs": ["cc-art-320", "cc-art-357"],
            "relevance_score": 0.82
        }
    ],

    "jurisprudence_clusters": [
        {
            "id": "Cass-18210-2015",
            "court": "Cassazione",
            "date": "2015-09-14",
            "massima": "Annullabilità atti minore senza rappresentanza",
            "authority_score": 0.92,
            "applied_concepts": ["capacità_di_agire", "annullabilità"]
        },
        {
            "id": "Cass-3281-2019",
            "court": "Cassazione",
            "date": "2019-02-07",
            "massima": "Rappresentanza genitoriale necessaria per acquisto immobile",
            "authority_score": 0.89,
            "applied_concepts": ["capacità_di_agire", "rappresentanza_legale"]
        }
    ],

    "hierarchical_context": {
        "constitutional_basis": ["cost-art-2"],  // Diritti inviolabili della persona
        "codice_civile": ["cc-art-2", "cc-art-322", "cc-art-1418", "cc-art-1425"],
        "legge_ordinaria": [],
        "regolamenti": []
    },

    "statistics": {
        "norms_found": 4,
        "concepts_expanded": 2,
        "jurisprudence_found": 2,
        "query_time_ms": 47
    },

    "trace_id": "KGE-20240115-143025-def456"
}
```

### Flusso Informativo

```
Query Understanding Output
    ↓
    concepts: ["capacità_di_agire", "validità_contrattuale"]
    ↓
KG Enrichment (3 query parallele)
    ↓
    ├─ Concept→Norm: cc-art-2, cc-art-322, cc-art-1418
    ├─ Related Concepts: emancipazione, rappresentanza_legale
    └─ Jurisprudence: Cass-18210-2015, Cass-3281-2019
    ↓
EnrichedContext (contesto completo per Router)
    ↓
Router può ora pianificare:
  - API Agent: recupera testo di cc-art-2, cc-art-322, cc-art-1418
  - KG Agent: espandi grafo da emancipazione (eccezione importante!)
  - VectorDB Agent: cerca giurisprudenza simile a Cass-18210-2015
```

### Performance e Scalabilità

**Ottimizzazioni**:

1. **Query Parallele**: Le 3-4 query Cypher sono eseguite in parallelo (no sequential bottleneck)
2. **LIMIT Clauses**: Ogni query ha LIMIT per evitare risultati eccessivi
3. **Index su Concetti**: Neo4j index su `LegalConcept.name` per lookup veloce
4. **Caching**: Risultati cachati per concetti frequenti (es. "capacità_di_agire" viene richiesto spesso)

**Performance tipiche**:
- Query semplice (1-2 concetti): ~30-50ms
- Query complessa (5+ concetti): ~80-120ms
- Query con jurisprudence estesa: ~150-200ms

**Scalabilità**:
- KG con 100K norme + 10K concetti + 50K sentenze: performance stabile
- Read-only queries permettono horizontal scaling con Neo4j replicas

---

**FINE PARTE 1**

---

## LLM Router

### Overview

Il **LLM Router** è il componente decisionale centrale del sistema. Riceve l'**EnrichedContext** (output di KG Enrichment) e genera un piano strutturato per:

1. **Retrieval Plan**: Specificare quali agenti attivare e quali query eseguire
2. **Reasoning Plan**: Selezionare quali esperti coinvolgere e come combinarli
3. **Iteration Strategy**: Decidere se iterare e definire criteri di stop

### Responsabilità

**Input**:
- Query originale dell'utente
- QueryUnderstanding (entities, concepts, intent, temporal scope)
- EnrichedContext (norme mappate, concetti correlati, cluster giurisprudenziali)

**Output**:
- RouterDecision (piano strutturato per retrieval + reasoning)

**Funzioni**:
- Analizza il contesto arricchito per identificare gap informativi
- Seleziona strategie di retrieval ottimali (KG expansion, API fetch, semantic search)
- Sceglie esperti appropriati in base a intent e complessità della query
- Pianifica iterazioni quando necessario
- Traccia ogni decisione con rationale esplicito

### Flusso Decisionale

Il Router analizza il contesto arricchito e genera un piano strutturato seguendo questo flusso:

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT                                                       │
│  • Query originale                                           │
│  • QueryUnderstanding (entities, concepts, intent)          │
│  • EnrichedContext (mapped_norms, related_concepts, jurisp.)│
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  ANALISI CONTESTO                                            │
│  • Identifica gap informativi                                │
│  • Valuta complessità query                                  │
│  • Rileva potenziali conflitti normativi                     │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  PIANIFICAZIONE RETRIEVAL                                    │
│  • KG Agent: quali espansioni?                               │
│  • API Agent: quali norme (full text)?                       │
│  • VectorDB Agent: quali semantic search?                    │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  PIANIFICAZIONE REASONING                                    │
│  • Quali esperti attivare?                                   │
│  • Synthesis mode (convergent/divergent)?                    │
│  • Iterare o stop?                                           │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: RouterDecision                                      │
│  • retrieval_plan                                            │
│  • reasoning_plan                                            │
│  • iteration_strategy                                        │
│  • rationale + trace                                         │
└─────────────────────────────────────────────────────────────┘
```

### Input al Router

**Struttura dati input** (formato JSON):

```json
{
  "query": "È valido un contratto firmato da un sedicenne?",

  "understanding": {
    "entities": {
      "legal_object": "contratto",
      "person": {"age": 16, "type": "natural_person"}
    },
    "concepts": ["capacità_di_agire", "validità_contrattuale", "minore_età"],
    "intent": "validità_atto",
    "temporal_scope": "current",
    "complexity_score": 0.65
  },

  "enriched": {
    "mapped_norms": [
      {"id": "cc-art-2", "title": "Maggiore età", "relevance": 1.0},
      {"id": "cc-art-322", "title": "Annullabilità atti minore", "relevance": 0.95},
      {"id": "cc-art-1418", "title": "Cause nullità", "relevance": 0.88}
    ],
    "related_concepts": [
      {"name": "emancipazione", "relationship": "EXCEPTION_TO"},
      {"name": "rappresentanza_legale", "relationship": "RELATED_TO"}
    ],
    "jurisprudence_clusters": [
      {"id": "Cass-18210-2015", "authority": 0.92},
      {"id": "Cass-3281-2019", "authority": 0.89}
    ],
    "hierarchical_context": {
      "constitutional_basis": ["cost-art-2"],
      "codice_civile": ["cc-art-2", "cc-art-322", "cc-art-1418"]
    }
  }
}
```

### Output del Router: RouterDecision

**Struttura dati output** (formato JSON):

```json
{
  "retrieval_plan": {
    "kg_agent": {
      "task": "Expand graph from 'emancipazione' concept",
      "expansion_queries": [
        {
          "type": "concept_expansion",
          "starting_node": "emancipazione",
          "depth": 2,
          "rationale": "Check if emancipation creates exceptions"
        },
        {
          "type": "norm_relationships",
          "starting_norms": ["cc-art-322", "cc-art-1418", "cc-art-1425"],
          "relationship_types": ["MODIFIES", "DEROGATES", "INTEGRATES"],
          "rationale": "Find modifications to annulment rules"
        }
      ]
    },

    "api_agent": {
      "task": "Retrieve full text of norms identified by KG Enrichment",
      "norms_to_retrieve": [
        {"id": "cc-art-2", "version": "current", "priority": "high"},
        {"id": "cc-art-322", "version": "current", "priority": "high"},
        {"id": "cc-art-1418", "version": "current", "priority": "medium"},
        {"id": "cc-art-390", "version": "current", "priority": "low"}
      ],
      "rationale": "Need full text for literal interpretation"
    },

    "vectordb_agent": {
      "task": "Semantic search for jurisprudence",
      "semantic_queries": [
        {
          "query": "contratto minore annullabilità sedicenne capacità agire",
          "filters": {
            "document_type": ["sentenza"],
            "court_level": ["cassazione", "appello"],
            "date_range": "last_10_years"
          },
          "top_k": 10,
          "rationale": "Find case law to confirm interpretation"
        }
      ],
      "reranking": {
        "enabled": true,
        "boost_factors": {
          "authority_score": 0.3,
          "recency": 0.2,
          "semantic_similarity": 0.5
        }
      }
    }
  },

  "reasoning_plan": {
    "experts": ["Literal_Interpreter", "Precedent_Analyst"],
    "rationale": "Query intent is 'validità_atto'. Literal Interpreter needed for exact wording (Art. 2, 322). Precedent Analyst confirms with case law (Cass. 18210/2015). Systemic-Teleological not needed (rule is clear). Principles Balancer not needed (no constitutional conflict).",
    "synthesis_mode": "convergent",
    "synthesis_rationale": "Both experts likely agree: Art. 322 is clear, case law consistent"
  },

  "iteration_strategy": {
    "iteration_number": 1,
    "max_iterations": 2,
    "stop_criteria": "Stop if: (1) experts converge, (2) no ambiguity in norms, (3) case law confirms. Iterate if: (1) expert disagreement, (2) emancipation introduces complexity, (3) missing norms.",
    "confidence_threshold": 0.85
  },

  "rationale": "Query asks about contract validity for 16-year-old. KG Enrichment mapped concepts to norms successfully. Well-structured question with clear norms. Expecting convergent answer: 'Annullabile per Art. 322 c.c.'",

  "trace_id": "RTR-20240115-143030-xyz789",
  "timestamp": "2024-01-15T14:30:30.123Z",
  "rlcf_guidance_used": false
}
```

### Logica di Selezione degli Esperti

Il Router seleziona esperti in base a **intent** e **complessità**:

| Intent | Complessità | Esperti Selezionati | Rationale |
|--------|-------------|---------------------|-----------|
| `validità_atto` | < 0.7 | Literal + Precedent | Norma chiara, conferma con giurisprudenza |
| `validità_atto` | > 0.7 | Literal + Systemic + Precedent | Ambiguità richiede analisi ratio legis |
| `bilanciamento_diritti` | qualsiasi | Principles + Systemic + Precedent | Conflitto valori costituzionali |
| `interpretazione_norma` | < 0.6 | Literal | Norma chiara |
| `interpretazione_norma` | > 0.6 | Literal + Systemic | Ambiguità semantica |
| `conformità_costituzionale` | qualsiasi | Principles + Literal + Precedent | Verifica legittimità costituzionale |
| `evoluzione_giurisprudenziale` | qualsiasi | Precedent + Systemic | Analisi trend case law |
| `conseguenze_giuridiche` | < 0.7 | Literal + Precedent | Conseguenze chiare da norma |
| `conseguenze_giuridiche` | > 0.7 | Tutti e 4 | Scenario complesso, serve analisi multi-prospettiva |

### RLCF Integration Point

Il Router è il **primo punto di integrazione RLCF**. Il sistema apprende da feedback:

**Ciclo di apprendimento**:

```
┌──────────────────────────────────────────────────────────┐
│  RACCOLTA FEEDBACK                                        │
│  (query, understanding, enriched) → router_decision       │
│                                   ↓                       │
│                              user_feedback                │
│                              (rating, corrections)        │
└──────────────────────┬───────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│  TRAINING DATASET                                         │
│  Tupla: (features, decision, reward)                      │
│                                                            │
│  Features:                                                 │
│  - intent, complexity, num_concepts, num_mapped_norms     │
│  - has_constitutional_basis, num_jurisprudence            │
│                                                            │
│  Decision:                                                 │
│  - experts_activated, retrieval_scope, iteration_max      │
│                                                            │
│  Reward:                                                   │
│  - user_rating (1-5), time_to_answer, cost               │
└──────────────────────┬───────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│  POLICY LEARNING                                          │
│  Modello apprende:                                        │
│  • Quali esperti per quali query                          │
│  • Quando iterare (vs stop al primo round)                │
│  • Scope retrieval ottimale (full vs targeted)            │
└──────────────────────┬───────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│  GUIDANCE AL ROUTER                                       │
│  Policy suggerisce: "For intent=validità_atto +           │
│  complexity<0.7 → use Literal+Precedent only"             │
└──────────────────────────────────────────────────────────┘
```

**Esempio di ottimizzazione appresa**:

Iterazione iniziale:
- Query intent=`validità_atto`, complexity=0.65
- Router attiva tutti e 4 gli esperti (costoso, lento)
- Feedback: "Risposta corretta ma 3 esperti erano ridondanti. Rating: 3/5"

Dopo RLCF:
- Query simile: intent=`validità_atto`, complexity=0.63
- RLCF suggerisce: "Attiva solo Literal + Precedent"
- Router segue guidance
- Feedback: "Perfetto! Veloce e accurato. Rating: 5/5"

**Obiettivi di apprendimento**:
1. Minimizzare costo retrieval mantenendo qualità
2. Massimizzare successo al primo round (evitare iterazioni inutili)
3. Apprendere pattern expert selection per categorie di query

---

## Retrieval Agents

I **Retrieval Agents** sono componenti tecnici che eseguono il piano di retrieval generato dal Router.

### Caratteristiche Architetturali

**Separazione responsabilità**:
- Agents recuperano dati da fonti diverse
- Agents NON ragionano sui dati
- Agents sono idempotenti (stessa query → stesso risultato)
- Agents tracciano ogni operazione

**Esecuzione parallela**:
- I 3 agenti eseguono contemporaneamente
- Performance = max(KG_time, API_time, VectorDB_time)
- Esempio: max(50ms, 120ms, 225ms) = 225ms (vs 395ms sequenziale)

### Architettura dei Tre Agenti

```
┌─────────────────────────────────────────────────────────────┐
│                    ROUTER DECISION                          │
│  retrieval_plan: {kg_agent:{...}, api_agent:{...}, ...}    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
          ┌────────────┴───────────┬──────────────┐
          ↓                        ↓              ↓
    ┌──────────┐            ┌──────────┐    ┌──────────┐
    │KG Agent  │            │API Agent │    │VectorDB  │
    │          │            │          │    │Agent     │
    └──────────┘            └──────────┘    └──────────┘
          │                        │              │
          │ Graph expansion        │ Full texts   │ Semantic search
          ↓                        ↓              ↓
┌──────────────────┐    ┌──────────────────┐  ┌──────────────────┐
│ Graph data:      │    │ Norm texts:      │  │ Similar docs:    │
│ • Nodes          │    │ • Art.2 c.c.     │  │ • Cass.18210/2015│
│ • Relations      │    │ • Art.322 c.c.   │  │ • Cass.3281/2019 │
│ • Paths          │    │ • Art.1418 c.c.  │  │ • Dottrina       │
└──────────────────┘    └──────────────────┘  └──────────────────┘
          │                        │              │
          └────────────┬───────────┴──────────────┘
                       ↓
              ┌─────────────────┐
              │ RETRIEVED DATA  │
              │ (merged result) │
              └─────────────────┘
```

---

### KG Agent (Graph Expansion)

**Responsabilità**: Espandere il Knowledge Graph seguendo relazioni tra nodi.

**Input** (dal Router):
```json
{
  "expansion_queries": [
    {
      "type": "concept_expansion",
      "starting_node": "emancipazione",
      "depth": 2,
      "rationale": "Check exceptions to capacity rule"
    },
    {
      "type": "norm_relationships",
      "starting_norms": ["cc-art-322", "cc-art-1418"],
      "relationship_types": ["MODIFIES", "DEROGATES", "INTEGRATES"],
      "rationale": "Find modifications to annulment rules"
    }
  ]
}
```

**Processing**:
- Esegue query di espansione sul grafo (es. Cypher per Neo4j)
- Limita profondità per evitare esplosione combinatoria
- Segue solo relazioni rilevanti specificate
- Read-only (nessuna modifica al grafo)

**Output**:
```json
{
  "expansions": [
    {
      "query_type": "concept_expansion",
      "starting_point": "emancipazione",
      "nodes_found": [
        {"type": "LegalConcept", "name": "emancipazione"},
        {"type": "Article", "id": "cc-art-390", "title": "Emancipazione"},
        {"type": "Article", "id": "cc-art-391", "title": "Effetti emancipazione"},
        {"type": "LegalConcept", "name": "capacità_limitata"}
      ],
      "relationships": [
        {
          "from": "emancipazione",
          "to": "cc-art-390",
          "type": "REGULATES"
        },
        {
          "from": "emancipazione",
          "to": "capacità_di_agire",
          "type": "EXCEPTION_TO",
          "properties": {"description": "Acquisto anticipato capacità"}
        }
      ],
      "paths": [
        "emancipazione -[REGULATES]-> cc-art-390",
        "emancipazione -[EXCEPTION_TO]-> capacità_di_agire -[REGULATES]-> cc-art-2"
      ],
      "insights": {
        "exception_found": true,
        "affects_norms": ["cc-art-390", "cc-art-391"],
        "rationale": "Emancipation creates exception to general capacity rule in Art. 2"
      }
    }
  ],
  "trace_id": "KGA-uuid",
  "timestamp": "2024-01-15T14:30:35Z",
  "execution_time_ms": 50
}
```

**Tipi di espansione supportati**:

1. **Concept Expansion**: Parte da un concetto, trova norme collegate e concetti correlati
2. **Norm Relationships**: Trova modifiche/deroghe/integrazioni tra norme
3. **Hierarchical Traversal**: Naviga gerarchia fonti (Costituzione → Legge → Regolamento)
4. **Temporal Traversal**: Trova versioni storiche di norme (multivigenza)

---

### API Agent (Norm Text Retrieval)

**Responsabilità**: Recuperare testi completi delle norme da API esterna.

**Input** (dal Router):
```json
{
  "norms_to_retrieve": [
    {"id": "cc-art-2", "version": "current", "priority": "high"},
    {"id": "cc-art-322", "version": "current", "priority": "high"},
    {"id": "cc-art-1418", "version": "current", "priority": "medium"},
    {"id": "cc-art-390", "version": "current", "priority": "low"}
  ]
}
```

**Processing**:
- Interroga API Akoma Ntoso per ogni norma
- Gestisce multivigenza (versione current vs versione storica)
- Usa caching per performance (Redis/similar)
- Fallback su cache se API non disponibile
- Parsing strutturato XML/JSON Akoma Ntoso

**Output**:
```json
{
  "norms": [
    {
      "norm_id": "cc-art-2",
      "version": "current",
      "title": "Maggiore età. Capacità di agire",
      "full_text": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa.",
      "structured": {
        "paragraphs": [
          {
            "number": 1,
            "text": "La maggiore età è fissata al compimento del diciottesimo anno."
          },
          {
            "number": 2,
            "text": "Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa."
          }
        ]
      },
      "metadata": {
        "source": "Codice Civile",
        "book": "Libro I - Delle persone e della famiglia",
        "effective_from": "1942-03-16",
        "effective_to": null,
        "status": "vigente"
      },
      "retrieved_from": "cache",
      "trace_id": "API-uuid-1"
    },
    {
      "norm_id": "cc-art-322",
      "version": "current",
      "title": "Atti compiuti dal minore",
      "full_text": "Gli atti compiuti dal minore possono essere annullati su istanza del minore stesso o dei suoi rappresentanti.",
      "structured": {
        "paragraphs": [
          {
            "number": 1,
            "text": "Gli atti compiuti dal minore possono essere annullati su istanza del minore stesso o dei suoi rappresentanti."
          }
        ]
      },
      "metadata": {
        "source": "Codice Civile",
        "book": "Libro I",
        "effective_from": "1942-03-16",
        "status": "vigente"
      },
      "retrieved_from": "api",
      "trace_id": "API-uuid-2"
    }
  ],
  "trace_id": "API-main-uuid",
  "timestamp": "2024-01-15T14:30:35Z",
  "performance": {
    "api_calls": 2,
    "cache_hits": 2,
    "total_time_ms": 120
  }
}
```

**Gestione multivigenza**:

Esempio: "Cosa diceva Art. 5 DL 18/2020 il 15 marzo 2020?"

```json
{
  "norm_id": "DL-18-2020-art-5",
  "version": "2020-03-15",
  "title": "Misure urgenti contenimento COVID-19",
  "full_text": "[Testo vigente il 15 marzo 2020]",
  "metadata": {
    "effective_from": "2020-03-09",
    "effective_to": "2020-05-17",
    "status": "abrogato",
    "abrogated_by": "DL-33-2020"
  }
}
```

---

### VectorDB Agent (Semantic Search)

**Responsabilità**: Ricerca semantica su embeddings per trovare documenti simili.

**Input** (dal Router):
```json
{
  "semantic_queries": [
    {
      "query": "contratto minore annullabilità sedicenne capacità agire",
      "filters": {
        "document_type": ["sentenza"],
        "court_level": ["cassazione", "appello"],
        "date_range": "last_10_years"
      },
      "top_k": 10,
      "reranking": {
        "enabled": true,
        "boost_factors": {
          "authority_score": 0.3,
          "recency": 0.2,
          "semantic_similarity": 0.5
        }
      },
      "rationale": "Find case law to confirm interpretation"
    }
  ]
}
```

**Processing**:
- Hybrid search: vector similarity + keyword matching (BM25)
- Metadata filtering (temporal, court level, document type)
- Over-retrieval (top_k × 2) per reranking
- Cross-encoder reranking con boost factors:
  - **Authority score**: Peso sentenze Cassazione > Appello > Tribunale
  - **Recency**: Favorisce sentenze recenti
  - **Semantic similarity**: Similarità vettoriale query-document

**Output**:
```json
{
  "results": [
    {
      "id": "Cass-18210-2015",
      "document_type": "sentenza",
      "court": "Cassazione",
      "date": "2015-09-14",
      "massima": "L'atto compiuto dal minore non emancipato è annullabile su istanza del minore stesso o dei suoi rappresentanti legali, anche dopo il raggiungimento della maggiore età.",
      "full_text_excerpt": "[...]",
      "scores": {
        "semantic_similarity": 0.89,
        "authority_score": 0.92,
        "recency_score": 0.55,
        "final_score": 0.87
      },
      "trace_id": "VDB-uuid-1"
    },
    {
      "id": "Cass-3281-2019",
      "document_type": "sentenza",
      "court": "Cassazione",
      "date": "2019-02-07",
      "massima": "La rappresentanza legale dei genitori è necessaria per gli atti di straordinaria amministrazione compiuti dal minore, anche se emancipato.",
      "scores": {
        "semantic_similarity": 0.85,
        "authority_score": 0.89,
        "recency_score": 0.75,
        "final_score": 0.84
      },
      "trace_id": "VDB-uuid-2"
    },
    {
      "id": "App-Milano-1234-2020",
      "document_type": "sentenza",
      "court": "Appello Milano",
      "date": "2020-03-15",
      "massima": "Il contratto stipulato da minorenne è annullabile, non nullo...",
      "scores": {
        "semantic_similarity": 0.91,
        "authority_score": 0.65,
        "recency_score": 0.80,
        "final_score": 0.82
      },
      "trace_id": "VDB-uuid-3"
    }
  ],
  "metadata": {
    "total_candidates": 20,
    "returned": 3,
    "filters_applied": ["document_type", "court_level", "date_range"],
    "reranking_enabled": true
  },
  "trace_id": "VDB-main-uuid",
  "timestamp": "2024-01-15T14:30:35Z",
  "performance": {
    "vector_search_ms": 45,
    "reranking_ms": 180,
    "total_ms": 225
  }
}
```

**Reranking formula**:

```
final_score = (semantic_similarity × 0.5) +
              (authority_score × 0.3) +
              (recency_score × 0.2)

dove:
- semantic_similarity ∈ [0,1] da cosine similarity embeddings
- authority_score ∈ [0,1] da metadata (Cassazione=1.0, Appello=0.7, Tribunale=0.4)
- recency_score ∈ [0,1] = max(0, 1 - years_old/20)
```

---

### Risultato Aggregato del Retrieval

Dopo esecuzione parallela dei 3 agenti, il sistema produce **RetrievalResult** aggregato:

```json
{
  "kg_expansion": {
    "nodes_found": 8,
    "new_norms_discovered": ["cc-art-390", "cc-art-391"],
    "exceptions_identified": ["emancipazione"],
    "time_ms": 50
  },

  "norm_texts": {
    "norms_retrieved": 4,
    "cache_hits": 2,
    "api_calls": 2,
    "time_ms": 120
  },

  "semantic_matches": {
    "jurisprudence_found": 3,
    "dottrina_found": 0,
    "avg_relevance": 0.84,
    "time_ms": 225
  },

  "trace_id": "RET-main-uuid",
  "timestamp": "2024-01-15T14:30:35Z",
  "total_time_ms": 225,
  "execution_mode": "parallel"
}
```

Questo risultato aggregato diventa input per i **Reasoning Experts**.

---

**FINE PARTE 2**

---

**Prossimi step**: Parte 3 conterrà i 4 Reasoning Experts (Literal Interpreter, Systemic-Teleological Reasoner, Principles Balancer, Precedent Analyst).

## Reasoning Experts

I **Reasoning Experts** sono componenti specializzati che applicano diverse metodologie di interpretazione giuridica ai dati recuperati dai Retrieval Agents.

### Principio Architetturale: Separazione Epistemologica

Gli esperti sono separati per **metodologia interpretativa**, non per dominio giuridico:

```
❌ APPROCCIO ERRATO (per dominio):
   - Esperto Civile
   - Esperto Penale
   - Esperto Lavoro
   → Problema: impossibile cross-analysis tra materie

✅ APPROCCIO CORRETTO (epistemologico):
   - Literal Interpreter (positivismo)
   - Systemic-Teleological (finalismo)
   - Principles Balancer (costituzionalismo)
   - Precedent Analyst (empirismo)
   → Vantaggio: applicabili a qualsiasi materia giuridica
```

### I Quattro Esperti

```
┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVED DATA                               │
│  • Norm texts (da API Agent)                                    │
│  • Graph context (da KG Agent)                                  │
│  • Similar cases (da VectorDB Agent)                            │
└──────────────────────┬──────────────────────────────────────────┘
                       ↓
          ┌────────────┴──────────────┬─────────────┬──────────────┐
          ↓                           ↓             ↓              ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│ LITERAL          │  │ SYSTEMIC-        │  │ PRINCIPLES   │  │ PRECEDENT    │
│ INTERPRETER      │  │ TELEOLOGICAL     │  │ BALANCER     │  │ ANALYST      │
│                  │  │                  │  │              │  │              │
│ Positivismo      │  │ Finalismo        │  │ Costitu-     │  │ Empirismo    │
│ giuridico        │  │ Ratio legis      │  │ zionalismo   │  │ giuridico    │
└──────────────────┘  └──────────────────┘  └──────────────┘  └──────────────┘
          │                           │             │              │
          │ "Testo dice X"            │ "Scopo è Y" │ "Bilancia Z" │ "Giudici W"
          ↓                           ↓             ↓              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXPERT OUTPUTS                               │
│  • Interpretazione + rationale                                  │
│  • Confidence score                                             │
│  • Sources used                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Expert 1: Literal Interpreter

### Epistemologia

**Corrente**: Positivismo giuridico, originalismo testuale

**Principi**:
- La legge dice esattamente ciò che è scritto
- Interpretazione grammaticale e letterale
- "In claris non fit interpretatio" (ciò che è chiaro non si interpreta)
- Primato del testo legislativo

**Quando attivarlo**:
- Intent: `validità_atto`, `interpretazione_norma`, `requisiti_procedurali`
- Complessità < 0.7 (norma chiara)
- Quando è necessaria certezza giuridica formale

### Input

```json
{
  "query": "È valido un contratto firmato da un sedicenne?",
  "retrieved_norms": [
    {
      "id": "cc-art-2",
      "full_text": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa.",
      "structured": {
        "paragraphs": [
          {"number": 1, "text": "La maggiore età è fissata al compimento del diciottesimo anno."},
          {"number": 2, "text": "Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa."}
        ]
      }
    },
    {
      "id": "cc-art-322",
      "full_text": "Gli atti compiuti dal minore possono essere annullati su istanza del minore stesso o dei suoi rappresentanti."
    }
  ],
  "graph_context": {
    "norm_relationships": [],
    "exceptions": ["emancipazione"]
  }
}
```

### Metodologia

**Step di reasoning**:

1. **Analisi letterale del testo**
   - Identifica termini chiave: "maggiore età", "diciottesimo anno", "capacità di compiere atti"
   - Parse grammaticale: soggetto, verbo, complementi
   - Nessuna interpretazione estensiva o analogica

2. **Applicazione diretta alla fattispecie**
   - Query menziona: "sedicenne" (16 anni)
   - Art. 2: "diciottesimo anno" (18 anni)
   - Confronto: 16 < 18 → minore

3. **Conseguenze testuali**
   - Art. 322: "atti compiuti dal minore possono essere annullati"
   - Verbo: "possono essere annullati" → annullabilità (non nullità)

4. **Verifica eccezioni esplicite nel testo**
   - Art. 2 dice: "per i quali non sia stabilita un'età diversa"
   - Controlla se esiste norma che stabilisce età diversa per contratti
   - (Nel caso specifico: no)

### Output

```json
{
  "expert": "Literal_Interpreter",
  "interpretation": "Il contratto firmato da un sedicenne è ANNULLABILE",

  "rationale": {
    "main_argument": "Art. 2 c.c. stabilisce testualmente che la maggiore età si raggiunge al 18° anno. Un sedicenne è quindi minore. Art. 322 c.c. stabilisce testualmente che gli atti del minore 'possono essere annullati'.",

    "textual_analysis": [
      {
        "norm": "cc-art-2",
        "key_phrase": "La maggiore età è fissata al compimento del diciottesimo anno",
        "interpretation": "Letteralmente: maggiore età = 18 anni. Sedicenne (16 anni) è minore."
      },
      {
        "norm": "cc-art-322",
        "key_phrase": "possono essere annullati",
        "interpretation": "Il verbo 'possono' indica annullabilità (azione costitutiva), non nullità automatica. Serve istanza di parte."
      }
    ],

    "grammatical_notes": [
      "'Possono essere annullati' (tempo: presente, modo: indicativo, forma: passiva) indica possibilità, non automatismo.",
      "'Su istanza' indica legittimazione attiva necessaria (minore o rappresentanti)."
    ],

    "exceptions_checked": [
      {
        "norm": "cc-art-2",
        "clause": "per i quali non sia stabilita un'età diversa",
        "finding": "Nessuna norma stabilisce età diversa per contratti generici → si applica regola generale (18 anni)"
      }
    ]
  },

  "conclusion": "ANNULLABILE (non nullo)",

  "confidence": 0.95,
  "confidence_rationale": "Testo normativo è esplicito e non ambiguo. Termini 'diciottesimo anno' e 'possono essere annullati' sono chiari.",

  "sources": [
    {"norm": "cc-art-2", "relevance": 1.0, "usage": "Definizione maggiore età"},
    {"norm": "cc-art-322", "relevance": 1.0, "usage": "Conseguenza atti minore"}
  ],

  "limitations": [
    "Non considera ratio legis (analisi teleologica)",
    "Non considera evoluzione giurisprudenziale",
    "Non valuta bilanciamento con principi costituzionali",
    "Ignora contesto economico-sociale"
  ],

  "trace_id": "LIT-uuid",
  "timestamp": "2024-01-15T14:30:40Z"
}
```

### Limitazioni dell'Approccio Letterale

| Scenario | Problema | Esempio |
|----------|----------|---------|
| Norma ambigua | Più interpretazioni letterali possibili | "Danno ingiusto" (Art. 2043): cosa significa "ingiusto"? |
| Lacuna normativa | Testo non copre caso | Responsabilità per danni da IA: norma non esisteva quando codice scritto |
| Contrasto valori | Lettera vs spirito | Diritto alla vita (testo) vs eutanasia (dignità) |
| Evoluzione sociale | Testo obsoleto | "Buon costume" (1942) vs concezione attuale |

---

## Expert 2: Systemic-Teleological Reasoner

### Epistemologia

**Corrente**: Finalismo giuridico, interpretazione teleologica

**Principi**:
- Ogni norma ha uno scopo (ratio legis)
- Interpretazione sistematica (norma nel contesto dell'ordinamento)
- "Lex dixit minus quam voluit" (la legge dice meno di ciò che intende)
- Ricerca della coerenza del sistema giuridico

**Quando attivarlo**:
- Intent: `interpretazione_norma`, `bilanciamento_diritti`
- Complessità > 0.6 (ambiguità, lacune)
- Quando testo letterale insufficiente o contraddittorio
- Quando serve analisi di scopo legislativo

### Input

```json
{
  "query": "Un minore emancipato può stipulare contratto di lavoro autonomo?",
  "retrieved_norms": [
    {
      "id": "cc-art-390",
      "full_text": "Il minore è emancipato di diritto per effetto del matrimonio.",
      "context": "Libro I - Delle persone e della famiglia"
    },
    {
      "id": "cc-art-394",
      "full_text": "L'emancipato può compiere atti di ordinaria amministrazione, ma per gli atti eccedenti l'ordinaria amministrazione deve essere assistito da un curatore.",
      "context": "Capo IX - Dell'emancipazione"
    }
  ],
  "graph_context": {
    "ratio_legis_emancipazione": "Favorire autonomia minore che ha assunto responsabilità familiari tramite matrimonio",
    "systemic_context": "Sistema graduale di acquisto capacità (minore → emancipato → maggiorenne)"
  },
  "ambiguity": "Contratto lavoro autonomo è 'ordinaria' o 'straordinaria' amministrazione?"
}
```

### Metodologia

**Step di reasoning**:

1. **Identificazione ratio legis**
   - Perché legislatore ha creato emancipazione?
   - Scopo: favorire autonomia responsabile di minore maturo
   - Bilanciamento: protezione vs autonomia

2. **Analisi sistematica**
   - Collocazione norma nel sistema (Libro I, Capo IX)
   - Confronto con istituti simili (interdizione, inabilitazione, amministrazione di sostegno)
   - Coerenza con principi generali (art. 2 Cost: diritti inviolabili)

3. **Interpretazione teleologica**
   - Lavoro autonomo: realizza autonomia economica
   - Coerente con ratio emancipazione (responsabilità familiare → capacità economica)
   - "Ordinaria amministrazione" interpretato funzionalmente, non formalmente

4. **Test di coerenza**
   - Interpretazione proposta è coerente con scopo istituto?
   - Produce risultati ragionevoli?
   - È conforme a sistema complessivo?

### Output

```json
{
  "expert": "Systemic_Teleological_Reasoner",
  "interpretation": "Il minore emancipato PUÒ stipulare contratto di lavoro autonomo SENZA assistenza curatore",

  "rationale": {
    "main_argument": "La ratio dell'emancipazione è favorire l'autonomia del minore che ha assunto responsabilità familiari. Il lavoro autonomo realizza questa autonomia economica ed è coerente con lo scopo dell'istituto. Deve essere considerato 'ordinaria amministrazione' in senso funzionale.",

    "ratio_legis_analysis": {
      "emancipazione": {
        "scopo_legislatore": "Riconoscere capacità a minore che, sposandosi, ha dimostrato maturità e assunto responsabilità familiari",
        "bilanciamento": "Protezione (limiti atti straordinari) vs autonomia (atti ordinari senza assistenza)",
        "evoluzione_storica": "Istituto pensato quando matrimonio possibile a età più giovane, oggi meno frequente ma ratio invariata"
      }
    },

    "systemic_analysis": {
      "collocazione_normativa": "Capo IX (Emancipazione) tra Capo VIII (Minore età) e Libro II (Successioni) → status intermedio",

      "confronto_istituti_simili": [
        {
          "istituto": "Interdizione (art. 414)",
          "differenza": "Interdetto perde capacità, emancipato la acquista parzialmente",
          "ratio": "Protezione totale vs autonomia parziale"
        },
        {
          "istituto": "Amministrazione sostegno (art. 404)",
          "differenza": "ADS personalizzabile, emancipazione rigida (ordinaria/straordinaria)",
          "similitudine": "Entrambi bilanciano protezione e autonomia"
        }
      ],

      "principi_costituzionali": [
        {
          "norma": "Art. 2 Cost",
          "principio": "Diritti inviolabili della persona",
          "applicazione": "Lavoro autonomo realizza personalità (art. 2) e diritto al lavoro (art. 4)"
        },
        {
          "norma": "Art. 4 Cost",
          "principio": "Diritto al lavoro",
          "applicazione": "Limitare lavoro autonomo contrasterebbe con diritto costituzionale"
        }
      ]
    },

    "interpretazione_teleologica": {
      "problema": "'Ordinaria amministrazione' è concetto aperto",

      "interpretazione_formalista": "Contratto lavoro autonomo = impresa → straordinaria amministrazione → serve curatore",

      "interpretazione_funzionalista": "Lavoro autonomo NON professionale (es. freelance occasionale) = gestione quotidiana reddito → ordinaria amministrazione → NO curatore",

      "scelta_interpretativa": "Funzionalista",

      "motivazione": "Ratio emancipazione è favorire autonomia responsabile. Richiedere curatore per lavoro autonomo frustrebbe questo scopo. Il minore emancipato, avendo assunto responsabilità familiare (matrimonio), è capace di gestire lavoro autonomo che realizzi sostentamento familiare."
    },

    "test_coerenza": {
      "coerenza_ratio": true,
      "coerenza_sistema": true,
      "ragionevolezza_risultato": true,
      "conformità_costituzionale": true
    }
  },

  "conclusion": "PUÒ stipulare senza curatore (interpretazione sistematico-teleologica di 'ordinaria amministrazione')",

  "confidence": 0.78,
  "confidence_rationale": "Interpretazione coerente con ratio e sistema, ma margine di incertezza perché concetto 'ordinaria amministrazione' aperto. Giurisprudenza potrebbe divergere.",

  "alternative_interpretations": [
    {
      "interpretation": "Lavoro autonomo sempre straordinario → serve curatore",
      "rationale": "Approccio formalista: qualsiasi attività imprenditoriale è straordinaria",
      "weakness": "Frustra ratio emancipazione, contrasta art. 4 Cost"
    }
  ],

  "sources": [
    {"norm": "cc-art-390", "usage": "Definizione emancipazione"},
    {"norm": "cc-art-394", "usage": "Distinzione ordinaria/straordinaria"},
    {"constitutional": "art-2-Cost", "usage": "Principio autonomia persona"},
    {"constitutional": "art-4-Cost", "usage": "Diritto al lavoro"}
  ],

  "caveats": [
    "Interpretazione proposta, non certezza assoluta",
    "Dipende da natura specifica lavoro autonomo (professionale vs occasionale)",
    "Giurisprudenza potrebbe adottare interpretazione diversa",
    "Consigliabile richiedere curatore in casi dubbi per sicurezza"
  ],

  "trace_id": "SYS-uuid",
  "timestamp": "2024-01-15T14:30:42Z"
}
```

### Quando Systemic-Teleological è Superiore a Literal

| Scenario | Literal fallirebbe | Systemic-Teleological riesce |
|----------|-------------------|------------------------------|
| Norma ambigua | "Danno ingiusto": cosa significa? | Analizza ratio (riparare danni illeciti) → interpreta "ingiusto" = contra ius |
| Lacuna | Responsabilità per danni IA: norma non esiste | Analogia da responsabilità produttore (ratio: proteggere danneggiati) |
| Contrasto apparente | Art. X dice A, Art. Y dice non-A | Analisi sistematica trova criterio coerenza (lex specialis, gerarchia) |
| Evoluzione sociale | "Buon costume" 1942 ≠ 2024 | Interpreta "buon costume" secondo valori attuali (ratio: morale sociale) |

---

## Expert 3: Principles Balancer

### Epistemologia

**Corrente**: Costituzionalismo, principialismo, neocostituzionalismo

**Principi**:
- Diritti fondamentali sono nucleo ordinamento
- Quando diritti confliggono: bilanciamento (non gerarchia)
- Test di proporzionalità (idoneità, necessità, proporzione)
- Primato della Costituzione

**Quando attivarlo**:
- Intent: `bilanciamento_diritti`, `conformità_costituzionale`
- Query coinvolge diritti fondamentali in conflitto
- Verifica costituzionalità norma
- Casi eticamente sensibili (vita, libertà, dignità)

### Input

```json
{
  "query": "È legittimo licenziamento di lavoratrice che rifiuta vaccino COVID-19 obbligatorio per categoria?",

  "retrieved_norms": [
    {
      "id": "DL-44-2021-art-4",
      "full_text": "È obbligatorio per esercenti professioni sanitarie vaccinarsi contro COVID-19...",
      "hierarchical_level": "decreto_legge"
    },
    {
      "id": "L-300-1970-art-18",
      "full_text": "Il licenziamento deve essere sorretto da giusta causa o giustificato motivo...",
      "hierarchical_level": "legge_ordinaria"
    }
  ],

  "constitutional_norms": [
    {
      "id": "cost-art-2",
      "text": "La Repubblica riconosce e garantisce i diritti inviolabili dell'uomo...",
      "principle": "Diritti inviolabili persona"
    },
    {
      "id": "cost-art-32",
      "text": "La Repubblica tutela la salute come fondamentale diritto dell'individuo e interesse della collettività. Nessuno può essere obbligato a un determinato trattamento sanitario se non per disposizione di legge...",
      "principle": "Diritto alla salute + libertà autodeterminazione sanitaria"
    },
    {
      "id": "cost-art-4",
      "text": "La Repubblica riconosce a tutti i cittadini il diritto al lavoro...",
      "principle": "Diritto al lavoro"
    }
  ],

  "conflict": {
    "right_A": "Libertà autodeterminazione sanitaria (rifiuto vaccino)",
    "right_B": "Tutela salute collettiva + diritto al lavoro altri",
    "incompatibility": "Lavoratrice sanitaria non vaccinata = rischio per pazienti e colleghi"
  }
}
```

### Metodologia

**Step di reasoning**:

1. **Identificazione diritti in conflitto**
   - Diritto A: Libertà autodeterminazione sanitaria (art. 32 Cost)
   - Diritto B: Tutela salute collettiva (art. 32 Cost)
   - Diritto C: Diritto al lavoro (art. 4 Cost)

2. **Analisi gerarchica fonti**
   - Costituzione > Legge ordinaria > Decreto legge
   - Entrambi diritti hanno rango costituzionale → serve bilanciamento

3. **Test di proporzionalità (triplo)**
   - **Idoneità**: Obbligo vaccino è idoneo a tutelare salute collettiva?
   - **Necessità**: È misura meno restrittiva possibile?
   - **Proporzionalità in senso stretto**: Beneficio (salute) > Sacrificio (libertà)?

4. **Bilanciamento contestuale**
   - Categoria: professionisti sanitari (contatto con soggetti fragili)
   - Situazione: pandemia (emergenza sanitaria)
   - Alternative: riassegnazione mansioni? Sospensione? Licenziamento?

### Output

```json
{
  "expert": "Principles_Balancer",
  "interpretation": "Licenziamento LEGITTIMO se preceduto da tentativi riassegnazione mansioni. Obbligo vaccinale COSTITUZIONALMENTE LEGITTIMO per operatori sanitari in contesto pandemico.",

  "rationale": {
    "main_argument": "Conflitto tra libertà autodeterminazione sanitaria (art. 32 Cost) e tutela salute collettiva (art. 32 Cost). Test di proporzionalità: obbligo vaccinale per sanitari è idone, necessario e proporzionato in contesto pandemia. Licenziamento è extrema ratio dopo tentativo riassegnazione.",

    "rights_identification": [
      {
        "right": "Libertà autodeterminazione sanitaria",
        "constitutional_basis": "Art. 32 comma 2 Cost",
        "content": "Nessuno può essere obbligato a trattamento sanitario se non per legge",
        "holder": "Lavoratrice",
        "limitation": "Clausola 'se non per legge' consente obblighi vaccinali legislativi"
      },
      {
        "right": "Tutela salute collettiva",
        "constitutional_basis": "Art. 32 comma 1 Cost",
        "content": "Salute come interesse della collettività",
        "beneficiaries": "Pazienti, colleghi, comunità",
        "urgency": "Elevata (contesto pandemico)"
      },
      {
        "right": "Diritto al lavoro",
        "constitutional_basis": "Art. 4 Cost",
        "content": "Diritto al lavoro come diritto sociale fondamentale",
        "holder": "Lavoratrice",
        "limitation": "Non assoluto, bilanciabile con altri diritti"
      }
    ],

    "hierarchical_analysis": {
      "level_norms": [
        {"norm": "Art. 32 Cost", "rank": 1, "status": "Costituzione"},
        {"norm": "Art. 4 Cost", "rank": 1, "status": "Costituzione"},
        {"norm": "DL 44/2021", "rank": 3, "status": "Decreto-legge (convertito)"},
        {"norm": "L 300/1970", "rank": 2, "status": "Legge ordinaria"}
      ],
      "conclusion": "Diritti in conflitto hanno STESSO rango costituzionale → impossibile gerarchia → serve bilanciamento"
    },

    "proportionality_test": {
      "suitability_test": {
        "question": "Obbligo vaccinale è idoneo a tutelare salute collettiva?",
        "analysis": "Evidenze scientifiche (OMS, ISS) dimostrano che vaccino riduce trasmissione virus e gravità malattia. Operatori sanitari sono vettori potenziali verso soggetti fragili.",
        "conclusion": "SÌ, idoneo",
        "score": 1.0
      },

      "necessity_test": {
        "question": "Esiste misura meno restrittiva della libertà?",
        "alternatives_considered": [
          {
            "alternative": "Tamponi quotidiani",
            "effectiveness": "Minore (rileva infezione, non previene)",
            "feasibility": "Onerosa e invasiva quotidianamente"
          },
          {
            "alternative": "DPI rafforzati",
            "effectiveness": "Insufficiente (protezione parziale)",
            "feasibility": "Non elimina rischio"
          },
          {
            "alternative": "Smart working",
            "effectiveness": "Inapplicabile (professioni sanitarie richiedono presenza)",
            "feasibility": "Impossibile"
          }
        ],
        "conclusion": "NO misura meno restrittiva con pari efficacia",
        "score": 0.9
      },

      "proportionality_stricto_sensu": {
        "question": "Sacrificio libertà è proporzionato a beneficio salute?",
        "sacrifice": {
          "right_limited": "Autodeterminazione sanitaria",
          "extent": "Limitata a singolo trattamento (vaccino), non permanente",
          "reversibility": "Effetto vaccino temporale, non irreversibile",
          "severity": "Media (non è intervento invasivo permanente)"
        },
        "benefit": {
          "right_protected": "Salute collettiva",
          "beneficiaries": "Pazienti fragili, anziani, immunodepressi",
          "magnitude": "Elevata (prevenzione decessi e malattia grave)",
          "urgency": "Massima (contesto emergenza pandemica)"
        },
        "balancing": "Beneficio (tutela vita e salute collettività) PREVALE su sacrificio (limitazione temporanea autodeterminazione per singolo trattamento)",
        "conclusion": "SÌ, proporzionato",
        "score": 0.85
      },

      "overall_proportionality": "SUPERATO (tutti e 3 test positivi)"
    },

    "contextual_balancing": {
      "specific_category": {
        "category": "Professionisti sanitari",
        "peculiarity": "Contatto diretto con soggetti fragili (pazienti, anziani, immunodepressi)",
        "duty_of_care": "Obbligo deontologico 'primum non nocere' (non nuocere)",
        "impact": "Maggiore legittimità obbligo per questa categoria vs popolazione generale"
      },

      "temporal_context": {
        "situation": "Pandemia COVID-19",
        "emergency_level": "Elevata (stato emergenza dichiarato)",
        "scientific_certainty": "Alta (efficacia vaccino dimostrata)",
        "impact": "Emergenza giustifica limitazioni temporanee diritti"
      },

      "graduated_measures": {
        "step_1": "Obbligo vaccinale (limitazione libertà)",
        "step_2": "Sospensione senza retribuzione (limitazione lavoro temporanea)",
        "step_3": "Riassegnazione mansioni senza contatto pazienti (soluzione intermedia)",
        "step_4": "Licenziamento (extrema ratio)",
        "requirement": "Datore deve tentare step 3 prima di step 4",
        "legitimacy": "Licenziamento legittimo SOLO se riassegnazione impossibile"
      }
    },

    "jurisprudence_reference": {
      "corte_costituzionale": [
        {
          "decision": "Sent. 5/2018",
          "principle": "Obbligo vaccinale legittimo se supera test proporzionalità",
          "application": "Conferma legittimità obblighi vaccinali per tutela salute collettiva"
        },
        {
          "decision": "Sent. 307/1990",
          "principle": "Bilanciamento diritti costituzionali richiede proporzionalità",
          "application": "Metodologia applicata al caso concreto"
        }
      ],
      "cassazione": [
        {
          "decision": "Cass. 23731/2021",
          "principle": "Sospensione lavoratore sanitario non vaccinato legittima",
          "application": "Precedente favorevole a misure restrittive"
        }
      ]
    }
  },

  "conclusion": "Licenziamento LEGITTIMO se extrema ratio (dopo tentativo riassegnazione mansioni). Obbligo vaccinale COSTITUZIONALMENTE PROPORZIONATO per operatori sanitari in pandemia.",

  "conditional_legitimacy": {
    "condition": "Datore di lavoro deve aver tentato riassegnazione a mansioni senza contatto pazienti",
    "if_condition_met": "Licenziamento legittimo",
    "if_condition_not_met": "Licenziamento illegittimo (mancata proporzionalità graduata)"
  },

  "confidence": 0.82,
  "confidence_rationale": "Test proporzionalità superato con margine, giurisprudenza conforme, ma area sensibile con possibili evoluzioni interpretative.",

  "sources": [
    {"constitutional": "art-32-Cost", "usage": "Diritto salute + libertà sanitaria"},
    {"constitutional": "art-4-Cost", "usage": "Diritto lavoro"},
    {"norm": "DL-44-2021", "usage": "Obbligo vaccinale categorie"},
    {"jurisprudence": "C.Cost-5-2018", "usage": "Legittimità obblighi vaccinali"},
    {"jurisprudence": "Cass-23731-2021", "usage": "Sospensione lavoratore"}
  ],

  "dissenting_view": {
    "position": "Licenziamento sempre illegittimo, violazione art. 4 Cost",
    "rationale": "Diritto al lavoro è diritto sociale primario, obbligo vaccinale viola autodeterminazione",
    "weakness": "Ignora bilanciamento e test proporzionalità, contrasta giurisprudenza consolidata"
  },

  "trace_id": "PRIN-uuid",
  "timestamp": "2024-01-15T14:30:45Z"
}
```

### Test di Proporzionalità: Schema Generale

```
┌────────────────────────────────────────────────────────────┐
│  CONFLITTO TRA DIRITTI FONDAMENTALI                        │
│  Diritto A <──────────incompatibile──────────> Diritto B   │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  TEST 1: IDONEITÀ                                          │
│  Domanda: La misura è idonea a tutelare il diritto?       │
│  ─────────────────────────────────────────────────────     │
│  Se NO → misura illegittima (inefficace)                   │
│  Se SÌ → procedi a Test 2                                  │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  TEST 2: NECESSITÀ                                         │
│  Domanda: Esiste alternativa meno restrittiva?            │
│  ─────────────────────────────────────────────────────     │
│  Se SÌ → misura illegittima (non necessaria)               │
│  Se NO → procedi a Test 3                                  │
└──────────────────────────┬─────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│  TEST 3: PROPORZIONALITÀ IN SENSO STRETTO                 │
│  Domanda: Beneficio > Sacrificio?                         │
│  ─────────────────────────────────────────────────────     │
│  Bilancia:                                                 │
│  • Gravità limitazione diritto limitato                   │
│  • Importanza tutela diritto protetto                     │
│  • Urgenza/necessità intervento                           │
│  • Reversibilità limitazione                              │
│                                                            │
│  Se Beneficio ≤ Sacrificio → illegittima                  │
│  Se Beneficio > Sacrificio → LEGITTIMA ✓                  │
└────────────────────────────────────────────────────────────┘
```

---

## Expert 4: Precedent Analyst

### Epistemologia

**Corrente**: Empirismo giuridico, realismo giuridico

**Principi**:
- Il diritto "vivente" è quello applicato dai giudici
- Precedenti vincolanti (Cassazione a Sezioni Unite) o persuasivi
- Evoluzione giurisprudenziale indica trend interpretativi
- Certezza giuridica tramite uniformità giurisprudenza

**Quando attivarlo**:
- Intent: `evoluzione_giurisprudenziale`, qualsiasi query per conferma
- Quando esiste giurisprudenza consolidata
- Quando interpretazione controversa (divergenze tra corti)
- Per validare interpretazioni di altri esperti con case law

### Input

```json
{
  "query": "Contratto sedicenne è nullo o annullabile?",

  "retrieved_jurisprudence": [
    {
      "id": "Cass-18210-2015",
      "court": "Cassazione",
      "chamber": "Sezione III Civile",
      "date": "2015-09-14",
      "massima": "L'atto compiuto dal minore non emancipato è annullabile su istanza del minore stesso o dei suoi rappresentanti legali, anche dopo il raggiungimento della maggiore età.",
      "full_text": "[...estratto sentenza...]",
      "cited_norms": ["cc-art-2", "cc-art-322", "cc-art-1425"],
      "authority_score": 0.92
    },
    {
      "id": "Cass-3281-2019",
      "court": "Cassazione",
      "chamber": "Sezione Lavoro",
      "date": "2019-02-07",
      "massima": "La rappresentanza legale dei genitori è necessaria per gli atti di straordinaria amministrazione compiuti dal minore, anche se emancipato. L'atto compiuto senza rappresentanza è annullabile.",
      "cited_norms": ["cc-art-320", "cc-art-322", "cc-art-394"],
      "authority_score": 0.89
    },
    {
      "id": "Cass-12450-2018",
      "court": "Cassazione",
      "chamber": "Sezione I Civile",
      "date": "2018-05-16",
      "massima": "Il minore può ratificare l'atto annullabile dopo il raggiungimento della maggiore età, sanandone i vizi.",
      "cited_norms": ["cc-art-322", "cc-art-1444"],
      "authority_score": 0.88
    },
    {
      "id": "App-Milano-1234-2020",
      "court": "Appello Milano",
      "date": "2020-03-15",
      "massima": "Il contratto stipulato da minorenne è annullabile, non nullo. La distinzione è rilevante per prescrizione azione.",
      "cited_norms": ["cc-art-322", "cc-art-1418", "cc-art-1442"],
      "authority_score": 0.65
    }
  ],

  "literal_interpretation": "ANNULLABILE (da Literal Interpreter)",
  "systemic_interpretation": "ANNULLABILE (da Systemic-Teleological)"
}
```

### Metodologia

**Step di reasoning**:

1. **Analisi orientamento giurisprudenziale**
   - Identificare ratio decidendi (motivo decisione)
   - Distinguere obiter dicta (affermazioni incidentali)
   - Classificare per grado corte (Cassazione > Appello > Tribunale)

2. **Verifica uniformità**
   - Tutte sentenze concordi? → orientamento consolidato
   - Divergenze? → orientamento controverso
   - Evoluzione temporale? → trend interpretativo

3. **Distinguishing**
   - Fattispecie sentenza simile a query?
   - Differenze rilevanti che giustificano soluzione diversa?

4. **Applicazione al caso concreto**
   - Precedente è vincolante o persuasivo?
   - Soluzione giurisprudenziale si applica alla fattispecie?

### Output

```json
{
  "expert": "Precedent_Analyst",
  "interpretation": "Contratto sedicenne è ANNULLABILE (non nullo). Orientamento CONSOLIDATO in Cassazione.",

  "rationale": {
    "main_argument": "Giurisprudenza di Cassazione è unanime e consolidata: atti del minore sono annullabili (art. 322 c.c.), non nulli. Nessuna divergenza rilevata negli ultimi 10 anni. Ratio decidendi: distinzione tra invalidità radicale (nullità) e relativa (annullabilità) per tutelare minore con azione costitutiva.",

    "jurisprudential_orientation": {
      "status": "CONSOLIDATO",
      "uniformity": "100% sentenze concordi (4/4)",
      "temporal_consistency": "Orientamento stabile dal 2015 a oggi",
      "court_levels": {
        "cassazione": "Unanime (3 sentenze)",
        "appello": "Conforme (1 sentenza)",
        "tribunale": "Nessuna sentenza contraria rilevata"
      }
    },

    "case_analysis": [
      {
        "case_id": "Cass-18210-2015",
        "authority": 0.92,
        "binding_level": "Persuasivo (non Sezioni Unite)",
        "relevance": 1.0,

        "ratio_decidendi": "Atto minore è annullabile ex art. 322 c.c. Annullabilità (non nullità) perché norma tutela interesse minore (relativo), non interesse generale (assoluto).",

        "fact_pattern": {
          "description": "Minore 16 anni stipula contratto compravendita immobile senza rappresentanza genitori",
          "similarity_to_query": 1.0,
          "distinguishing_factors": "Nessuno (fattispecie identica)"
        },

        "legal_reasoning": "Corte distingue nullità (art. 1418: vizi strutturali contratto, rilevabile d'ufficio, imprescrittibile) da annullabilità (art. 1425: vizi della volontà, serve istanza parte, prescrizione 5 anni). Minore età rientra in annullabilità.",

        "cited_norms": ["cc-art-322", "cc-art-1425", "cc-art-1442"],

        "precedents_cited": ["Cass. 5447/2010", "Cass. 18812/2008"],

        "obiter_dicta": "Corte osserva (incidentalmente) che minore può ratificare atto dopo maggiore età, ma questo è obiter (non essenziale per decisione)."
      },

      {
        "case_id": "Cass-3281-2019",
        "authority": 0.89,
        "binding_level": "Persuasivo",
        "relevance": 0.85,

        "ratio_decidendi": "Atti straordinaria amministrazione di minore (anche emancipato) senza rappresentanza sono annullabili.",

        "fact_pattern": {
          "description": "Minore emancipato stipula contratto vendita immobile senza curatore",
          "similarity_to_query": 0.80,
          "distinguishing_factors": "Query non specifica se emancipato, ma ratio applicabile comunque"
        },

        "legal_reasoning": "Conferma orientamento Cass-18210/2015. Aggiunge: anche minore emancipato (che ha parziale capacità) ha atti annullabili se eccedenti ordinaria amministrazione.",

        "application_to_query": "Se sedicenne è emancipato → ancora più chiaro che atto è annullabile. Se non emancipato → a fortiori annullabile."
      },

      {
        "case_id": "Cass-12450-2018",
        "authority": 0.88,
        "binding_level": "Persuasivo",
        "relevance": 0.70,

        "ratio_decidendi": "Atto annullabile del minore può essere ratificato al raggiungimento maggiore età.",

        "fact_pattern": {
          "description": "Minore stipula contratto a 17 anni, ratifica a 19 anni",
          "similarity_to_query": 0.65,
          "distinguishing_factors": "Query non menziona ratifica, ma conferma natura annullabile (non nulla)"
        },

        "legal_reasoning": "Se atto fosse nullo, ratifica sarebbe impossibile (nullità insanabile). Possibilità di ratifica conferma natura annullabile.",

        "application_to_query": "Conferma indiretta che atto minore è annullabile (non nullo)."
      },

      {
        "case_id": "App-Milano-1234-2020",
        "authority": 0.65,
        "binding_level": "Non vincolante (grado inferiore)",
        "relevance": 0.90,

        "ratio_decidendi": "Contratto minorenne annullabile, non nullo. Distinzione rilevante per termine prescrizione (5 anni vs imprescrittibilità).",

        "fact_pattern": {
          "description": "Minore 16 anni stipula contratto, azione annullamento dopo 4 anni",
          "similarity_to_query": 0.95,
          "distinguishing_factors": "Nessuno rilevante"
        },

        "legal_reasoning": "Corte Appello si conforma a orientamento Cassazione. Sottolinea rilevanza pratica distinzione: nullità rilevabile sempre, annullabilità prescrive in 5 anni (art. 1442).",

        "application_to_query": "Conferma orientamento consolidato anche in corti inferiori."
      }
    ],

    "divergent_interpretations": {
      "found": false,
      "note": "Nessuna sentenza contraria rilevata. Orientamento unanime."
    },

    "temporal_evolution": {
      "period": "2015-2024",
      "trend": "STABILE",
      "evolution_narrative": "Orientamento consolidato da almeno 2015, confermato costantemente senza oscillazioni. Precedenti citati risalgono a 2008-2010, indicando consolidamento ventennale.",
      "prediction": "Orientamento prevedibilmente stabile nei prossimi anni (assenza fattori innovativi)"
    },

    "distinguishing_analysis": {
      "query_fact_pattern": "Contratto sedicenne",
      "similar_cases": ["Cass-18210-2015 (identica)", "App-Milano-1234-2020 (identica)"],
      "distinguishable_cases": [],
      "conclusion": "Nessun distinguishing necessario. Precedenti direttamente applicabili."
    },

    "consensus_with_other_experts": {
      "literal_interpreter": {
        "agreement": true,
        "note": "Literal conclude ANNULLABILE da art. 322. Giurisprudenza conferma."
      },
      "systemic_teleological": {
        "agreement": true,
        "note": "Systemic conclude ANNULLABILE da ratio. Giurisprudenza conferma."
      },
      "principles_balancer": {
        "agreement": "N/A",
        "note": "Caso non coinvolge bilanciamento costituzionale."
      }
    }
  },

  "conclusion": "ANNULLABILE (orientamento consolidato Cassazione, unanime, stabile temporalmente)",

  "confidence": 0.95,
  "confidence_rationale": "Orientamento unanime in Cassazione, nessuna sentenza contraria, stabilità temporale decennale. Altissima probabilità che giudice applichi stesso orientamento.",

  "practical_implications": {
    "action_required": "Istanza di annullamento da parte minore o rappresentanti (art. 322)",
    "legitimation": "Attiva: solo minore o rappresentanti legali possono agire",
    "prescription": "5 anni dal raggiungimento maggiore età (art. 1442)",
    "effects_annulment": "Retroattivi (restituzione prestazioni, art. 1443)",
    "ratification_possible": "Sì, al raggiungimento maggiore età (Cass-12450-2018)"
  },

  "predictability": {
    "litigation_risk": "BASSO",
    "judge_likely_outcome": "ANNULLABILITÀ (95% probabilità)",
    "recommendation": "Soluzione giuridicamente certa, rischio contenzioso minimo"
  },

  "sources": [
    {
      "type": "jurisprudence",
      "id": "Cass-18210-2015",
      "authority": 0.92,
      "relevance": 1.0,
      "usage": "Ratio decidendi principale"
    },
    {
      "type": "jurisprudence",
      "id": "Cass-3281-2019",
      "authority": 0.89,
      "relevance": 0.85,
      "usage": "Conferma orientamento"
    },
    {
      "type": "jurisprudence",
      "id": "Cass-12450-2018",
      "authority": 0.88,
      "relevance": 0.70,
      "usage": "Ratifica = conferma annullabilità"
    },
    {
      "type": "jurisprudence",
      "id": "App-Milano-1234-2020",
      "authority": 0.65,
      "relevance": 0.90,
      "usage": "Conformità corti inferiori"
    }
  ],

  "trace_id": "PREC-uuid",
  "timestamp": "2024-01-15T14:30:48Z"
}
```

### Tipologie di Orientamenti Giurisprudenziali

| Tipo | Caratteristiche | Affidabilità | Esempio |
|------|----------------|--------------|---------|
| **Consolidato** | Unanime, stabile >5 anni, più gradi giudizio | Altissima (95%) | Contratto minore = annullabile |
| **Maggioritario** | Prevalente ma con qualche dissent | Alta (80%) | Danno non patrimoniale: risarcibile se danno biologico |
| **Oscillante** | Alterna tra interpretazioni | Media (60%) | Licenziamento verbale: valido o nullo? |
| **Contrasti** | Divergenze tra sezioni Cassazione | Bassa (40%) | Usucapione beni pubblici: possibile o no? |
| **Innovativo** | Recente, non ancora consolidato | Incerta (30%) | Responsabilità piattaforme per contenuti utenti |
| **In evoluzione** | Trend di cambiamento visibile | Variabile | Privacy vs trasparenza: bilanciamento in evoluzione |

---

## Coordinamento tra Esperti

### Scenario 1: Convergenza (query semplice)

```
Query: "Contratto sedicenne è nullo o annullabile?"

┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ LITERAL        │    │ PRECEDENT      │    │ (altri esperti │
│ INTERPRETER    │    │ ANALYST        │    │  non attivati) │
└────────────────┘    └────────────────┘    └────────────────┘
        │                      │
        ↓                      ↓
    "ANNULLABILE          "ANNULLABILE
     (Art. 322)"          (Cass. unanime)"
        │                      │
        └──────────┬───────────┘
                   ↓
            ┌─────────────┐
            │ SYNTHESIS   │
            │ Convergent  │
            └─────────────┘
                   ↓
            Confidence: 0.95
            "ANNULLABILE (certezza alta)"
```

### Scenario 2: Divergenza (query complessa)

```
Query: "Licenziamento lavoratrice non vaccinata è legittimo?"

┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ LITERAL    │  │ SYSTEMIC   │  │ PRINCIPLES │  │ PRECEDENT  │
└────────────┘  └────────────┘  └────────────┘  └────────────┘
      │               │               │               │
      ↓               ↓               ↓               ↓
  "Letteralmente  "Ratio: tutela "Bilanciamento "Giurisprudenza
   obbligo →       salute →        art.32 vs 4:  recente →
   legittimo"      legittimo"      legittimo     favorevole"
   (conf: 0.8)     (conf: 0.75)    (conf: 0.82)  (conf: 0.85)
      │               │               │               │
      └───────────────┴───────────────┴───────────────┘
                          ↓
                   ┌─────────────┐
                   │ SYNTHESIS   │
                   │ Convergent  │
                   │ (tutti      │
                   │  d'accordo) │
                   └─────────────┘
                          ↓
                  Confidence: 0.85
                  "LEGITTIMO (consensus)"
```

### Scenario 3: Conflitto (richiede Synthesis complessa)

```
Query: "Eutanasia consensuale è reato?"

┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ LITERAL    │  │ SYSTEMIC   │  │ PRINCIPLES │  │ PRECEDENT  │
└────────────┘  └────────────┘  └────────────┘  └────────────┘
      │               │               │               │
      ↓               ↓               ↓               ↓
  "Art. 579      "Ratio: tutela  "Conflitto:      "Sent. 242/2019
   (omicidio       vita →          vita vs         Corte Cost.:
   consens.):      SÌ reato"       dignità →       depenaliz.
   SÌ reato"                       AMBIGUO"        parziale"
   (conf: 0.9)    (conf: 0.7)     (conf: 0.5)     (conf: 0.8)
      │               │               │               │
      └───────────────┴───────────────┴───────────────┘
                          ↓
                   ┌─────────────┐
                   │ SYNTHESIS   │
                   │ Divergent   │
                   │ (weighted)  │
                   └─────────────┘
                          ↓
                  Confidence: 0.65
                  "Reato MA depenalizzato in condizioni
                   specifiche (Sent. 242/2019)"
```

---

**FINE PARTE 3**

---

**Prossimi step**: Parte 4 conterrà Iterative Loop + Synthesis.

## Iterative Loop

Il **Loop Iterativo** consente al sistema di recuperare informazioni aggiuntive quando la prima iterazione non produce risultati sufficientemente affidabili.

### Principio Architetturale

```
┌─────────────────────────────────────────────────────────────┐
│  ITERATION 1                                                 │
│  ────────────────────────────────────────────────────────    │
│  Query Understanding → KG Enrichment → Router → Retrieval    │
│  → Experts → Synthesis                                       │
│                                                               │
│  Output: confidence = 0.65 (< threshold)                     │
│          gaps = ["norma su emancipazione mancante"]          │
└──────────────────────────────┬────────────────────────────────┘
                               ↓
                     ┌──────────────────┐
                     │ STOP CRITERIA    │
                     │ (ML-based RLCF)  │
                     └──────────────────┘
                               ↓
                    Should iterate? YES
                    (confidence < 0.80 AND gaps identified)
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  ITERATION 2                                                 │
│  ────────────────────────────────────────────────────────    │
│  Focus: recupera norma emancipazione (cc-art-390)            │
│  Router (targeted) → Retrieval (focused) → Experts → Synth   │
│                                                               │
│  Output: confidence = 0.88 (> threshold)                     │
│          gaps = []                                           │
└──────────────────────────────┬────────────────────────────────┘
                               ↓
                     ┌──────────────────┐
                     │ STOP CRITERIA    │
                     └──────────────────┘
                               ↓
                    Should iterate? NO
                    (confidence OK AND no gaps)
                               ↓
                        ┌──────────┐
                        │ FINAL    │
                        │ ANSWER   │
                        └──────────┘
```

### Quando Iterare

**Trigger per nuova iterazione**:

1. **Confidence insufficiente**
   - Threshold: varia per intent (learned via RLCF)
   - Esempio: intent=`validità_atto` richiede confidence > 0.85
   - Esempio: intent=`bilanciamento_diritti` richiede confidence > 0.80

2. **Gap informativi identificati**
   - Esperti segnalano: "Need more data on X"
   - Esempio: "Manca norma su eccezione emancipazione"
   - Esempio: "Giurisprudenza incompleta su punto Y"

3. **Conflitto irrisolto tra esperti**
   - Divergenza > 0.40 (distanza tra interpretazioni)
   - Esempio: Literal dice "nullo", Precedent dice "annullabile"
   - Richiede dati aggiuntivi per risolvere

4. **Query complessità alta + risultato incerto**
   - Complexity score > 0.75 AND confidence < 0.80
   - Caso border-line che richiede approfondimento

**Quando NON iterare (stop)**:

1. **Confidence sufficiente + consensus**
   - Tutti esperti d'accordo, confidence media > threshold

2. **Max iterations raggiunto**
   - Adattivo: semplice=max 2, complessa=max 5 (learned via RLCF)
   - Safeguard contro loop infiniti

3. **Nessun gap identificato**
   - Retrieval ha recuperato tutte informazioni rilevanti disponibili

4. **Marginal improvement**
   - Iterazione aggiuntiva porterebbe miglioramento < 5%
   - Costo/beneficio non giustifica iterazione

### Stop Criteria: ML-Based (RLCF)

Il sistema apprende quando fermarsi tramite feedback.

**Feature set per decisione**:

```json
{
  "query_features": {
    "intent": "validità_atto",
    "complexity_score": 0.68,
    "num_concepts": 3,
    "temporal_complexity": false
  },

  "iteration_state": {
    "current_iteration": 1,
    "max_iterations_learned": 3
  },

  "retrieval_state": {
    "norms_retrieved": 4,
    "jurisprudence_found": 2,
    "gaps_identified": ["emancipazione"],
    "coverage_score": 0.75
  },

  "expert_state": {
    "experts_activated": ["Literal", "Precedent"],
    "confidence_scores": [0.85, 0.78],
    "confidence_avg": 0.815,
    "confidence_std": 0.035,
    "consensus": true,
    "divergence_score": 0.12
  },

  "synthesis_state": {
    "synthesis_mode": "convergent",
    "final_confidence": 0.82,
    "minority_views": []
  }
}
```

**Decisione ML model**:

```json
{
  "decision": "STOP",
  "rationale": [
    "Confidence (0.82) > threshold_learned (0.80) for intent='validità_atto'",
    "Consensus achieved (divergence=0.12 < 0.30)",
    "Coverage acceptable (0.75 > 0.70)",
    "Marginal improvement predicted < 5% if iterate"
  ],
  "confidence_in_decision": 0.91,
  "alternative": {
    "decision": "ITERATE",
    "probability": 0.09,
    "reason": "Gap 'emancipazione' potrebbe essere rilevante"
  }
}
```

**RLCF training data**:

```json
{
  "episode": {
    "features": {...},
    "decision": "STOP",
    "outcome": {
      "user_rating": 4.5,
      "user_feedback": "Risposta corretta ma avrebbe potuto approfondire emancipazione",
      "actual_iterations_needed": 2
    },
    "reward": -0.2,
    "lesson": "For this query type, iterate once when gap='emancipazione' even if confidence>0.80"
  }
}
```

**Adaptive thresholds learned**:

| Intent | Confidence Threshold | Consensus Threshold | Coverage Threshold |
|--------|---------------------|---------------------|-------------------|
| `validità_atto` | 0.85 | 0.15 (low divergence) | 0.75 |
| `interpretazione_norma` | 0.80 | 0.20 | 0.70 |
| `bilanciamento_diritti` | 0.75 | 0.30 (tolera divergenza) | 0.80 |
| `conformità_costituzionale` | 0.80 | 0.25 | 0.85 |
| `evoluzione_giurisprudenziale` | 0.78 | 0.25 | 0.75 |
| `conseguenze_giuridiche` | 0.82 | 0.18 | 0.72 |

**Max iterations adaptive**:

| Complexity Score | Max Iterations (learned) |
|-----------------|-------------------------|
| < 0.5 (semplice) | 2 |
| 0.5 - 0.7 (media) | 3 |
| 0.7 - 0.85 (alta) | 4 |
| > 0.85 (molto alta) | 5 |

### Esempio: Iterazione Necessaria

**Iteration 1**:

```json
{
  "query": "Minore emancipato può comprare casa?",

  "retrieval_result_iter1": {
    "norms": ["cc-art-2", "cc-art-322"],
    "gaps": ["emancipazione", "acquisto_immobile"]
  },

  "expert_outputs_iter1": {
    "Literal": {
      "interpretation": "Minore non può (Art. 2: maggiore età = 18 anni)",
      "confidence": 0.75,
      "caveat": "Non ho trovato norma su emancipazione, potrebbe cambiare risposta"
    },
    "Precedent": {
      "interpretation": "Probabilmente non può",
      "confidence": 0.65,
      "caveat": "Giurisprudenza su emancipazione mancante"
    }
  },

  "synthesis_iter1": {
    "conclusion": "Probabilmente NO",
    "confidence": 0.70,
    "gaps": ["Manca analisi emancipazione (cc-art-390, cc-art-394)"]
  },

  "stop_criteria_decision": {
    "decision": "ITERATE",
    "reasons": [
      "Confidence (0.70) < threshold (0.80)",
      "Gap critico identificato: emancipazione",
      "Esperti hanno segnalato incertezza"
    ]
  }
}
```

**Iteration 2** (focused retrieval):

```json
{
  "retrieval_plan_iter2": {
    "focus": "Gap filling: emancipazione + acquisto immobile",
    "kg_agent": "Expand from emancipazione concept",
    "api_agent": ["cc-art-390", "cc-art-394", "cc-art-1470"],
    "vectordb_agent": "Giurisprudenza emancipato acquisto immobile"
  },

  "retrieval_result_iter2": {
    "norms": [
      "cc-art-390 (emancipazione)",
      "cc-art-394 (atti emancipato: ordinaria vs straordinaria amministrazione)",
      "cc-art-1470 (compravendita immobile)"
    ],
    "jurisprudence": ["Cass-5674-2017: Emancipato può vendere, non acquistare immobile senza curatore"]
  },

  "expert_outputs_iter2": {
    "Literal": {
      "interpretation": "Emancipato può atti ordinaria amministrazione. Acquisto immobile è straordinaria → serve curatore",
      "confidence": 0.90
    },
    "Systemic": {
      "interpretation": "Ratio emancipazione: autonomia ma protezione. Acquisto immobile eccede protezione → curatore necessario",
      "confidence": 0.85
    },
    "Precedent": {
      "interpretation": "Cass. consolidata: emancipato NON può acquistare immobile senza curatore",
      "confidence": 0.92
    }
  },

  "synthesis_iter2": {
    "conclusion": "NO, minore emancipato NON può acquistare casa senza curatore (Art. 394 + Cass. 5674/2017)",
    "confidence": 0.89,
    "gaps": []
  },

  "stop_criteria_decision": {
    "decision": "STOP",
    "reasons": [
      "Confidence (0.89) > threshold (0.80)",
      "Consensus tra esperti (divergence = 0.08)",
      "Gap risolto (emancipazione ora coperta)",
      "Coverage completa (1.0)"
    ]
  }
}
```

**Outcome**: 2 iterazioni necessarie. Prima insufficiente (gap critico), seconda risolve.

---

## Synthesis

Il **Synthesis Component** combina gli output di più esperti in una risposta coerente e ben fondata.

### Architettura

```
┌─────────────────────────────────────────────────────────────┐
│  EXPERT OUTPUTS                                              │
│  ────────────────────────────────────────────────────────    │
│  • Literal: "ANNULLABILE (conf: 0.90)"                      │
│  • Systemic: "ANNULLABILE (conf: 0.85)"                     │
│  • Precedent: "ANNULLABILE (conf: 0.92)"                    │
│  • Principles: NOT ACTIVATED                                 │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │  CONSENSUS ANALYSIS  │
                    │  Convergent mode     │
                    └──────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  SYNTHESIS OUTPUT                                            │
│  ────────────────────────────────────────────────────────    │
│  Conclusion: "ANNULLABILE"                                   │
│  Confidence: 0.89 (weighted average)                         │
│  Consensus: TRUE (all experts agree)                         │
│  Minority views: []                                          │
│                                                               │
│  Rationale: "Tutti e tre gli esperti concordano:            │
│  - Literal: Art. 322 dice 'possono essere annullati'        │
│  - Systemic: Ratio tutela minore → annullabilità            │
│  - Precedent: Cass. unanime su annullabilità                │
│  Nessuna interpretazione alternativa valida."                │
└─────────────────────────────────────────────────────────────┘
```

### Modalità Operative

**1. Convergent Mode** (esperti d'accordo):

```json
{
  "mode": "convergent",
  "trigger": "divergence_score < 0.30",

  "expert_outputs": [
    {
      "expert": "Literal",
      "conclusion": "ANNULLABILE",
      "confidence": 0.90,
      "key_argument": "Art. 322: 'possono essere annullati'"
    },
    {
      "expert": "Systemic",
      "conclusion": "ANNULLABILE",
      "confidence": 0.85,
      "key_argument": "Ratio tutela minore → annullabilità relativa"
    },
    {
      "expert": "Precedent",
      "conclusion": "ANNULLABILE",
      "confidence": 0.92,
      "key_argument": "Cass. 18210/2015 consolidata"
    }
  ],

  "synthesis_process": {
    "step_1": "Verify consensus (all agree on 'ANNULLABILE')",
    "step_2": "Aggregate confidence (weighted average by expert reliability)",
    "step_3": "Combine rationales (integrate all key arguments)",
    "step_4": "Identify strongest sources (Precedent: Cass. highest authority)"
  },

  "synthesis_output": {
    "conclusion": "ANNULLABILE",
    "confidence": 0.89,
    "confidence_calculation": "(0.90 × 0.33) + (0.85 × 0.30) + (0.92 × 0.37) = 0.89",
    "weights": {
      "Literal": 0.33,
      "Systemic": 0.30,
      "Precedent": 0.37
    },
    "weight_rationale": "Precedent weighted higher (orientamento consolidato Cassazione)",

    "integrated_rationale": "Il contratto firmato da un sedicenne è ANNULLABILE. Convergenza tra metodologie: (1) Interpretazione letterale: Art. 322 c.c. stabilisce 'possono essere annullati', indicando annullabilità costitutiva su istanza. (2) Analisi sistematica: La ratio della tutela del minore giustifica annullabilità (invalidità relativa) piuttosto che nullità (assoluta), per bilanciare protezione e certezza dei traffici. (3) Giurisprudenza: Orientamento consolidato in Cassazione (Cass. 18210/2015, Cass. 3281/2019) conferma unanimemente annullabilità.",

    "sources_ranked": [
      {"type": "jurisprudence", "id": "Cass-18210-2015", "authority": 0.92},
      {"type": "norm", "id": "cc-art-322", "authority": 1.0},
      {"type": "norm", "id": "cc-art-2", "authority": 1.0}
    ],

    "minority_views": [],
    "caveats": ["Atto può essere ratificato al raggiungimento maggiore età"],
    "practical_implications": ["Serve istanza di parte (minore o rappresentanti)", "Prescrizione 5 anni (art. 1442)"]
  }
}
```

**2. Divergent Mode** (esperti in disaccordo):

```json
{
  "mode": "divergent",
  "trigger": "divergence_score > 0.30",

  "expert_outputs": [
    {
      "expert": "Literal",
      "conclusion": "LEGITTIMO",
      "confidence": 0.85,
      "key_argument": "DL 44/2021 impone obbligo vaccinale → licenziamento conseguenza testuale"
    },
    {
      "expert": "Principles",
      "conclusion": "LEGITTIMO se extrema ratio",
      "confidence": 0.78,
      "key_argument": "Test proporzionalità: legittimo solo dopo tentativo riassegnazione mansioni"
    },
    {
      "expert": "Precedent",
      "conclusion": "LEGITTIMO",
      "confidence": 0.88,
      "key_argument": "Cass. 23731/2021 conferma legittimità sospensione/licenziamento"
    }
  ],

  "divergence_analysis": {
    "literal_vs_principles": {
      "disagreement": "Principles richiede condizionalità (extrema ratio), Literal no",
      "divergence_score": 0.35,
      "nature": "Interpretazione diversa applicabilità (incondizionata vs condizionata)"
    }
  },

  "synthesis_process": {
    "step_1": "Identify majority position (2/3: LEGITTIMO incondizionato)",
    "step_2": "Identify minority position (1/3: LEGITTIMO condizionato)",
    "step_3": "Evaluate strength of minority argument",
    "step_4": "Decide: adopt majority or synthesize intermediate position",
    "decision": "SYNTHESIZE (minority argument has strong constitutional basis)"
  },

  "synthesis_output": {
    "conclusion_majority": "Licenziamento LEGITTIMO",
    "conclusion_nuanced": "Licenziamento LEGITTIMO se preceduto da tentativo riassegnazione mansioni (extrema ratio)",

    "confidence": 0.82,

    "rationale_majority": "La maggioranza degli esperti (Literal, Precedent) conclude per legittimità licenziamento basandosi su: (1) DL 44/2021 impone obbligo vaccinale per sanitari, (2) Giurisprudenza conferma legittimità sospensione (Cass. 23731/2021).",

    "rationale_minority": "L'esperto Principles Balancer, applicando test di proporzionalità costituzionale, sottolinea che licenziamento deve essere extrema ratio: datore deve tentare riassegnazione a mansioni senza contatto pazienti prima di licenziare. Solo se impossibile, licenziamento proporzionato (Art. 4 Cost: diritto al lavoro).",

    "synthesis_adopted": "MAJORITY + CAVEAT",

    "final_answer": {
      "conclusion": "Licenziamento LEGITTIMO, ma solo se extrema ratio",
      "conditions": [
        "Datore deve aver tentato riassegnazione mansioni senza contatto pazienti",
        "Se riassegnazione impossibile → licenziamento legittimo",
        "Se riassegnazione possibile ma non tentata → licenziamento illegittimo"
      ],
      "confidence": 0.82,
      "recommendation": "Verificare se datore ha esplorato alternative prima di licenziare"
    },

    "minority_report": {
      "position": "Licenziamento sempre illegittimo (violazione Art. 4 Cost)",
      "expert_hypothetical": "Principles Balancer (interpretazione minoritaria estrema)",
      "rationale": "Diritto al lavoro prevale su obbligo vaccinale, proporzionalità mai soddisfatta",
      "weakness": "Contrasta con giurisprudenza consolidata, ignora Art. 32 Cost (salute collettiva)",
      "probability": 0.05,
      "note": "Interpretazione possibile ma altamente improbabile in giudizio"
    },

    "sources_ranked": [
      {"type": "norm", "id": "DL-44-2021", "authority": 0.85, "supporting": "majority"},
      {"type": "constitutional", "id": "art-32-Cost", "authority": 1.0, "supporting": "majority"},
      {"type": "constitutional", "id": "art-4-Cost", "authority": 1.0, "supporting": "minority_caveat"},
      {"type": "jurisprudence", "id": "Cass-23731-2021", "authority": 0.88, "supporting": "majority"}
    ]
  }
}
```

### Conflict Resolution: Majority + Minority Report

**Strategia**: Risposta principale (maggioranza) + sezione interpretazioni alternative.

**Vantaggi**:
- Trasparenza massima (utente vede tutte le prospettive)
- Accountability (ogni interpretazione tracciata con fonte)
- Utilità pratica (avvocato può scegliere strategia difensiva)

**Esempio output utente**:

```markdown
## Risposta

**Conclusione**: Licenziamento **LEGITTIMO**, ma solo se preceduto da tentativo di riassegnazione mansioni (extrema ratio).

**Confidence**: 82%

---

### Analisi Convergente

La maggioranza degli esperti giuridici concorda sulla legittimità del licenziamento:

1. **Interpretazione Letterale** (confidence: 85%)
   - DL 44/2021 art. 4 impone obbligo vaccinale per operatori sanitari
   - Violazione obbligo → licenziamento è conseguenza testuale

2. **Analisi Giurisprudenziale** (confidence: 88%)
   - Cass. 23731/2021 conferma legittimità sospensione lavoratore non vaccinato
   - Orientamento consolidato favorevole a misure restrittive

### Interpretazione Minoritaria: Caveat Costituzionale

**Principles Balancer** (confidence: 78%) aggiunge condizionalità costituzionale:

- **Test di proporzionalità**: Licenziamento deve essere extrema ratio
- **Art. 4 Cost** (diritto al lavoro) richiede che datore tenti prima:
  1. Riassegnazione a mansioni senza contatto pazienti
  2. Sospensione temporanea
- Solo se alternative impossibili → licenziamento proporzionato

### Conclusione Sintetizzata

Il licenziamento è **costituzionalmente legittimo** se:
- ✓ Datore ha tentato riassegnazione mansioni (senza contatto pazienti)
- ✓ Riassegnazione risultata impossibile o impraticabile
- ✓ Licenziamento come extrema ratio

Il licenziamento è **illegittimo** se:
- ✗ Datore non ha esplorato alternative
- ✗ Riassegnazione era possibile ma non tentata

**Raccomandazione pratica**: Verificare se il datore di lavoro ha documentato tentativi di riassegnazione prima del licenziamento.

---

### Fonti

- DL 44/2021 art. 4 (Obbligo vaccinale operatori sanitari)
- Art. 32 Cost (Diritto alla salute)
- Art. 4 Cost (Diritto al lavoro)
- Cass. 23731/2021 (Legittimità sospensione lavoratore non vaccinato)
- Corte Cost. 5/2018 (Legittimità obblighi vaccinali con test proporzionalità)
```

### Confidence Aggregation

**Formula weighted average**:

```
confidence_final = Σ (confidence_i × weight_i)

dove:
- confidence_i = confidence dell'esperto i
- weight_i = peso dell'esperto i (based on reliability + applicability)
```

**Calcolo pesi**:

```json
{
  "experts_activated": ["Literal", "Systemic", "Precedent"],

  "base_weights": {
    "Literal": 0.33,
    "Systemic": 0.33,
    "Precedent": 0.34
  },

  "adjustments": {
    "Precedent": "+0.05 (orientamento consolidato Cassazione)",
    "Systemic": "-0.03 (ratio chiara, meno rilevante)"
  },

  "final_weights": {
    "Literal": 0.33,
    "Systemic": 0.30,
    "Precedent": 0.37
  },

  "confidence_calculation": {
    "Literal": "0.90 × 0.33 = 0.297",
    "Systemic": "0.85 × 0.30 = 0.255",
    "Precedent": "0.92 × 0.37 = 0.340",
    "SUM": "0.297 + 0.255 + 0.340 = 0.892"
  },

  "final_confidence": 0.89
}
```

**Boost per consensus**:

```json
{
  "base_confidence": 0.89,
  "consensus_detected": true,
  "consensus_boost": 0.03,
  "final_confidence": 0.92,
  "rationale": "Consensus among all experts increases reliability"
}
```

**Penalty per divergenza**:

```json
{
  "base_confidence": 0.85,
  "divergence_detected": true,
  "divergence_score": 0.42,
  "divergence_penalty": -0.08,
  "final_confidence": 0.77,
  "rationale": "Significant disagreement reduces overall confidence"
}
```

### Esempio Completo: Iterazione + Synthesis

**Query**: "Minore emancipato 17 anni può stipulare contratto lavoro autonomo?"

**Iteration 1**:

```json
{
  "retrieval": {
    "norms": ["cc-art-2", "cc-art-390"],
    "gaps": ["distinzione ordinaria/straordinaria amministrazione"]
  },

  "experts": {
    "Literal": {
      "conclusion": "Incerto (art. 394 menziona 'ordinaria amministrazione' ma non definisce)",
      "confidence": 0.60
    },
    "Systemic": {
      "conclusion": "Probabilmente SÌ (se lavoro non professionale)",
      "confidence": 0.65
    }
  },

  "synthesis": {
    "conclusion": "Incerto",
    "confidence": 0.62,
    "gaps": ["Serve chiarimento su cosa è 'ordinaria amministrazione'"]
  },

  "stop_criteria": "ITERATE (confidence < 0.80, gap critico)"
}
```

**Iteration 2** (focused):

```json
{
  "retrieval_focused": {
    "api_agent": ["cc-art-394", "cc-art-320"],
    "vectordb_agent": "Giurisprudenza 'ordinaria amministrazione' emancipato lavoro"
  },

  "retrieval_result": {
    "jurisprudence": [
      "Cass. 8742/2016: Lavoro autonomo non professionale = ordinaria amministrazione per emancipato",
      "Trib. Milano 2018: Contratto freelance occasionale rientra in autonomia emancipato"
    ]
  },

  "experts": {
    "Literal": {
      "conclusion": "Art. 394 non definisce ma giurisprudenza interpreta estensivamente",
      "confidence": 0.80
    },
    "Systemic": {
      "conclusion": "SÌ, ratio emancipazione supporta autonomia lavorativa non professionale",
      "confidence": 0.85
    },
    "Precedent": {
      "conclusion": "SÌ, Cass. 8742/2016 + Trib. Milano 2018 concordi",
      "confidence": 0.88
    }
  },

  "synthesis": {
    "mode": "convergent",
    "conclusion": "SÌ, minore emancipato PUÒ stipulare contratto lavoro autonomo NON professionale",
    "confidence": 0.84,
    "conditions": ["Lavoro autonomo occasionale (non attività imprenditoriale stabile)"],

    "rationale_integrated": "Convergenza tra metodologie: (1) Art. 394 c.c. non definisce 'ordinaria amministrazione' ma lascia spazio interpretativo. (2) Ratio emancipazione è favorire autonomia responsabile: lavoro autonomo occasionale realizza questa autonomia. (3) Giurisprudenza consolidata (Cass. 8742/2016, Trib. Milano 2018) interpreta estensivamente 'ordinaria amministrazione' per includere lavoro autonomo non professionale.",

    "minority_views": [],

    "sources": [
      {"norm": "cc-art-394", "usage": "Base normativa"},
      {"jurisprudence": "Cass-8742-2016", "authority": 0.88, "usage": "Interpretazione 'ordinaria amministrazione'"},
      {"jurisprudence": "Trib-Milano-2018", "authority": 0.65, "usage": "Conferma orientamento"}
    ]
  },

  "stop_criteria": "STOP (confidence 0.84 > 0.80, consensus, gap risolto)"
}
```

**Final Output**:

```json
{
  "iterations_total": 2,
  "final_conclusion": "SÌ, con condizioni",
  "final_confidence": 0.84,
  "final_rationale": "[vedi synthesis.rationale_integrated]",
  "conditions": ["Lavoro autonomo occasionale, non attività imprenditoriale"],
  "sources": [...]
}
```

---

**FINE PARTE 4**

---

**Prossimi step**: Parte 5 conterrà Traceability System + RLCF Integration completa.

---

## 5. Traceability + RLCF Integration

Questa sezione documenta due aspetti fondamentali del sistema MERL-T:

1. **Traceability**: sistema completo di tracciamento per accountability, audit, e debugging
2. **RLCF Integration**: punti di integrazione del Reinforcement Learning from Community Feedback attraverso tutti i componenti

---

### 5.1 Traceability System

Il sistema di traceability garantisce che **ogni decisione** del sistema sia:
- **Tracciabile**: con Trace ID univoco propagato attraverso tutti i componenti
- **Riproducibile**: con log completo di input/output/decisioni
- **Spiegabile**: con rationale esplicito per ogni scelta
- **Auditabile**: con timestamp, versioni, e metadati per compliance

#### 5.1.1 Architettura Generale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRACE LIFECYCLE                                 │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Query Input  │  → Genera Trace ID: "trc_20250102_143022_a1b2c3"
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│ QUERY UNDERSTANDING                                                  │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "query_understanding"                                     │
│ timestamp: "2025-01-02T14:30:22.145Z"                               │
│ input: { raw_query: "..." }                                         │
│ output: { concepts: [...], intent: "...", complexity: 0.68 }        │
│ model_version: "spacy_lg_v3.7.2"                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ KG ENRICHMENT                                                        │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "kg_enrichment"                                           │
│ timestamp: "2025-01-02T14:30:22.347Z"                               │
│ input: { concepts: [...] }                                          │
│ cypher_queries: [ "MATCH (c:LegalConcept)...", ... ]                │
│ output: { norms: [...], relations: [...] }                          │
│ kg_version: "neo4j_db_v2025-01-01"                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ROUTER                                                               │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "router"                                                  │
│ decisions: [                                                         │
│   { type: "expert_selection", selected: [...], rationale: "..." },  │
│   { type: "retrieval_plan", agents: [...], rationale: "..." }       │
│ ]                                                                    │
│ llm_calls: [ { model: "gpt-4o", tokens: 1234, ... } ]               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RETRIEVAL AGENTS (paralleli)                                         │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "retrieval"                                               │
│ agents: [                                                            │
│   { agent: "kg_agent", norms_retrieved: 8, ... },                   │
│   { agent: "api_agent", texts_retrieved: 8, ... },                  │
│   { agent: "vector_agent", chunks_retrieved: 15, ... }              │
│ ]                                                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ REASONING EXPERTS (paralleli)                                        │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "experts"                                                 │
│ iteration: 1                                                         │
│ experts: [                                                           │
│   { expert: "literal", conclusion: "...", confidence: 0.82, ... },  │
│   { expert: "systemic", conclusion: "...", confidence: 0.76, ... }, │
│   { expert: "principles", conclusion: "...", confidence: 0.71, ...},│
│   { expert: "precedent", conclusion: "...", confidence: 0.88, ... } │
│ ]                                                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ITERATIVE LOOP DECISION                                              │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "loop_controller"                                         │
│ iteration: 1                                                         │
│ decision: "CONTINUE"                                                 │
│ rationale: "Divergenza 0.24 > threshold 0.15, serve iterazione"     │
│ stop_criteria_evaluated: { confidence: false, consensus: false, ... }│
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                   ┌───────┴───────┐
                   │  ITERATION 2  │  (nuovo ciclo Experts → Loop)
                   └───────┬───────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SYNTHESIS                                                            │
│ ─────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                              │
│ component: "synthesis"                                               │
│ mode: "divergent"                                                    │
│ majority_position: "Licenziamento LEGITTIMO"                        │
│ minority_report: { position: "...", experts: [...] }                │
│ final_confidence: 0.815                                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT + TRACE EXPORT                                          │
│ ──────────────────────────────────────────────────────────────────── │
│ trace_id: "trc_20250102_143022_a1b2c3"                               │
│ total_duration_ms: 4327                                               │
│ total_llm_tokens: 18450                                               │
│ iterations_count: 2                                                   │
│ export_formats: [ "json", "human_readable_md" ]                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### 5.1.2 Trace ID Schema

Il Trace ID è generato all'inizio della query e propagato attraverso tutti i componenti.

**Formato**:
```
trc_{timestamp}_{random_suffix}

Esempio: trc_20250102_143022_a1b2c3
```

**Componenti**:
- `trc_`: prefisso fisso
- `{timestamp}`: `YYYYMMDD_HHMMSS` (UTC)
- `{random_suffix}`: 6 caratteri alfanumerici per unicità

#### 5.1.3 Trace Log Structure

Ogni componente logga la propria esecuzione in formato strutturato JSON.

**Schema Generale**:

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "query_understanding | kg_enrichment | router | retrieval | experts | synthesis | loop_controller",
  "timestamp": "2025-01-02T14:30:22.145Z",
  "iteration": 1,
  "input": { ... },
  "output": { ... },
  "metadata": {
    "model_version": "spacy_lg_v3.7.2",
    "duration_ms": 245,
    "status": "success | error",
    "error_message": null
  }
}
```

**Campi Comuni**:

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `trace_id` | string | ID univoco della query |
| `component` | enum | Componente che ha generato il log |
| `timestamp` | ISO 8601 | Timestamp preciso (millisecondi) |
| `iteration` | int | Numero iterazione (per Experts/Loop) |
| `input` | object | Dati in input al componente |
| `output` | object | Dati in output dal componente |
| `metadata.duration_ms` | int | Tempo esecuzione (millisecondi) |
| `metadata.status` | enum | `success` o `error` |

#### 5.1.4 Trace per Componente

##### Query Understanding Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "query_understanding",
  "timestamp": "2025-01-02T14:30:22.145Z",
  "input": {
    "raw_query": "Un minorenne può stipulare un contratto valido?"
  },
  "output": {
    "concepts": [
      {
        "name": "capacità_di_agire",
        "confidence": 0.92,
        "category": "soggetti_diritto"
      },
      {
        "name": "validità_contrattuale",
        "confidence": 0.88,
        "category": "contratti"
      }
    ],
    "intent": "validità_atto",
    "intent_confidence": 0.89,
    "complexity": 0.68,
    "entities": [
      { "text": "minorenne", "label": "LEGAL_SUBJECT", "span": [3, 12] }
    ]
  },
  "metadata": {
    "model_version": "spacy_lg_v3.7.2",
    "ml_model": "intent_classifier_v2.1",
    "duration_ms": 245,
    "status": "success"
  }
}
```

##### KG Enrichment Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "kg_enrichment",
  "timestamp": "2025-01-02T14:30:22.347Z",
  "input": {
    "concepts": ["capacità_di_agire", "validità_contrattuale"],
    "entities": [
      { "text": "minorenne", "label": "LEGAL_SUBJECT" }
    ]
  },
  "cypher_queries_executed": [
    {
      "query_template": "concept_to_norm",
      "cypher": "MATCH (c:LegalConcept)<-[:REGULATES]-(a:Article) WHERE c.name IN $concepts RETURN ...",
      "parameters": {
        "concepts": ["capacità_di_agire", "validità_contrattuale"]
      },
      "results_count": 8
    },
    {
      "query_template": "related_norms_expansion",
      "cypher": "MATCH (a:Article)-[:MODIFIES|DEROGATES]->(related:Article) WHERE a.id IN $norm_ids RETURN ...",
      "parameters": {
        "norm_ids": ["cc_art_2", "cc_art_322", ...]
      },
      "results_count": 5
    }
  ],
  "output": {
    "norms": [
      {
        "id": "cc_art_2",
        "title": "Maggiore età. Capacità di agire",
        "hierarchy": "codice",
        "regulates_concepts": ["capacità_di_agire"]
      },
      {
        "id": "cc_art_322",
        "title": "Atti che il minore può compiere",
        "hierarchy": "codice",
        "regulates_concepts": ["capacità_di_agire", "validità_contrattuale"]
      }
    ],
    "total_norms_found": 8,
    "relations_found": 5
  },
  "metadata": {
    "kg_version": "neo4j_db_v2025-01-01",
    "total_query_time_ms": 102,
    "duration_ms": 125,
    "status": "success"
  }
}
```

##### Router Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "router",
  "timestamp": "2025-01-02T14:30:22.512Z",
  "input": {
    "intent": "validità_atto",
    "complexity": 0.68,
    "concepts": ["capacità_di_agire", "validità_contrattuale"],
    "norms_enriched": ["cc_art_2", "cc_art_322", ...]
  },
  "decisions": [
    {
      "type": "expert_selection",
      "selected_experts": ["literal", "precedent"],
      "rationale": "Intent 'validità_atto' + complessità < 0.7 → servono interpretazione letterale + conferma giurisprudenziale",
      "confidence": 0.87,
      "rlcf_checkpoint": "router_expert_v2.3"
    },
    {
      "type": "retrieval_plan",
      "agents_selected": ["kg_agent", "api_agent"],
      "kg_strategy": "expand_related_norms",
      "api_strategy": "full_text_retrieval",
      "vector_excluded_reason": "Norma chiara, non serve ricerca semantica",
      "rationale": "Norme già identificate da KG Enrichment, serve solo testo completo + espansione relazioni",
      "rlcf_checkpoint": "router_retrieval_v1.8"
    },
    {
      "type": "iteration_expectation",
      "expected_iterations": 1,
      "expected_stop_reason": "alta_confidenza",
      "rationale": "Query di validità su norma chiara, probabile convergenza immediata",
      "rlcf_checkpoint": "router_iteration_v1.5"
    }
  ],
  "llm_calls": [
    {
      "model": "gpt-4o",
      "prompt_tokens": 1245,
      "completion_tokens": 387,
      "total_tokens": 1632,
      "temperature": 0.3,
      "call_id": "llm_router_20250102_143022_01"
    }
  ],
  "metadata": {
    "router_version": "rlcf_trained_v2.3",
    "duration_ms": 1340,
    "status": "success"
  }
}
```

##### Retrieval Agents Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "retrieval",
  "timestamp": "2025-01-02T14:30:23.892Z",
  "input": {
    "retrieval_plan": {
      "agents": ["kg_agent", "api_agent"],
      "kg_strategy": "expand_related_norms",
      "api_strategy": "full_text_retrieval"
    }
  },
  "agents_execution": [
    {
      "agent": "kg_agent",
      "start_time": "2025-01-02T14:30:23.895Z",
      "end_time": "2025-01-02T14:30:24.103Z",
      "cypher_queries": [
        {
          "template": "expand_related_norms",
          "cypher": "MATCH (a:Article)-[r:MODIFIES|DEROGATES|INTEGRATES*1..2]->(related:Article) WHERE a.id IN $norm_ids RETURN ...",
          "results_count": 5
        }
      ],
      "output": {
        "norms_retrieved": 8,
        "norms": [
          { "id": "cc_art_2", "relations": [...] },
          { "id": "cc_art_322", "relations": [...] }
        ]
      },
      "metadata": {
        "duration_ms": 208,
        "status": "success"
      }
    },
    {
      "agent": "api_agent",
      "start_time": "2025-01-02T14:30:23.896Z",
      "end_time": "2025-01-02T14:30:24.512Z",
      "api_calls": [
        {
          "endpoint": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:codice.civile:1942-03-16;262~art2",
          "http_status": 200,
          "response_time_ms": 245
        },
        {
          "endpoint": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:codice.civile:1942-03-16;262~art322",
          "http_status": 200,
          "response_time_ms": 289
        }
      ],
      "output": {
        "texts_retrieved": 8,
        "total_characters": 12456
      },
      "metadata": {
        "duration_ms": 616,
        "status": "success"
      }
    }
  ],
  "metadata": {
    "total_duration_ms": 620,
    "parallel_execution": true,
    "status": "success"
  }
}
```

##### Experts Trace (Iteration 1)

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "experts",
  "timestamp": "2025-01-02T14:30:24.520Z",
  "iteration": 1,
  "input": {
    "norms": [...],
    "texts": [...],
    "query": "Un minorenne può stipulare un contratto valido?",
    "experts_selected": ["literal", "precedent"]
  },
  "experts_execution": [
    {
      "expert": "literal",
      "start_time": "2025-01-02T14:30:24.522Z",
      "end_time": "2025-01-02T14:30:26.103Z",
      "reasoning": {
        "norms_analyzed": ["cc_art_2", "cc_art_322"],
        "textual_analysis": [
          {
            "norm": "cc_art_2",
            "disposizione": "La maggiore età è fissata al compimento del diciottesimo anno.",
            "ratio": "Chi non ha compiuto 18 anni è minorenne"
          },
          {
            "norm": "cc_art_322",
            "disposizione": "Il minore è ammesso a compiere gli atti per i quali è stabilita un'età minore...",
            "ratio": "Esistono eccezioni espresse (es. Art. 2238 per lavoro)"
          }
        ],
        "sillogismo": [
          "MAGGIORE: Il contratto stipulato da incapace è annullabile (Art. 1425)",
          "MINORE: Soggetto è minorenne (< 18 anni)",
          "CONCLUSIONE: Contratto ANNULLABILE salvo eccezioni espresse (Art. 322)"
        ]
      },
      "conclusion": "Contratto ANNULLABILE (salvo eccezioni Art. 322)",
      "confidence": 0.92,
      "sources": [
        { "norm": "cc_art_2", "weight": 0.5 },
        { "norm": "cc_art_322", "weight": 0.3 },
        { "norm": "cc_art_1425", "weight": 0.2 }
      ],
      "llm_calls": [
        {
          "model": "gpt-4o",
          "prompt_tokens": 2345,
          "completion_tokens": 678,
          "temperature": 0.2
        }
      ],
      "metadata": {
        "duration_ms": 1581,
        "status": "success"
      }
    },
    {
      "expert": "precedent",
      "start_time": "2025-01-02T14:30:24.523Z",
      "end_time": "2025-01-02T14:30:26.892Z",
      "reasoning": {
        "precedents_analyzed": [
          {
            "court": "Cass. Civ. Sez. I",
            "date": "2018-03-15",
            "number": "6234/2018",
            "massima": "Il contratto stipulato dal minore è annullabile su istanza del rappresentante legale o del minore stesso dopo la maggiore età (Art. 1441-1442)",
            "orientation": "consolidata",
            "relevance": 0.89
          }
        ],
        "orientation_synthesis": "Giurisprudenza consolidata conferma annullabilità contratti minorenne"
      },
      "conclusion": "Contratto ANNULLABILE (orientamento consolidato)",
      "confidence": 0.88,
      "sources": [
        { "precedent": "Cass. 6234/2018", "weight": 0.6 },
        { "norm": "cc_art_1441", "weight": 0.4 }
      ],
      "llm_calls": [
        {
          "model": "gpt-4o",
          "prompt_tokens": 3456,
          "completion_tokens": 892,
          "temperature": 0.2
        }
      ],
      "metadata": {
        "duration_ms": 2369,
        "status": "success"
      }
    }
  ],
  "convergence_analysis": {
    "conclusions_aligned": true,
    "divergence_score": 0.04,
    "confidence_avg": 0.90
  },
  "metadata": {
    "total_duration_ms": 2400,
    "parallel_execution": true,
    "status": "success"
  }
}
```

##### Loop Controller Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "loop_controller",
  "timestamp": "2025-01-02T14:30:26.920Z",
  "iteration": 1,
  "input": {
    "expert_outputs": [
      { "expert": "literal", "confidence": 0.92, "conclusion": "..." },
      { "expert": "precedent", "confidence": 0.88, "conclusion": "..." }
    ],
    "query_features": {
      "intent": "validità_atto",
      "complexity": 0.68
    }
  },
  "stop_criteria_evaluation": {
    "confidence_threshold": {
      "required": 0.85,
      "actual": 0.90,
      "met": true
    },
    "consensus_threshold": {
      "required": 0.15,
      "actual": 0.04,
      "met": true
    },
    "coverage_threshold": {
      "required": 0.75,
      "actual": 0.88,
      "met": true
    },
    "max_iterations": {
      "max_allowed": 3,
      "current": 1,
      "met": true
    }
  },
  "decision": "STOP",
  "rationale": "Alta confidenza (0.90 > 0.85) + pieno consenso (divergenza 0.04 < 0.15) → iterazione non necessaria",
  "metadata": {
    "rlcf_checkpoint": "loop_controller_v1.5",
    "duration_ms": 45,
    "status": "success"
  }
}
```

##### Synthesis Trace

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "component": "synthesis",
  "timestamp": "2025-01-02T14:30:26.965Z",
  "input": {
    "expert_outputs": [
      { "expert": "literal", "conclusion": "Contratto ANNULLABILE", "confidence": 0.92, ... },
      { "expert": "precedent", "conclusion": "Contratto ANNULLABILE", "confidence": 0.88, ... }
    ],
    "convergence_analysis": {
      "divergence_score": 0.04,
      "aligned": true
    }
  },
  "synthesis_mode": "convergent",
  "synthesis_process": {
    "confidence_aggregation": {
      "formula": "weighted_average",
      "weights": {
        "literal": 0.52,
        "precedent": 0.48
      },
      "final_confidence": 0.902
    },
    "rationale_integration": {
      "key_arguments": [
        "Art. 2 CC: minorenne = < 18 anni",
        "Art. 1425 CC: contratto incapace annullabile",
        "Cass. 6234/2018: orientamento consolidato"
      ]
    },
    "consensus_boost": {
      "applied": true,
      "boost_factor": 1.04,
      "final_confidence_boosted": 0.938
    }
  },
  "output": {
    "conclusion": "Il contratto stipulato da un minorenne è ANNULLABILE (Art. 1425 CC), salvo eccezioni espresse dalla legge (Art. 322 CC)",
    "confidence": 0.938,
    "rationale": "La normativa civilistica stabilisce chiaramente che la maggiore età si raggiunge a 18 anni (Art. 2) e che gli atti compiuti da soggetti incapaci sono annullabili (Art. 1425). La giurisprudenza consolidata conferma tale orientamento (Cass. 6234/2018).",
    "sources": [
      { "type": "norm", "id": "cc_art_2", "weight": 0.35 },
      { "type": "norm", "id": "cc_art_1425", "weight": 0.35 },
      { "type": "precedent", "id": "Cass. 6234/2018", "weight": 0.30 }
    ],
    "caveats": [
      "Esistono eccezioni per atti espressamente consentiti dalla legge (es. Art. 2238 CC per contratti di lavoro del minore emancipato)"
    ]
  },
  "metadata": {
    "duration_ms": 234,
    "status": "success"
  }
}
```

#### 5.1.5 Trace Export Formats

Il sistema esporta le trace in due formati:

**1. JSON completo** (per audit programmatico):

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "query": "Un minorenne può stipulare un contratto valido?",
  "start_time": "2025-01-02T14:30:22.145Z",
  "end_time": "2025-01-02T14:30:27.199Z",
  "total_duration_ms": 5054,
  "status": "success",
  "components": [
    { ... },  // query_understanding log
    { ... },  // kg_enrichment log
    { ... },  // router log
    { ... },  // retrieval log
    { ... },  // experts log (iteration 1)
    { ... },  // loop_controller log
    { ... }   // synthesis log
  ],
  "statistics": {
    "total_llm_calls": 3,
    "total_llm_tokens": 9087,
    "total_iterations": 1,
    "total_norms_retrieved": 8,
    "total_precedents_analyzed": 1
  },
  "final_output": { ... }
}
```

**2. Markdown human-readable** (per spiegabilità utente):

```markdown
# Trace Report: trc_20250102_143022_a1b2c3

**Query**: Un minorenne può stipulare un contratto valido?
**Timestamp**: 2025-01-02 14:30:22 UTC
**Durata totale**: 5.05 secondi
**Iterazioni**: 1

---

## 1. Query Understanding

**Concetti estratti**:
- capacità_di_agire (confidence: 0.92)
- validità_contrattuale (confidence: 0.88)

**Intent classificato**: validità_atto (confidence: 0.89)
**Complessità**: 0.68 (media)

---

## 2. KG Enrichment

**Norme identificate**:
- Art. 2 CC - Maggiore età. Capacità di agire
- Art. 322 CC - Atti che il minore può compiere
- Art. 1425 CC - Annullabilità del contratto
- ... (5 norme aggiuntive)

**Query Cypher eseguite**: 2
**Tempo esecuzione**: 125 ms

---

## 3. Router Decisioni

**Esperti selezionati**: Literal Interpreter, Precedent Analyst
**Rationale**: Query di validità su norma chiara → serve interpretazione letterale + conferma giurisprudenziale

**Retrieval plan**: KG Agent (espansione relazioni) + API Agent (testi completi)
**Iterazioni previste**: 1 (alta probabilità convergenza immediata)

---

## 4. Retrieval

**KG Agent**: 8 norme recuperate (208 ms)
**API Agent**: 8 testi completi recuperati (616 ms)

---

## 5. Reasoning (Iteration 1)

### Literal Interpreter
**Conclusione**: Contratto ANNULLABILE (salvo eccezioni Art. 322)
**Confidence**: 0.92
**Fonti**: Art. 2 CC, Art. 322 CC, Art. 1425 CC

### Precedent Analyst
**Conclusione**: Contratto ANNULLABILE (orientamento consolidato)
**Confidence**: 0.88
**Fonti**: Cass. 6234/2018, Art. 1441 CC

**Convergenza**: Sì (divergenza: 0.04)

---

## 6. Loop Decision

**Decisione**: STOP
**Rationale**: Alta confidenza (0.90 > 0.85) + pieno consenso (divergenza 0.04 < 0.15)

---

## 7. Synthesis

**Modalità**: Convergent
**Conclusione finale**:
> Il contratto stipulato da un minorenne è **ANNULLABILE** (Art. 1425 CC), salvo eccezioni espresse dalla legge (Art. 322 CC).

**Confidence finale**: 0.938

**Rationale integrato**:
La normativa civilistica stabilisce chiaramente che la maggiore età si raggiunge a 18 anni (Art. 2) e che gli atti compiuti da soggetti incapaci sono annullabili (Art. 1425). La giurisprudenza consolidata conferma tale orientamento (Cass. 6234/2018).

**Caveat**:
Esistono eccezioni per atti espressamente consentiti dalla legge (es. Art. 2238 CC per contratti di lavoro del minore emancipato).

---

## Statistics

- **LLM Calls**: 3
- **Total Tokens**: 9,087
- **Norms Retrieved**: 8
- **Precedents Analyzed**: 1
- **Iterations**: 1
```

#### 5.1.6 Accountability & Audit

Il sistema di traceability garantisce:

**1. Riproducibilità**:
- Ogni trace include versioni di tutti i modelli/database
- Possibile rieseguire la query con gli stessi componenti

**2. Auditabilità**:
- Log immutabili con timestamp
- Trace ID univoco per correlazione
- Esportazione in formato standard (JSON)

**3. Spiegabilità**:
- Rationale esplicito per ogni decisione
- Fonti citate con pesi
- Export human-readable per utenti non tecnici

**4. Compliance**:
- Timestamp precisi per ogni operazione
- Tracciamento di tutti gli accessi alle API esterne
- Log delle chiamate LLM (per GDPR/trasparenza)

**Tabella Compliance Requirements**:

| Requisito | Implementazione | Standard |
|-----------|-----------------|----------|
| **Trasparenza decisionale** | Rationale esplicito in ogni componente | GDPR Art. 22 |
| **Tracciabilità fonti** | Citazioni con pesi in synthesis | ISO 25964 |
| **Auditabilità temporale** | Timestamp millisecondi + versioning | ISO 8601 |
| **Riproducibilità** | Versioning modelli/DB in metadata | IEEE 7002 |
| **Spiegabilità utente** | Export markdown human-readable | UNI 11881 |

---

### 5.2 RLCF Integration

Il **Reinforcement Learning from Community Feedback (RLCF)** è integrato trasversalmente in tutti i componenti per apprendere dai feedback della community legale (avvocati, giuristi, giudici).

#### 5.2.1 Architettura Generale RLCF

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RLCF LIFECYCLE                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────┐
│ MERL-T System  │  → Genera Output + Trace
└────────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ USER FEEDBACK COLLECTION                                             │
│ ─────────────────────────────────────────────────────────────────── │
│ Modalità:                                                            │
│ 1. Rating esplicito (1-5 stelle)                                    │
│ 2. Preferenza comparativa (A vs B)                                  │
│ 3. Correzione esplicita (testo alternativo)                         │
│ 4. Validazione componente-specifica (es. "Router scelta sbagliata") │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ REWARD SIGNAL GENERATION                                             │
│ ─────────────────────────────────────────────────────────────────── │
│ Mapping feedback → reward numerico per ogni componente:             │
│ - Router: reward su expert_selection + retrieval_plan               │
│ - Retrieval: reward su relevance norme/precedenti                   │
│ - Experts: reward su singoli argomenti                              │
│ - Synthesis: reward su conclusione finale                           │
│ - Loop: reward su stop_decision                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ TRAINING DATA GENERATION                                             │
│ ─────────────────────────────────────────────────────────────────── │
│ Format: (state, action, reward, next_state)                         │
│ Aggregato per componente + versioning                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ OFFLINE RL TRAINING                                                  │
│ ─────────────────────────────────────────────────────────────────── │
│ Algoritmi: PPO, DPO (Direct Preference Optimization)                │
│ Frequency: Weekly batch update                                      │
│ Validation: Hold-out test set + A/B testing                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ MODEL DEPLOYMENT                                                     │
│ ─────────────────────────────────────────────────────────────────── │
│ Nuova versione checkpoint → production (con A/B testing)            │
│ Versioning semantico (es. router_expert_v2.3 → v2.4)                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 RLCF Integration Points

**Tabella Componenti + Decisioni Apprendibili**:

| Componente | Decisione Apprendibile | Stato (Input) | Azione (Output) | Reward Signal |
|------------|------------------------|---------------|-----------------|---------------|
| **Router** | Expert Selection | intent, complexity, concepts, norms | selected_experts | Feedback: "esperti giusti?" (1-5) |
| **Router** | Retrieval Planning | intent, norms_enriched | agents_selected, strategy | Feedback: "norme rilevanti?" (1-5) |
| **Router** | Iteration Expectation | intent, complexity | expected_iterations | Differenza vs iterazioni reali |
| **Retrieval (KG)** | Query Optimization | concepts, norms | cypher_query_template | Feedback: "norme recuperate rilevanti?" |
| **Retrieval (Vector)** | Similarity Threshold | query_embedding, complexity | threshold_value | Feedback: "chunks rilevanti?" |
| **Experts** | Argument Emphasis | norm_text, query_context | arguments_weights | Feedback: "argomenti convincenti?" |
| **Synthesis** | Expert Weighting | expert_conclusions, confidences | final_weights | Feedback: "sintesi corretta?" (1-5) |
| **Loop** | Stop Decision | iteration, expert_state | STOP/CONTINUE | Feedback: "iterazione utile/inutile" |

#### 5.2.3 Feedback Collection Schema

**Formato Feedback**:

```json
{
  "feedback_id": "fb_20250102_150312_x9y8z7",
  "trace_id": "trc_20250102_143022_a1b2c3",
  "timestamp": "2025-01-02T15:03:12.456Z",
  "user": {
    "id": "user_123",
    "role": "avvocato",
    "expertise": ["diritto_civile", "contratti"],
    "experience_years": 12
  },
  "feedback_type": "rating_explicit",
  "overall_rating": 4,
  "component_ratings": [
    {
      "component": "router",
      "decision": "expert_selection",
      "rating": 5,
      "comment": "Esperti corretti per query di validità"
    },
    {
      "component": "synthesis",
      "decision": "final_conclusion",
      "rating": 4,
      "comment": "Conclusione corretta ma manca riferimento Art. 1441 CC per termini annullabilità"
    }
  ],
  "suggested_corrections": [
    {
      "component": "synthesis",
      "field": "caveats",
      "suggestion": "Aggiungere: 'Termine annullamento: 5 anni dalla maggiore età (Art. 1442 CC)'"
    }
  ]
}
```

**Feedback Types**:

1. **Rating esplicito** (1-5 stelle):
   ```json
   {
     "feedback_type": "rating_explicit",
     "overall_rating": 4,
     "component_ratings": [...]
   }
   ```

2. **Preferenza comparativa** (A vs B):
   ```json
   {
     "feedback_type": "preference_comparison",
     "trace_a": "trc_..._a",
     "trace_b": "trc_..._b",
     "preferred": "trace_a",
     "reason": "Sintesi più chiara e completa"
   }
   ```

3. **Correzione esplicita**:
   ```json
   {
     "feedback_type": "explicit_correction",
     "component": "synthesis",
     "field": "conclusion",
     "original": "Contratto ANNULLABILE",
     "corrected": "Contratto ANNULLABILE entro 5 anni dalla maggiore età (Art. 1442)"
   }
   ```

4. **Validazione binaria**:
   ```json
   {
     "feedback_type": "binary_validation",
     "component": "router",
     "decision": "expert_selection",
     "valid": true
   }
   ```

#### 5.2.4 Reward Signal Design

**Mapping Feedback → Reward**:

```python
# NOTA: Questo è pseudo-codice concettuale, NON implementazione Python

reward_mapping = {
  "rating_explicit": {
    5: +1.0,   # Eccellente
    4: +0.5,   # Buono
    3: 0.0,    # Neutro
    2: -0.5,   # Insufficiente
    1: -1.0    # Pessimo
  },
  "preference_comparison": {
    "preferred": +1.0,
    "not_preferred": -1.0
  },
  "binary_validation": {
    "valid": +1.0,
    "invalid": -1.0
  }
}
```

**Reward Shaping per Componente**:

| Componente | Reward Formula | Esempio |
|------------|----------------|---------|
| **Router (Expert Selection)** | `r = rating_expert_selection * 1.0` | rating=5 → r=+1.0 |
| **Router (Retrieval Plan)** | `r = (relevance_norms / total_norms) * 2.0 - 1.0` | 8/10 norme rilevanti → r=+0.6 |
| **Experts (Arguments)** | `r = rating_arguments * weight_expert` | rating=4, weight=0.5 → r=+0.25 |
| **Synthesis** | `r = rating_conclusion * 1.5` | rating=4 → r=+0.75 |
| **Loop (Stop Decision)** | `r = -1 se iterazione inutile, +1 se utile` | iterazione inutile → r=-1.0 |

**Reward Aggregation**:

Per ogni trace con feedback, si genera un reward per ogni decisione:

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "feedback_id": "fb_20250102_150312_x9y8z7",
  "rewards": [
    {
      "component": "router",
      "decision": "expert_selection",
      "state": { "intent": "validità_atto", "complexity": 0.68, ... },
      "action": { "selected_experts": ["literal", "precedent"] },
      "reward": +1.0,
      "next_state": { ... }
    },
    {
      "component": "synthesis",
      "decision": "final_conclusion",
      "state": { "expert_conclusions": [...], ... },
      "action": { "conclusion": "...", "confidence": 0.938 },
      "reward": +0.67,
      "next_state": null
    }
  ]
}
```

#### 5.2.5 Training Data Format

**Per ogni componente**, si raccolgono esempi nel formato `(s, a, r, s')`:

**Esempio: Router Expert Selection**

```json
{
  "component": "router_expert_selection",
  "training_examples": [
    {
      "state": {
        "intent": "validità_atto",
        "complexity": 0.68,
        "concepts": ["capacità_di_agire", "validità_contrattuale"],
        "norms_enriched": ["cc_art_2", "cc_art_322", "cc_art_1425"]
      },
      "action": {
        "selected_experts": ["literal", "precedent"]
      },
      "reward": +1.0,
      "next_state": {
        "expert_outputs": [
          { "expert": "literal", "confidence": 0.92 },
          { "expert": "precedent", "confidence": 0.88 }
        ]
      },
      "metadata": {
        "trace_id": "trc_20250102_143022_a1b2c3",
        "feedback_id": "fb_20250102_150312_x9y8z7",
        "user_expertise": ["diritto_civile"],
        "timestamp": "2025-01-02T15:03:12.456Z"
      }
    },
    {
      "state": {
        "intent": "bilanciamento_diritti",
        "complexity": 0.88,
        "concepts": ["libertà_espressione", "diritto_privacy"],
        "norms_enriched": ["cost_art_21", "cost_art_15", ...]
      },
      "action": {
        "selected_experts": ["principles", "systemic", "precedent"]
      },
      "reward": +0.5,
      "next_state": { ... },
      "metadata": { ... }
    }
  ]
}
```

**Esempio: Loop Stop Decision**

```json
{
  "component": "loop_stop_decision",
  "training_examples": [
    {
      "state": {
        "iteration": 1,
        "intent": "validità_atto",
        "complexity": 0.68,
        "expert_state": {
          "confidence_avg": 0.90,
          "consensus": true,
          "divergence_score": 0.04
        }
      },
      "action": {
        "decision": "STOP"
      },
      "reward": +1.0,
      "rationale_feedback": "Decisione corretta, iterazione ulteriore sarebbe stata inutile",
      "metadata": { ... }
    },
    {
      "state": {
        "iteration": 1,
        "intent": "bilanciamento_diritti",
        "complexity": 0.88,
        "expert_state": {
          "confidence_avg": 0.72,
          "consensus": false,
          "divergence_score": 0.35
        }
      },
      "action": {
        "decision": "STOP"
      },
      "reward": -1.0,
      "rationale_feedback": "Errore: serviva iterazione 2 per approfondire divergenza",
      "metadata": { ... }
    }
  ]
}
```

#### 5.2.6 Training Loop Architecture

**Fasi del Training**:

```
┌────────────────────────────────────────────────────────────────┐
│ FASE 1: DATA COLLECTION (continuo)                            │
│ ──────────────────────────────────────────────────────────────│
│ - Sistema in produzione genera trace                          │
│ - Utenti forniscono feedback                                  │
│ - Feedback → reward → training examples                       │
│ - Storage: PostgreSQL (tabella rlcf_training_data)            │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│ FASE 2: DATA AGGREGATION (weekly)                             │
│ ──────────────────────────────────────────────────────────────│
│ - Raggruppa esempi per componente                             │
│ - Filtra outliers (es. feedback da utenti non esperti)        │
│ - Bilancia dataset (es. oversampling intent rari)             │
│ - Split: 80% train, 10% validation, 10% test                  │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│ FASE 3: OFFLINE RL TRAINING (weekly batch)                    │
│ ──────────────────────────────────────────────────────────────│
│ Algoritmi:                                                     │
│ - PPO (Proximal Policy Optimization)                          │
│ - DPO (Direct Preference Optimization) per comparazioni       │
│                                                                │
│ Per ogni componente:                                           │
│ - Inizializza da checkpoint precedente                        │
│ - Train per N epochs con early stopping                       │
│ - Valida su validation set                                    │
│ - Salva nuovo checkpoint se miglioramento > threshold         │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│ FASE 4: VALIDATION & A/B TESTING (prima del deploy)           │
│ ──────────────────────────────────────────────────────────────│
│ - Test su hold-out test set                                   │
│ - Metriche: accuracy, precision, recall su decisioni          │
│ - A/B test in produzione: 10% traffic su nuovo modello        │
│ - Monitoraggio metriche per 48h                               │
└────────────┬───────────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│ FASE 5: DEPLOYMENT (se A/B test positivo)                     │
│ ──────────────────────────────────────────────────────────────│
│ - Rollout graduale: 10% → 50% → 100% traffic                  │
│ - Versioning: router_expert_v2.3 → v2.4                       │
│ - Rollback automatico se metriche peggiorano                  │
└────────────────────────────────────────────────────────────────┘
```

**Training Hyperparameters (esempio Router)**:

```json
{
  "component": "router_expert_selection",
  "algorithm": "PPO",
  "hyperparameters": {
    "learning_rate": 3e-4,
    "batch_size": 64,
    "epochs": 10,
    "gamma": 0.99,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01
  },
  "early_stopping": {
    "patience": 3,
    "min_delta": 0.001
  },
  "validation_metrics": [
    "expert_selection_accuracy",
    "avg_reward",
    "user_satisfaction_score"
  ]
}
```

#### 5.2.7 RLCF Checkpoints & Versioning

Ogni componente ha un **checkpoint versionato** con semantica:

**Versioning Schema**: `{component}_{decision}_v{major}.{minor}`

**Esempio Lifecycle**:

```
router_expert_v1.0  (bootstrap: regole hard-coded)
       ↓
router_expert_v2.0  (primo training RLCF, 500 feedback)
       ↓
router_expert_v2.1  (bugfix: gestione intent rari)
       ↓
router_expert_v2.2  (training batch settimana 2, 1200 feedback)
       ↓
router_expert_v2.3  (training batch settimana 3, 1800 feedback)
       ↓
router_expert_v2.4  (training batch settimana 4, 2500 feedback) ← CURRENT
```

**Metadata Checkpoint**:

```json
{
  "checkpoint_id": "router_expert_v2.4",
  "component": "router",
  "decision": "expert_selection",
  "version": "2.4",
  "training_date": "2025-01-02",
  "training_examples_count": 2500,
  "validation_metrics": {
    "accuracy": 0.87,
    "avg_reward": 0.68,
    "user_satisfaction": 4.2
  },
  "model_architecture": "transformer_classifier",
  "model_parameters": 125000000,
  "training_time_hours": 3.5,
  "baseline_checkpoint": "router_expert_v2.3",
  "improvement_vs_baseline": +0.03
}
```

#### 5.2.8 Feedback Loop Closure

**Ciclo Completo**:

1. **Utente esegue query** → sistema genera trace
2. **Utente fornisce feedback** → reward signal generato
3. **Training data accumulato** → batch settimanale
4. **Offline training** → nuovo checkpoint
5. **A/B testing** → validazione in produzione
6. **Deployment graduale** → nuovo modello in produzione
7. **Monitoring** → metriche in tempo reale
8. **Utente vede miglioramenti** → fornisce nuovo feedback (loop)

**Tabella Metriche Monitorate**:

| Metrica | Descrizione | Target | Attuale (esempio) |
|---------|-------------|--------|-------------------|
| **User Satisfaction** | Rating medio 1-5 | > 4.0 | 4.2 |
| **Router Accuracy** | % expert selection corretti | > 85% | 87% |
| **Iteration Efficiency** | % query risolte in 1 iter | > 70% | 73% |
| **Synthesis Quality** | Rating sintesi finale | > 4.0 | 4.3 |
| **Feedback Rate** | % utenti che danno feedback | > 30% | 35% |
| **Training Frequency** | Batch training ogni N giorni | 7 | 7 |

---

### 5.3 Privacy & GDPR Compliance

#### 5.3.1 Anonimizzazione Feedback

I feedback sono **anonimizzati** prima del training:

**Dati Rimossi**:
- User ID → sostituito con hash pseudonimo
- Query personali → generalizzate (es. "Mario Rossi" → "[NOME]")
- Dati sensibili → rimossi (GDPR Art. 9)

**Dati Conservati**:
- User role (avvocato, giudice, giurista)
- User expertise (settori diritto)
- User experience (anni esperienza)
- Timestamp (aggregato a livello settimanale)

#### 5.3.2 Retention Policy

**Trace Logs**:
- **Conservazione**: 90 giorni (audit compliance)
- **Archiviazione**: dopo 90 giorni → storage cold (per ricerche future)
- **Cancellazione**: su richiesta utente (GDPR Art. 17)

**Training Data**:
- **Conservazione**: permanente (anonimizzato)
- **Revisione**: semestrale per rimozione bias

---

### 5.4 Adaptive Components with Safety Constraints

L'integrazione RLCF rende il sistema **adattivo**, ma serve **bilanciamento** tra:
- ✅ **Adattività**: Apprendere da feedback per migliorare decisioni
- ✅ **Tracciabilità**: Spiegare ogni decisione per audit/compliance
- ✅ **Safety**: Vincoli hard non violabili (gerarchia fonti, budget, limiti)

#### 5.4.1 Architettura Ibrida: Rule-Based Fallback + RLCF Enhancement

**Pattern generale** per componenti adattivi:

```
┌──────────────────────────────────────────────────────────────┐
│           HYBRID DECISION PATTERN                            │
└──────────────────────────────────────────────────────────────┘

Input: (intent, complexity, context)
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Rule-Based Fallback (deterministico)                │
│ ──────────────────────────────────────────────────────────  │
│ base_decision = RULE_TABLE[intent][complexity]              │
│                                                              │
│ Example:                                                     │
│   intent="validità_atto", complexity=0.68                   │
│   → base_experts = ["literal", "precedent"]                 │
│   → base_confidence_threshold = 0.85                        │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: RLCF Enhancement (se disponibile)                   │
│ ──────────────────────────────────────────────────────────  │
│ IF rlcf_model.is_trained() AND rlcf_model.confidence > 0.75:│
│   ml_decision = rlcf_model.predict(state)                   │
│                                                              │
│   Example:                                                   │
│   ml_experts = ["literal", "precedent", "systemic"]         │
│   ml_confidence = 0.89                                       │
│                                                              │
│   → RLCF suggests adding "systemic" expert                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Safety Validation (vincoli hard)                    │
│ ──────────────────────────────────────────────────────────  │
│ validate_constraints(ml_decision):                          │
│   - Gerarchia fonti rispettata?                             │
│   - Budget non superato? (max LLM calls, max iterations)    │
│   - Threshold entro range sicuri? [min, max]                │
│   - Esperti obbligatori inclusi? (es. Principles se cost.)  │
│                                                              │
│ IF valid:                                                    │
│   final_decision = ml_decision                               │
│   trace("Using RLCF: {ml} (base was {base})")               │
│ ELSE:                                                        │
│   final_decision = base_decision                             │
│   trace("RLCF violated constraints, fallback to rule-based")│
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
                  final_decision
```

**Vantaggi**:
- ✅ **Cold-start safety**: Sistema funziona anche senza RLCF (fallback deterministico)
- ✅ **Graceful degradation**: Se RLCF fallisce/timeout → fallback automatico
- ✅ **Spiegabilità**: Trace log mostra decisione base + RLCF adjustment + rationale
- ✅ **Safety-first**: Vincoli hard non violabili da ML

#### 5.4.2 Componenti Adattivi con Vincoli

**Tabella Riepilogativa**:

| Componente | Livello Adattività | Vincoli Hard (Non Violabili) | Trace Log Requirement |
|------------|-------------------|------------------------------|----------------------|
| **Router Expert Selection** | BOUNDED | Min 1 expert, Max 4 experts. Se `bilanciamento_diritti` → Principles OBBLIGATORIO | "Base rule: [L,P], RLCF: [L,P,S], Rationale: +systemic for complexity 0.68" |
| **Stop Criteria Thresholds** | BOUNDED | Confidence ∈ [0.65, 0.95], Divergence ∈ [0.05, 0.35], Max_iter ≤ 5 (hard limit) | "ML threshold=0.82, actual=0.85 → STOP (within safe range [0.70-0.90])" |
| **Synthesis Weighting** | BOUNDED | Min weight per expert=0.10, Σ weights=1.0, Gerarchia fonti rispettata (Costituzione > Legge) | "Base weights=[0.33,0.33,0.34], RLCF=[0.38,0.27,0.35], Constraints: ✓" |
| **Retrieval Agent Selection** | BOUNDED | Se norme mappate → API Agent OBBLIGATORIO. Max 10 API calls/query. Budget: $0.10/query | "ML suggests [KG,API], skipping Vector (conf=0.91). Cost estimate: $0.04" |
| **Query Understanding Concepts** | FULL (con validazione) | Concetti estratti devono esistere in KG o essere validati da expert review | "LLM extracted ['diritto_oblio'], KG validation: NOT FOUND → expert review" |
| **Trace ID Generation** | NONE | UUID v7 deterministico (timestamp-sortable), formato fisso `trc_{ts}_{uuid}` | N/A (deterministico, no ML) |
| **Audit Log Schema** | NONE | Schema JSON fisso (versionato), ISO 8601 timestamps, backward compatible | N/A (compliance requirement) |
| **Gerarchia Fonti Normative** | NONE | Kelseniana: Costituzione > Legge Cost. > Legge Ord. > Regolamento (IMMUTABILE) | N/A (vincolo costituzionale) |

**Legenda Livelli**:
- **NONE**: Completamente deterministico, zero ML
- **BOUNDED**: RLCF entro vincoli hard (range min-max, constraint validation)
- **FULL**: RLCF senza vincoli numerici fissi (ma con validazione semantica)

#### 5.4.3 Esempio Dettagliato: Router Expert Selection con Safety

**Scenario**: Query `"È legittimo licenziamento per critica su social media?"`

**Query Understanding Output**:
```json
{
  "intent": "bilanciamento_diritti",
  "complexity": 0.88,
  "concepts": ["licenziamento", "libertà_espressione", "dovere_fedeltà"]
}
```

**STEP 1 - Rule-Based Fallback**:
```json
{
  "rule_table_lookup": {
    "intent": "bilanciamento_diritti",
    "complexity": "ANY",
    "base_experts": ["principles", "systemic", "precedent"],
    "rationale": "Bilanciamento diritti → serve Principles (test proporzionalità) + Systemic (ratio) + Precedent (orientamento)"
  }
}
```

**STEP 2 - RLCF Enhancement**:
```json
{
  "rlcf_model": "router_expert_v2.4",
  "rlcf_input": {
    "intent": "bilanciamento_diritti",
    "complexity": 0.88,
    "concepts": ["licenziamento", "libertà_espressione", "dovere_fedeltà"]
  },
  "rlcf_output": {
    "predicted_experts": ["principles", "systemic", "precedent", "literal"],
    "confidence": 0.84,
    "rationale_ml": "Alta complessità (0.88) + conflitto normativo → aggiungi Literal per interpretazione Art. 2105 CC (obbligo fedeltà)"
  }
}
```

**STEP 3 - Safety Validation**:
```json
{
  "constraints_check": {
    "min_experts": {"required": 1, "actual": 4, "pass": true},
    "max_experts": {"required": 4, "actual": 4, "pass": true},
    "bilanciamento_requires_principles": {"required": true, "actual": true, "pass": true},
    "gerarchia_fonti_respected": true,
    "budget_check": {"max_llm_calls": 8, "estimated": 4, "pass": true}
  },
  "validation_result": "PASS",
  "final_decision": {
    "selected_experts": ["literal", "systemic", "principles", "precedent"],
    "source": "RLCF (validated)",
    "fallback_used": false
  }
}
```

**Trace Log (Export Markdown)**:
```
### Router Decision: Expert Selection

**Intent**: bilanciamento_diritti
**Complexity**: 0.88 (alta)

**Base Rule (fallback)**: ["principles", "systemic", "precedent"]
**Rationale base**: Bilanciamento diritti richiede test proporzionalità (Principles) + ratio legis (Systemic) + orientamento giurisprudenziale (Precedent)

**RLCF Enhancement (v2.4)**:
**ML Suggestion**: ["principles", "systemic", "precedent", "literal"]
**ML Confidence**: 84%
**ML Rationale**: Alta complessità (0.88) + conflitto normativo (libertà espressione vs obbligo fedeltà) → aggiungi Literal per interpretazione precisa Art. 2105 CC (obbligo fedeltà lavoratore)

**Safety Validation**:
✅ Constraints rispettati:
  - Min 1 expert, Max 4 experts (actual: 4) ✓
  - Bilanciamento diritti → Principles obbligatorio ✓
  - Budget LLM: 4 calls (max 8) ✓
  - Gerarchia fonti: rispettata ✓

**FINAL DECISION**: ["literal", "systemic", "principles", "precedent"]
**Source**: RLCF-enhanced (validated)
**Fallback used**: NO
```

**Scenario Alternativo - RLCF Violazione Vincoli**:

Se RLCF avesse suggerito `["systemic", "precedent"]` (omettendo Principles):

```
**Safety Validation**:
❌ Constraints VIOLATI:
  - Bilanciamento diritti richiede Principles obbligatorio ✗

**FINAL DECISION**: ["principles", "systemic", "precedent"]
**Source**: Rule-based fallback
**Fallback used**: YES (RLCF violated mandatory constraint)
**Warning**: RLCF model v2.4 omitted mandatory Principles expert for bilanciamento_diritti. Using fallback.
```

#### 5.4.4 Esempio Dettagliato: Stop Criteria con Bounded RLCF

**Scenario**: Iteration 2 di query complessa su bilanciamento diritti.

**Expert State** (dopo iteration 2):
```json
{
  "iteration": 2,
  "expert_outputs": [
    {"expert": "literal", "confidence": 0.76, "conclusion": "Licenziamento LEGITTIMO"},
    {"expert": "systemic", "confidence": 0.73, "conclusion": "Licenziamento DIPENDE da gravità"},
    {"expert": "principles", "confidence": 0.71, "conclusion": "Licenziamento ILLEGITTIMO se critica moderata"},
    {"expert": "precedent", "confidence": 0.82, "conclusion": "Licenziamento DIPENDE (caso per caso)"}
  ],
  "convergence_analysis": {
    "confidence_avg": 0.755,
    "divergence_score": 0.24,
    "aligned": false
  }
}
```

**STEP 1 - Rule-Based Fallback Thresholds**:
```json
{
  "generic_thresholds": {
    "confidence_min": 0.80,
    "divergence_max": 0.20,
    "max_iterations": 3
  },
  "intent_specific_thresholds": {
    "intent": "bilanciamento_diritti",
    "confidence_min": 0.75,
    "divergence_max": 0.30,
    "max_iterations": 4
  },
  "rule_decision": {
    "checks": {
      "confidence_avg >= 0.75": {"actual": 0.755, "pass": true},
      "divergence_score <= 0.30": {"actual": 0.24, "pass": true},
      "iteration < 4": {"actual": 2, "pass": true}
    },
    "decision": "STOP",
    "rationale": "Intent-specific thresholds met (bilanciamento_diritti allows divergence up to 0.30)"
  }
}
```

**STEP 2 - RLCF ML-Based Threshold**:
```json
{
  "rlcf_model": "loop_controller_v1.5",
  "rlcf_input": {
    "intent": "bilanciamento_diritti",
    "complexity": 0.88,
    "iteration": 2,
    "expert_state": {
      "confidence_avg": 0.755,
      "divergence_score": 0.24,
      "conclusions_variety": 3
    }
  },
  "rlcf_output": {
    "decision": "CONTINUE",
    "confidence": 0.79,
    "learned_threshold": {
      "confidence_min": 0.78,
      "divergence_max": 0.22
    },
    "rationale_ml": "Divergenza 0.24 ancora alta per bilanciamento diritti. Iterazione 3 potrebbe convergere meglio (historical pattern: 68% convergenza su iter 3 per questo intent)"
  }
}
```

**STEP 3 - Safety Validation (Bounded Range)**:
```json
{
  "safe_ranges": {
    "confidence_min": {"min": 0.65, "max": 0.95},
    "divergence_max": {"min": 0.05, "max": 0.35},
    "max_iterations_hard_limit": 5
  },
  "rlcf_validation": {
    "learned_confidence_threshold": {
      "value": 0.78,
      "within_range": true,
      "range": [0.65, 0.95]
    },
    "learned_divergence_threshold": {
      "value": 0.22,
      "within_range": true,
      "range": [0.05, 0.35]
    },
    "iteration_check": {
      "current": 2,
      "hard_limit": 5,
      "pass": true
    }
  },
  "validation_result": "PASS",
  "final_decision": {
    "decision": "CONTINUE",
    "source": "RLCF (validated)",
    "fallback_used": false
  }
}
```

**Trace Log**:
```
### Loop Controller Decision (Iteration 2)

**Expert State**:
- Confidence avg: 0.755
- Divergence: 0.24 (partially aligned)
- Iteration: 2/5

**Rule-Based Thresholds (bilanciamento_diritti)**:
- Confidence min: 0.75 (✓ actual: 0.755)
- Divergence max: 0.30 (✓ actual: 0.24)
- Rule Decision: STOP (thresholds met)

**RLCF ML-Based Decision (v1.5)**:
- ML Decision: CONTINUE
- ML Confidence: 79%
- ML Learned Thresholds:
  - Confidence min: 0.78 (stricter than rule-based)
  - Divergence max: 0.22 (stricter than rule-based)
- ML Rationale: Divergenza 0.24 ancora sopra learned threshold 0.22. Pattern storico mostra 68% convergenza su iterazione 3 per bilanciamento_diritti → raccomando CONTINUE.

**Safety Validation (Bounded RLCF)**:
✅ ML thresholds within safe ranges:
  - Confidence 0.78 ∈ [0.65, 0.95] ✓
  - Divergence 0.22 ∈ [0.05, 0.35] ✓
  - Iteration 2 < hard limit 5 ✓

**FINAL DECISION**: CONTINUE to Iteration 3
**Source**: RLCF-enhanced (validated)
**Fallback used**: NO
**Estimated benefit**: +12% probability of convergence on iter 3 (based on historical data)
```

**Scenario Violazione - Hard Limit**:

Se iteration=4 e RLCF suggerisce CONTINUE:

```
**Safety Validation**:
⚠️ Approaching hard limit:
  - Current iteration: 4
  - Hard limit: 5
  - RLCF suggests: CONTINUE

**Budget Check**:
- Current LLM tokens: 42,300
- Estimated iter 5 tokens: 52,800
- Daily budget: 500,000 ✓ (still within budget)

**FINAL DECISION**: CONTINUE to Iteration 5 (LAST iteration allowed)
**Source**: RLCF (validated with warning)
**Warning**: Next iteration is LAST (hard limit). Will FORCE STOP after iter 5 regardless of convergence.
```

Se iteration=5 (hard limit raggiunto):

```
**Safety Validation**:
❌ Hard limit REACHED:
  - Current iteration: 5
  - Hard limit: 5
  - RLCF suggests: CONTINUE (ignored)

**FINAL DECISION**: FORCE STOP
**Source**: Hard limit override (safety constraint)
**Fallback used**: YES (hard limit non-negotiable)
**Warning**: Max iterations reached. Synthesis will proceed with current expert state (divergence: 0.19).
```

#### 5.4.5 Metriche Tracciabilità RLCF

Per ogni decisione RLCF-enhanced, il sistema traccia:

| Metrica | Descrizione | Esempio Valore |
|---------|-------------|----------------|
| `rlcf_model_version` | Versione checkpoint RLCF | `router_expert_v2.4` |
| `rlcf_confidence` | Confidence del modello ML | 0.84 |
| `base_decision` | Decisione fallback rule-based | `["literal", "precedent"]` |
| `ml_decision` | Decisione suggerita da RLCF | `["literal", "precedent", "systemic"]` |
| `constraints_validated` | Vincoli rispettati? | `true` |
| `constraints_violated` | Lista vincoli violati (se any) | `[]` (vuoto se pass) |
| `final_decision_source` | Fonte decisione finale | `"RLCF"` o `"fallback"` |
| `fallback_reason` | Perché fallback usato (se applicabile) | `"RLCF violated mandatory Principles constraint"` |
| `estimated_improvement` | Miglioramento stimato vs base | `"+12% user satisfaction (historical)"` |

**Export Trace JSON** (esempio completo):

```json
{
  "trace_id": "trc_20250102_150412_xyz",
  "component": "router",
  "decision_type": "expert_selection",
  "timestamp": "2025-01-02T15:04:12.456Z",
  "rlcf_decision": {
    "model_version": "router_expert_v2.4",
    "model_confidence": 0.84,
    "base_decision": {
      "source": "rule_table",
      "experts": ["principles", "systemic", "precedent"],
      "rationale": "Bilanciamento diritti → test proporzionalità + ratio + giurisprudenza"
    },
    "ml_decision": {
      "source": "rlcf_model",
      "experts": ["literal", "systemic", "principles", "precedent"],
      "rationale_ml": "Alta complessità + conflitto normativo → aggiungi Literal per Art. 2105 CC",
      "confidence": 0.84
    },
    "safety_validation": {
      "constraints": [
        {"name": "min_experts", "required": 1, "actual": 4, "pass": true},
        {"name": "max_experts", "required": 4, "actual": 4, "pass": true},
        {"name": "bilanciamento_requires_principles", "pass": true},
        {"name": "budget_llm_calls", "max": 8, "estimated": 4, "pass": true}
      ],
      "all_passed": true
    },
    "final_decision": {
      "experts": ["literal", "systemic", "principles", "precedent"],
      "source": "rlcf_validated",
      "fallback_used": false,
      "estimated_improvement": "+8% accuracy vs base (based on 234 similar queries)"
    }
  }
}
```

#### 5.4.6 Componenti NON Adattivi (Compliance)

Alcuni componenti **devono rimanere deterministici** per compliance/safety:

**1. Trace ID Generation** (GDPR Art. 5, ISO 8601):
```
Format: trc_{timestamp_utc}_{uuid_v7}
Example: trc_20250102_150412_01936f8a-b2c4-7890-abcd-123456789abc

Rationale:
- UUID v7 è timestamp-sortable (facilita audit cronologico)
- Formato fisso garantisce parsing automatico
- GDPR: utente può richiedere cancellazione via Trace ID → formato immutabile
```

**2. Audit Log Schema** (ISO 25964, IEEE 7002):
```json
{
  "schema_version": "v1.0",
  "trace_id": "...",
  "component": "enum[query_understanding, kg_enrichment, router, ...]",
  "timestamp": "ISO 8601 required",
  "input": {},
  "output": {},
  "metadata": {
    "duration_ms": "int",
    "status": "enum[success, error]"
  }
}
```

**Rationale**:
- Backward compatibility con audit tools esistenti
- Standard internazionali (ISO/IEEE) richiedono schema fisso
- Versionamento semantico per evoluzioni future (v1.0 → v2.0 con migration plan)

**3. Gerarchia Fonti Normative** (Art. 134 Cost.):
```
IMMUTABILE:
1. Costituzione (rigida, Art. 138 procedura aggravata)
2. Leggi costituzionali
3. Trattati UE direttamente applicabili (Art. 117 Cost.)
4. Leggi ordinarie (Codici, Leggi speciali)
5. Decreti Legislativi (Art. 76-77 Cost.)
6. Regolamenti
7. Giurisprudenza (interpretativa, non vincolante salvo Cass. SS.UU.)
```

**Rationale**:
- Principio costituzionale fondamentale (gerarchia Kelseniana)
- RLCF NON PUÒ apprendere a violare Costituzione
- Esempio VIETATO: preferire giurisprudenza a norma costituzionale

**Hard Constraint in Synthesis**:
```python
# Pseudo-codice constraint validation
def validate_source_hierarchy(synthesis_weights, sources):
    for source in sources:
        if source.type == "costituzione":
            assert synthesis_weights[source] >= MIN_CONSTITUTIONAL_WEIGHT
        if source.hierarchy < other_source.hierarchy:
            assert synthesis_weights[source] >= synthesis_weights[other_source]
    return True
```

---

## 5.5 Riepilogo Parte 5

Questa sezione ha documentato:

### Traceability System
- ✅ Architettura trace lifecycle
- ✅ Trace ID schema e propagazione
- ✅ Trace log structure per ogni componente
- ✅ Export formats (JSON + Markdown)
- ✅ Accountability & Audit compliance

### RLCF Integration
- ✅ RLCF lifecycle generale
- ✅ Integration points per componente (Router, Retrieval, Experts, Synthesis, Loop)
- ✅ Feedback collection schema (4 tipi)
- ✅ Reward signal design e mapping
- ✅ Training data format (s, a, r, s')
- ✅ Training loop architecture (5 fasi)
- ✅ Checkpoint versioning & deployment
- ✅ Feedback loop closure
- ✅ Privacy & GDPR compliance

### Adaptive Components with Safety Constraints (NUOVO)
- ✅ **Architettura ibrida**: Rule-based fallback + RLCF enhancement
- ✅ **Tabella componenti adattivi**: Livelli NONE/BOUNDED/FULL
- ✅ **Vincoli hard non violabili**: Gerarchia fonti, budget, limiti iteration
- ✅ **Esempi trace dettagliati**: Router Expert Selection, Stop Criteria con bounded RLCF
- ✅ **Spiegabilità garantita**: Log esplicito base decision → RLCF adjustment → validation
- ✅ **Safety-first**: Graceful degradation se RLCF fallisce/viola vincoli
- ✅ **Componenti non adattivi**: Trace ID, Audit Log, Gerarchia Fonti (compliance)

**Bilanciamento raggiunto**:
- ✅ Adattività (RLCF migliora decisioni)
- ✅ Tracciabilità (ogni decisione spiegata)
- ✅ Safety (vincoli costituzionali/budget non violabili)

**Prossimi step**:
- Parte 6: LangGraph Orchestration (architettura StateGraph, nodi, edges)
- Parte 7: Examples + Bootstrap Strategy (esempi end-to-end, strategia bootstrap)

---

---

## 6. LangGraph Orchestration

Questa sezione documenta l'orchestrazione dell'intero sistema MERL-T tramite **LangGraph**, il framework di LangChain per costruire applicazioni multi-agente con stato.

LangGraph permette di:
- Definire un **StateGraph** con nodi (componenti) e edges (transizioni)
- Gestire lo **stato condiviso** tra componenti
- Implementare **routing condizionale** basato su decisioni dinamiche
- Supportare **cicli iterativi** (loop Experts → Synthesis → Loop Controller → Experts)
- **Persistere lo stato** su database per resume di sessioni interrotte

---

### 6.1 Architettura StateGraph Generale

```
┌────────────────────────────────────────────────────────────────────────┐
│                      MERL-T LANGGRAPH STATEGRAPH                       │
└────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │    START     │
                              └──────┬───────┘
                                     │
                                     ▼
                         ┌─────────────────────────┐
                         │  Query Understanding    │  (node)
                         └──────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │   KG Enrichment         │  (node)
                         └──────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │   Router                │  (node)
                         └──────────┬──────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │   Retrieval Agents      │  (node, RunnableParallel)
                         │   - KG Agent            │
                         │   - API Agent           │
                         │   - Vector Agent        │
                         └──────────┬──────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────────┐
                    │      Reasoning Experts            │  (node, RunnableParallel)
                    │      - Literal Interpreter        │
                    │      - Systemic-Teleological      │
                    │      - Principles Balancer        │
                    │      - Precedent Analyst          │
                    └───────────────┬───────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────────┐
                         │   Loop Controller       │  (conditional node)
                         └──────────┬──────────────┘
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                   decision="CONTINUE"     decision="STOP"
                        │                       │
                        ▼                       ▼
          ┌──────────────────────┐   ┌─────────────────────────┐
          │ LOOP BACK to Experts │   │      Synthesis          │  (node)
          │  (iteration += 1)    │   └──────────┬──────────────┘
          └──────────────────────┘              │
                                                 ▼
                                      ┌─────────────────────────┐
                                      │     Output Formatter    │  (node)
                                      └──────────┬──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │     END      │
                                          └──────────────┘
```

**Caratteristiche Chiave**:
1. **Nodi sequenziali** fino al Router
2. **Nodi paralleli** per Retrieval e Experts (RunnableParallel)
3. **Nodo condizionale** per Loop Controller (decide CONTINUE vs STOP)
4. **Ciclo iterativo** tra Experts e Loop Controller
5. **State persistito** su database (PostgreSQL) per resume

---

### 6.2 State Schema

Lo **state** è condiviso tra tutti i nodi e contiene tutte le informazioni della pipeline.

#### 6.2.1 State Structure

```json
{
  "trace_id": "trc_20250102_143022_a1b2c3",
  "session_id": "sess_user123_20250102",

  "query": {
    "raw_query": "Un minorenne può stipulare un contratto valido?",
    "timestamp": "2025-01-02T14:30:22.145Z"
  },

  "query_understanding": {
    "concepts": [
      { "name": "capacità_di_agire", "confidence": 0.92 },
      { "name": "validità_contrattuale", "confidence": 0.88 }
    ],
    "intent": "validità_atto",
    "intent_confidence": 0.89,
    "complexity": 0.68,
    "entities": [
      { "text": "minorenne", "label": "LEGAL_SUBJECT", "span": [3, 12] }
    ]
  },

  "kg_enrichment": {
    "norms": [
      { "id": "cc_art_2", "title": "...", "hierarchy": "codice" },
      { "id": "cc_art_322", "title": "...", "hierarchy": "codice" }
    ],
    "relations": [
      { "from": "cc_art_2", "to": "cc_art_322", "type": "REGULATES" }
    ],
    "total_norms_found": 8
  },

  "router": {
    "expert_selection": {
      "selected": ["literal", "precedent"],
      "rationale": "..."
    },
    "retrieval_plan": {
      "agents_selected": ["kg_agent", "api_agent"],
      "strategies": {
        "kg": "expand_related_norms",
        "api": "full_text_retrieval"
      }
    },
    "iteration_expectation": {
      "expected_iterations": 1,
      "expected_stop_reason": "alta_confidenza"
    }
  },

  "retrieval": {
    "kg_results": {
      "norms": [...],
      "count": 8
    },
    "api_results": {
      "texts": [...],
      "count": 8
    },
    "vector_results": null
  },

  "iterations": [
    {
      "iteration_number": 1,
      "expert_outputs": [
        {
          "expert": "literal",
          "conclusion": "Contratto ANNULLABILE",
          "confidence": 0.92,
          "reasoning": {...},
          "sources": [...]
        },
        {
          "expert": "precedent",
          "conclusion": "Contratto ANNULLABILE",
          "confidence": 0.88,
          "reasoning": {...},
          "sources": [...]
        }
      ],
      "convergence_analysis": {
        "divergence_score": 0.04,
        "confidence_avg": 0.90,
        "aligned": true
      },
      "loop_decision": {
        "decision": "STOP",
        "rationale": "Alta confidenza + pieno consenso"
      }
    }
  ],

  "synthesis": {
    "mode": "convergent",
    "conclusion": "Il contratto stipulato da un minorenne è ANNULLABILE (Art. 1425 CC)...",
    "confidence": 0.938,
    "rationale": "...",
    "sources": [...],
    "caveats": [...]
  },

  "output": {
    "formatted_answer": "...",
    "trace_export_json": {...},
    "trace_export_markdown": "..."
  },

  "metadata": {
    "total_duration_ms": 5054,
    "total_llm_tokens": 9087,
    "total_iterations": 1,
    "status": "success"
  }
}
```

#### 6.2.2 State Updates

Ogni nodo riceve lo **state corrente** come input e restituisce un **state update** (merge parziale).

**Esempio: Query Understanding Node**

```
Input State:
{
  "trace_id": "trc_...",
  "query": { "raw_query": "...", ... }
}

Output (State Update):
{
  "query_understanding": {
    "concepts": [...],
    "intent": "validità_atto",
    "complexity": 0.68,
    ...
  }
}

Merged State:
{
  "trace_id": "trc_...",
  "query": { ... },
  "query_understanding": { ... }  ← ADDED
}
```

LangGraph **mergia automaticamente** gli update nello state condiviso.

---

### 6.3 Nodes Definition

Ogni nodo è una funzione che:
1. Riceve `state: State` come input
2. Esegue la logica del componente
3. Restituisce un `dict` con update allo state

#### 6.3.1 Node: Query Understanding

**Funzione** (pseudo-codice):

```
def query_understanding_node(state: State) -> dict:
    """
    Estrae concetti, intent, complessità dalla query.
    """
    raw_query = state["query"]["raw_query"]

    # Esegue NER, concept mapping, intent classification
    # (vedi query-understanding.md per dettagli ML)
    concepts = extract_concepts(raw_query)
    intent, intent_conf = classify_intent(raw_query, concepts)
    complexity = compute_complexity(raw_query, concepts)
    entities = extract_entities(raw_query)

    return {
        "query_understanding": {
            "concepts": concepts,
            "intent": intent,
            "intent_confidence": intent_conf,
            "complexity": complexity,
            "entities": entities
        }
    }
```

**Input**: `state["query"]`
**Output**: update con `query_understanding`

#### 6.3.2 Node: KG Enrichment

```
def kg_enrichment_node(state: State) -> dict:
    """
    Consulta Neo4j per mappare concetti → norme.
    """
    concepts = [c["name"] for c in state["query_understanding"]["concepts"]]

    # Esegue Cypher queries (vedi Part 1)
    norms = query_kg_concept_to_norm(concepts)
    relations = query_kg_expand_relations(norms)

    return {
        "kg_enrichment": {
            "norms": norms,
            "relations": relations,
            "total_norms_found": len(norms)
        }
    }
```

**Input**: `state["query_understanding"]["concepts"]`
**Output**: update con `kg_enrichment`

#### 6.3.3 Node: Router

```
def router_node(state: State) -> dict:
    """
    LLM-based router che decide expert selection + retrieval plan.
    """
    intent = state["query_understanding"]["intent"]
    complexity = state["query_understanding"]["complexity"]
    norms_enriched = state["kg_enrichment"]["norms"]

    # LLM call con prompt strutturato (vedi Part 2)
    router_output = llm_router_decision(
        intent=intent,
        complexity=complexity,
        norms=norms_enriched
    )

    return {
        "router": {
            "expert_selection": router_output["expert_selection"],
            "retrieval_plan": router_output["retrieval_plan"],
            "iteration_expectation": router_output["iteration_expectation"]
        }
    }
```

**Input**: `state["query_understanding"]`, `state["kg_enrichment"]`
**Output**: update con `router`

**Nota**: Il Router usa RLCF checkpoint `router_expert_v2.4` per decisioni apprese.

#### 6.3.4 Node: Retrieval Agents (PARALLEL)

```
def retrieval_agents_node(state: State) -> dict:
    """
    Esegue 3 retrieval agents in PARALLELO (RunnableParallel).
    """
    retrieval_plan = state["router"]["retrieval_plan"]
    agents_selected = retrieval_plan["agents_selected"]

    # RunnableParallel: esegue tutti gli agent contemporaneamente
    results = {}

    if "kg_agent" in agents_selected:
        results["kg_results"] = kg_agent.invoke(
            norms=state["kg_enrichment"]["norms"],
            strategy=retrieval_plan["strategies"]["kg"]
        )

    if "api_agent" in agents_selected:
        results["api_results"] = api_agent.invoke(
            norms=state["kg_enrichment"]["norms"],
            strategy=retrieval_plan["strategies"]["api"]
        )

    if "vector_agent" in agents_selected:
        results["vector_results"] = vector_agent.invoke(
            query=state["query"]["raw_query"],
            strategy=retrieval_plan["strategies"]["vector"]
        )

    return {
        "retrieval": results
    }
```

**Input**: `state["router"]["retrieval_plan"]`, `state["kg_enrichment"]["norms"]`
**Output**: update con `retrieval`

**Implementazione Parallelismo**:

```
# LangGraph pseudo-codice
retrieval_agents_parallel = RunnableParallel(
    kg_agent=kg_agent_runnable,
    api_agent=api_agent_runnable,
    vector_agent=vector_agent_runnable
)
```

**Timing**:
- Sequenziale: KG (208ms) + API (616ms) + Vector (340ms) = **1164ms**
- Parallelo: max(208, 616, 340) = **616ms** (~50% risparmio)

#### 6.3.5 Node: Reasoning Experts (PARALLEL)

```
def reasoning_experts_node(state: State) -> dict:
    """
    Esegue 2-4 Experts in PARALLELO (RunnableParallel).
    """
    experts_selected = state["router"]["expert_selection"]["selected"]
    current_iteration = len(state.get("iterations", [])) + 1

    # Prepara input comune per tutti gli Expert
    expert_input = {
        "query": state["query"]["raw_query"],
        "norms": state["kg_enrichment"]["norms"],
        "texts": state["retrieval"]["api_results"]["texts"],
        "chunks": state["retrieval"].get("vector_results", {}).get("chunks", [])
    }

    # RunnableParallel: esegue tutti gli Expert contemporaneamente
    expert_outputs = []

    if "literal" in experts_selected:
        expert_outputs.append(
            literal_expert.invoke(expert_input)
        )

    if "systemic" in experts_selected:
        expert_outputs.append(
            systemic_expert.invoke(expert_input)
        )

    if "principles" in experts_selected:
        expert_outputs.append(
            principles_expert.invoke(expert_input)
        )

    if "precedent" in experts_selected:
        expert_outputs.append(
            precedent_expert.invoke(expert_input)
        )

    # Analisi convergenza
    convergence = analyze_convergence(expert_outputs)

    # Aggiungi iterazione allo state
    iteration_data = {
        "iteration_number": current_iteration,
        "expert_outputs": expert_outputs,
        "convergence_analysis": convergence
    }

    # Append to iterations list
    iterations = state.get("iterations", [])
    iterations.append(iteration_data)

    return {
        "iterations": iterations
    }
```

**Input**: `state["router"]["expert_selection"]`, `state["retrieval"]`
**Output**: update con `iterations` (append nuova iterazione)

**Implementazione Parallelismo**:

```
# LangGraph pseudo-codice
experts_parallel = RunnableParallel(
    literal=literal_expert_runnable,
    systemic=systemic_expert_runnable,
    principles=principles_expert_runnable,
    precedent=precedent_expert_runnable
)
```

**Timing**:
- Sequenziale: 1581ms + 2369ms + 1920ms + 2156ms = **8026ms**
- Parallelo: max(1581, 2369, 1920, 2156) = **2369ms** (~70% risparmio)

#### 6.3.6 Node: Loop Controller (CONDITIONAL)

```
def loop_controller_node(state: State) -> dict:
    """
    Decide se continuare iterazione o fermarsi (ML-based, RLCF-learned).
    """
    current_iteration = len(state["iterations"])
    last_iteration = state["iterations"][-1]

    intent = state["query_understanding"]["intent"]
    complexity = state["query_understanding"]["complexity"]

    expert_state = {
        "confidence_avg": last_iteration["convergence_analysis"]["confidence_avg"],
        "consensus": last_iteration["convergence_analysis"]["aligned"],
        "divergence_score": last_iteration["convergence_analysis"]["divergence_score"]
    }

    # ML-based decision (RLCF checkpoint loop_controller_v1.5)
    decision = ml_stop_criteria_model.predict(
        features={
            "intent": intent,
            "complexity": complexity,
            "iteration": current_iteration,
            "expert_state": expert_state
        }
    )

    # Update last iteration con decisione
    state["iterations"][-1]["loop_decision"] = {
        "decision": decision,  # "STOP" or "CONTINUE"
        "rationale": generate_rationale(decision, expert_state)
    }

    return {
        "iterations": state["iterations"]
    }
```

**Input**: `state["iterations"][-1]`, `state["query_understanding"]`
**Output**: update con `iterations[-1]["loop_decision"]`

**Decision Output**: `"STOP"` or `"CONTINUE"`

Questa decisione è usata per **conditional routing** (vedi 6.4.3).

#### 6.3.7 Node: Synthesis

```
def synthesis_node(state: State) -> dict:
    """
    Sintetizza conclusioni da tutte le iterazioni.
    """
    all_expert_outputs = []
    for iteration in state["iterations"]:
        all_expert_outputs.extend(iteration["expert_outputs"])

    # Determina mode: convergent vs divergent
    last_convergence = state["iterations"][-1]["convergence_analysis"]
    mode = "convergent" if last_convergence["aligned"] else "divergent"

    # Synthesis logic (vedi Part 4)
    if mode == "convergent":
        synthesis_output = convergent_synthesis(all_expert_outputs)
    else:
        synthesis_output = divergent_synthesis_majority_minority(all_expert_outputs)

    return {
        "synthesis": synthesis_output
    }
```

**Input**: `state["iterations"]`
**Output**: update con `synthesis`

#### 6.3.8 Node: Output Formatter

```
def output_formatter_node(state: State) -> dict:
    """
    Formatta output finale + esporta trace.
    """
    synthesis = state["synthesis"]

    # Formatta risposta human-readable
    formatted_answer = format_answer(
        conclusion=synthesis["conclusion"],
        confidence=synthesis["confidence"],
        rationale=synthesis["rationale"],
        sources=synthesis["sources"],
        caveats=synthesis.get("caveats", [])
    )

    # Esporta trace (JSON + Markdown)
    trace_json = export_trace_json(state)
    trace_md = export_trace_markdown(state)

    return {
        "output": {
            "formatted_answer": formatted_answer,
            "trace_export_json": trace_json,
            "trace_export_markdown": trace_md
        },
        "metadata": {
            "total_duration_ms": compute_duration(state),
            "total_llm_tokens": compute_tokens(state),
            "total_iterations": len(state["iterations"]),
            "status": "success"
        }
    }
```

**Input**: `state["synthesis"]`, intero `state`
**Output**: update con `output`, `metadata`

---

### 6.4 Edges & Routing

Gli **edges** connettono i nodi e definiscono il flusso di esecuzione.

#### 6.4.1 Sequential Edges (diretti)

```
START → query_understanding → kg_enrichment → router → retrieval → experts
```

Questi edges sono **deterministici** e sempre eseguiti in sequenza.

**LangGraph pseudo-codice**:

```
graph.add_edge(START, "query_understanding")
graph.add_edge("query_understanding", "kg_enrichment")
graph.add_edge("kg_enrichment", "router")
graph.add_edge("router", "retrieval")
graph.add_edge("retrieval", "experts")
```

#### 6.4.2 Parallel Edges (RunnableParallel)

Per **Retrieval Agents** e **Reasoning Experts**, gli edges sono interni al nodo (gestiti da RunnableParallel).

```
# Retrieval Node internamente esegue:
┌─────────────┐
│  retrieval  │
└──────┬──────┘
       │
    ┌──┴──┐
    │ PAR │  (RunnableParallel)
    └──┬──┘
       ├────→ kg_agent
       ├────→ api_agent
       └────→ vector_agent
```

Dal punto di vista del grafo esterno, è un singolo nodo.

#### 6.4.3 Conditional Edge (Loop Controller)

Dopo `loop_controller`, l'edge è **condizionale** basato su `decision`.

```
experts → loop_controller → [CONDITION]
                               │
                    ┌──────────┴──────────┐
                    │                     │
              decision="CONTINUE"   decision="STOP"
                    │                     │
                    ▼                     ▼
                experts            synthesis
              (nuovo loop)
```

**LangGraph pseudo-codice**:

```
def should_continue_loop(state: State) -> str:
    """
    Conditional routing function.
    """
    last_decision = state["iterations"][-1]["loop_decision"]["decision"]

    if last_decision == "CONTINUE":
        return "experts"  # Loop back
    else:
        return "synthesis"  # Procedi a sintesi

# Aggiungi conditional edge
graph.add_conditional_edges(
    "loop_controller",
    should_continue_loop,
    {
        "experts": "experts",      # Se CONTINUE → torna a experts
        "synthesis": "synthesis"   # Se STOP → vai a synthesis
    }
)
```

**Nota**: Quando si loopa a `experts`, lo state mantiene tutte le iterazioni precedenti in `state["iterations"]`.

#### 6.4.4 Final Edges

```
loop_controller → synthesis → output_formatter → END
```

**LangGraph pseudo-codice**:

```
graph.add_edge("synthesis", "output_formatter")
graph.add_edge("output_formatter", END)
```

---

### 6.5 Complete StateGraph Definition

**LangGraph pseudo-codice completo**:

```
from langgraph.graph import StateGraph, END

# 1. Definisci State schema
class MerlTState(TypedDict):
    trace_id: str
    session_id: str
    query: dict
    query_understanding: dict
    kg_enrichment: dict
    router: dict
    retrieval: dict
    iterations: list[dict]
    synthesis: dict
    output: dict
    metadata: dict

# 2. Crea StateGraph
workflow = StateGraph(MerlTState)

# 3. Aggiungi nodi
workflow.add_node("query_understanding", query_understanding_node)
workflow.add_node("kg_enrichment", kg_enrichment_node)
workflow.add_node("router", router_node)
workflow.add_node("retrieval", retrieval_agents_node)
workflow.add_node("experts", reasoning_experts_node)
workflow.add_node("loop_controller", loop_controller_node)
workflow.add_node("synthesis", synthesis_node)
workflow.add_node("output_formatter", output_formatter_node)

# 4. Aggiungi edges sequenziali
workflow.set_entry_point("query_understanding")
workflow.add_edge("query_understanding", "kg_enrichment")
workflow.add_edge("kg_enrichment", "router")
workflow.add_edge("router", "retrieval")
workflow.add_edge("retrieval", "experts")
workflow.add_edge("experts", "loop_controller")

# 5. Aggiungi conditional edge per loop
def should_continue_loop(state: MerlTState) -> str:
    last_decision = state["iterations"][-1]["loop_decision"]["decision"]
    return "experts" if last_decision == "CONTINUE" else "synthesis"

workflow.add_conditional_edges(
    "loop_controller",
    should_continue_loop,
    {
        "experts": "experts",
        "synthesis": "synthesis"
    }
)

# 6. Aggiungi edges finali
workflow.add_edge("synthesis", "output_formatter")
workflow.add_edge("output_formatter", END)

# 7. Compila il grafo
app = workflow.compile(
    checkpointer=PostgreSQLCheckpointer(conn_string="..."),  # State persistence
    debug=True
)
```

---

### 6.6 State Persistence & Resume

LangGraph supporta **checkpointing** dello state su database per permettere:
- **Resume** di query interrotte (es. timeout, crash)
- **Audit** dello stato intermedio
- **Debugging** con visualizzazione step-by-step

#### 6.6.1 PostgreSQL Checkpointer

**Schema Database**:

```sql
CREATE TABLE langgraph_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    state JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_session (session_id),
    INDEX idx_trace (trace_id)
);
```

**Checkpoint Workflow**:

```
Esecuzione Normale:
  query_understanding → [CHECKPOINT 1] → kg_enrichment → [CHECKPOINT 2] → ...

Interruzione a kg_enrichment:
  [CRASH] → state perso

Con Checkpointer:
  Resume da CHECKPOINT 1 → riprendi da kg_enrichment
```

#### 6.6.2 Resume API

```
# Esempio: resume da session interrotta
app.invoke(
    input=None,  # Non serve input, usa checkpoint
    config={
        "configurable": {
            "thread_id": "sess_user123_20250102",  # session_id
            "checkpoint_id": "cp_trc_20250102_143022_a1b2c3_node_kg_enrichment"
        }
    }
)
```

Il grafo **riprende esattamente dal checkpoint** salvato.

#### 6.6.3 Retention Policy

**Checkpoints**:
- **Conservazione**: 7 giorni (per resume rapido)
- **Archiviazione**: dopo 7 giorni → storage cold (S3)
- **Cancellazione**: su richiesta utente (GDPR)

**Trace Logs** (vedi Part 5):
- **Conservazione**: 90 giorni

---

### 6.7 Error Handling & Retry Logic

Ogni nodo implementa **retry con backoff esponenziale** per gestire errori transienti.

#### 6.7.1 Retry Strategy

**Configurazione**:

```json
{
  "retry_policy": {
    "max_attempts": 3,
    "backoff_type": "exponential",
    "initial_delay_ms": 1000,
    "max_delay_ms": 8000,
    "multiplier": 2.0,
    "jitter": true
  }
}
```

**Backoff Schedule**:

| Attempt | Delay | Cumulative Time |
|---------|-------|-----------------|
| 1 (fail) | 0ms | 0ms |
| 2 (retry) | 1000ms + jitter | 1000ms |
| 3 (retry) | 2000ms + jitter | 3000ms |
| 4 (retry) | 4000ms + jitter | 7000ms |
| FAIL | - | - |

**Jitter**: Random delay ±20% per evitare thundering herd.

#### 6.7.2 Retryable Errors

**Categorie di Errori**:

| Errore | Retryable? | Strategia |
|--------|-----------|-----------|
| **API Normattiva timeout** | ✅ Sì | Retry con backoff (3 tentativi) |
| **Neo4j connection error** | ✅ Sì | Retry con backoff (3 tentativi) |
| **LLM rate limit (429)** | ✅ Sì | Retry con backoff (3 tentativi) |
| **LLM timeout** | ✅ Sì | Retry con timeout aumentato |
| **Weaviate/Qdrant connection** | ✅ Sì | Retry con backoff (3 tentativi) |
| **Input validation error** | ❌ No | Fail-fast, errore utente |
| **LLM malformed output** | ⚠️ Condizionale | Retry 1 volta con prompt fix, poi fail |
| **Out of memory** | ❌ No | Fail-fast, log alert |

#### 6.7.3 Fallback Strategies

Se tutti i retry falliscono, il sistema applica **fallback**:

**Tabella Fallback**:

| Componente | Errore | Fallback |
|------------|--------|----------|
| **API Agent** | Normattiva non disponibile | Usa solo VectorDB per testi simili |
| **Vector Agent** | Weaviate down | Usa solo KG + API (nessuna ricerca semantica) |
| **KG Agent** | Neo4j down | ⚠️ Errore critico, fallback a retrieval blind |
| **Expert (singolo)** | LLM timeout | Procedi con altri Expert, marca come "skipped" |
| **Router** | LLM malformed output | Usa default rule-based router (fallback deterministico) |

**Esempio: API Agent Fallback**

```
def retrieval_agents_node(state: State) -> dict:
    results = {}

    try:
        results["api_results"] = api_agent.invoke(..., retry=3)
    except MaxRetriesExceededError:
        logger.warning("API Agent failed, fallback to VectorDB only")
        # Fallback: usa VectorDB con query più ampia
        results["vector_results"] = vector_agent.invoke(
            query=state["query"]["raw_query"],
            strategy="expanded_search",
            top_k=30  # Aumenta risultati per compensare
        )
        results["api_results"] = None  # Marca come failed

    return {"retrieval": results}
```

#### 6.7.4 Error Propagation

Alcuni errori sono **critici** e fermano l'intera pipeline:

**Errori Critici**:
1. **Query Understanding fallisce** → impossibile procedere (no intent/concepts)
2. **KG Enrichment fallisce completamente** → Router cieco (no norme)
3. **Tutti gli Experts falliscono** → nessun reasoning disponibile
4. **Synthesis fallisce** → impossibile generare risposta

**Handling**:

```
def handle_critical_error(node_name: str, error: Exception, state: State):
    """
    Gestisce errori critici salvando trace parziale e restituendo errore utente.
    """
    # Salva trace parziale per debugging
    partial_trace = export_trace_json(state)
    save_failed_trace(trace_id=state["trace_id"], partial_trace=partial_trace)

    # Restituisci messaggio utente
    return {
        "output": {
            "formatted_answer": f"Siamo spiacenti, si è verificato un errore nel componente {node_name}. Il team tecnico è stato notificato.",
            "error_details": {
                "node": node_name,
                "error_type": type(error).__name__,
                "trace_id": state["trace_id"]
            }
        },
        "metadata": {
            "status": "error",
            "error_node": node_name
        }
    }
```

---

### 6.8 Monitoring & Observability

#### 6.8.1 Metrics per Node

Ogni nodo emette metriche in tempo reale:

**Metriche Standard**:

| Metrica | Descrizione | Esempio |
|---------|-------------|---------|
| `node.duration_ms` | Tempo esecuzione nodo | `query_understanding.duration_ms = 245` |
| `node.success_rate` | % esecuzioni senza errori | `router.success_rate = 0.987` |
| `node.retry_count` | Numero medio retry | `api_agent.retry_count = 0.12` |
| `node.llm_tokens` | Token LLM consumati | `router.llm_tokens = 1632` |
| `node.cache_hit_rate` | % cache hit (se applicabile) | `kg_enrichment.cache_hit_rate = 0.45` |

**Metriche Specifiche**:

| Nodo | Metrica Custom | Esempio |
|------|----------------|---------|
| **Router** | `expert_selection_accuracy` | 0.87 (vs feedback RLCF) |
| **Retrieval** | `norms_relevance_score` | 0.82 (% norme rilevanti) |
| **Experts** | `convergence_rate` | 0.73 (% query convergenti iter 1) |
| **Loop** | `avg_iterations` | 1.3 (media iterazioni per query) |
| **Synthesis** | `user_satisfaction` | 4.2 (rating medio 1-5) |

#### 6.8.2 Distributed Tracing

Integrazione con **OpenTelemetry** per tracing distribuito:

```
Query Request
│
├─ SPAN: query_understanding (245ms)
│   ├─ SPAN: spacy_ner (78ms)
│   ├─ SPAN: intent_classifier (102ms)
│   └─ SPAN: complexity_scorer (65ms)
│
├─ SPAN: kg_enrichment (125ms)
│   ├─ SPAN: neo4j_query_1 (56ms)
│   └─ SPAN: neo4j_query_2 (46ms)
│
├─ SPAN: router (1340ms)
│   └─ SPAN: llm_call_gpt4o (1298ms)
│
├─ SPAN: retrieval (620ms)
│   ├─ SPAN: kg_agent (208ms) ── PARALLEL
│   ├─ SPAN: api_agent (616ms) ── PARALLEL
│   └─ SPAN: vector_agent (340ms) ── PARALLEL
│
└─ ...
```

**Export**: Prometheus + Grafana dashboard.

#### 6.8.3 Alerting

**Alerts Configurati**:

| Alert | Condizione | Azione |
|-------|-----------|--------|
| **High Error Rate** | `node.success_rate < 0.95` per > 5 min | Pagerduty → team SRE |
| **Slow Response** | `p95_latency > 10s` per > 10 min | Slack alert → team ML |
| **LLM Budget** | `daily_tokens > 80% budget` | Email → team finance |
| **RLCF Drift** | `router_accuracy < 0.80` per > 1 day | Slack alert → team ML (retrain?) |

---

### 6.9 Performance Optimization

#### 6.9.1 Caching Strategy

**Cache Layers**:

1. **Query Understanding Cache** (Redis, TTL=24h):
   - Key: `hash(raw_query)`
   - Value: `{concepts, intent, complexity}`
   - Hit rate target: > 40%

2. **KG Enrichment Cache** (Redis, TTL=1h):
   - Key: `hash(concepts)`
   - Value: `{norms, relations}`
   - Hit rate target: > 50%

3. **Retrieval Cache** (Redis, TTL=1h):
   - Key: `hash(norm_ids + strategy)`
   - Value: `{texts, chunks}`
   - Hit rate target: > 30%

**Cache Invalidation**:
- **Manuale**: Quando database aggiornato (norme nuove)
- **TTL**: Automatic expiration dopo 1-24h

#### 6.9.2 Batching

Per query multiple simultanee, batch processing:

```
# Invece di 100 LLM calls sequenziali
for query in queries:
    router_decision(query)

# Batch di 10 alla volta
for batch in chunks(queries, batch_size=10):
    llm_batch_call(batch)  # Singola API call
```

**Speedup**: ~5x per batch size=10.

#### 6.9.3 Model Optimization

**LLM Optimization**:
- Router: usa `gpt-4o-mini` invece di `gpt-4o` (3x più veloce, -80% costo)
- Experts: usa `gpt-4o` solo per query complesse (complexity > 0.75)
- Synthesis: usa `gpt-4o-mini` per convergent mode, `gpt-4o` per divergent

**Table: Model Selection**:

| Componente | Complessità | Modello | Cost/1M tokens |
|------------|-------------|---------|----------------|
| Router | Sempre | `gpt-4o-mini` | $0.15 |
| Experts | < 0.75 | `gpt-4o-mini` | $0.15 |
| Experts | ≥ 0.75 | `gpt-4o` | $5.00 |
| Synthesis (convergent) | Sempre | `gpt-4o-mini` | $0.15 |
| Synthesis (divergent) | Sempre | `gpt-4o` | $5.00 |

**Risparmio Stimato**: 60% costi LLM senza perdita qualità.

---

### 6.10 Deployment Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          DEPLOYMENT STACK                          │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   API Gateway   │  (FastAPI, rate limiting, auth)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Application                        │
│  ──────────────────────────────────────────────────────────────│
│  - StateGraph compiled app                                      │
│  - Retry logic + error handling                                 │
│  - Checkpointer (PostgreSQL)                                    │
│  - Observability (OpenTelemetry)                                │
└──────────────┬──────────────────────────────────────────────────┘
               │
   ┌───────────┼───────────────┬──────────────┬─────────────┐
   │           │               │              │             │
   ▼           ▼               ▼              ▼             ▼
┌────────┐ ┌──────┐ ┌───────────────┐ ┌──────────┐ ┌──────────┐
│ Neo4j  │ │Redis │ │ PostgreSQL    │ │ Weaviate │ │ LLM APIs │
│  (KG)  │ │(cache│ │ (checkpoints) │ │ (vectors)│ │ (OpenAI) │
└────────┘ └──────┘ └───────────────┘ └──────────┘ └──────────┘
```

**Containerization**:

```yaml
# docker-compose.yml
services:
  merl-t-app:
    image: merl-t:latest
    replicas: 3
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_URI=redis://redis:6379
      - POSTGRES_URI=postgresql://postgres:5432/merl_t
      - WEAVIATE_URI=http://weaviate:8080
    depends_on:
      - neo4j
      - redis
      - postgres
      - weaviate

  neo4j:
    image: neo4j:5.15
    volumes:
      - neo4j_data:/data

  redis:
    image: redis:7-alpine

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data

  weaviate:
    image: semitechnologies/weaviate:1.24
```

**Scaling**:
- **Horizontal**: 3+ replicas app container (load balanced)
- **Vertical**: Neo4j/Weaviate su istanze dedicate (high memory)

---

## 6.11 Riepilogo Parte 6

Questa sezione ha documentato:

### LangGraph Orchestration
- ✅ Architettura StateGraph completa (diagramma con nodi ed edges)
- ✅ State schema dettagliato (JSON structure)
- ✅ Definizione di tutti i nodi (8 nodi con pseudo-codice)
- ✅ Edges sequenziali, paralleli, condizionali
- ✅ Routing condizionale per loop iterativo
- ✅ State persistence su PostgreSQL per resume
- ✅ Error handling con retry + backoff esponenziale
- ✅ Fallback strategies per componenti falliti
- ✅ Monitoring & observability (metriche, tracing, alerting)
- ✅ Performance optimization (caching, batching, model selection)
- ✅ Deployment architecture (Docker, scaling)

**Decisioni Architetturali** (da user input):
- ✅ **State Persistence**: PostgreSQL checkpointer
- ✅ **Error Handling**: Retry con backoff esponenziale (3 tentativi)
- ✅ **Parallelization**: RunnableParallel per Retrieval e Experts (~50-70% speedup)

**Prossimo step**:
- Parte 7: Examples + Bootstrap Strategy (esempi end-to-end completi, strategia bootstrap da generic a fine-tuned a RLCF)

---

---

## 7. Examples + Bootstrap Strategy

Questa sezione finale presenta:
1. **Esempi End-to-End completi** che mostrano il sistema in azione su query di complessità crescente
2. **Bootstrap Strategy** per l'avvio del sistema (da zero a RLCF-optimized)
3. **Conclusioni** sull'architettura MERL-T

---

### 7.1 Examples End-to-End

Presentiamo 6 esempi che coprono:
- **Complessità**: bassa → media → alta
- **Intent**: validità_atto, interpretazione_norma, bilanciamento_diritti, lacune_ordinamento
- **Iterazioni**: 1 iterazione (convergenza immediata), 2 iterazioni, 3 iterazioni
- **Modalità Synthesis**: convergente vs divergente (majority+minority)

---

#### 7.1.1 Esempio 1: Query Semplice (Validità Atto)

**Query**: *"Un minorenne può stipulare un contratto valido?"*

**Caratteristiche**:
- Intent: `validità_atto`
- Complessità: `0.68` (media-bassa)
- Iterazioni attese: 1 (convergenza immediata)
- Esperti selezionati: Literal, Precedent

---

##### Trace Completa

**1. Query Understanding**
```json
{
  "concepts": [
    { "name": "capacità_di_agire", "confidence": 0.92 },
    { "name": "validità_contrattuale", "confidence": 0.88 }
  ],
  "intent": "validità_atto",
  "complexity": 0.68,
  "entities": [
    { "text": "minorenne", "label": "LEGAL_SUBJECT" }
  ]
}
```

**2. KG Enrichment**
```json
{
  "norms": [
    { "id": "cc_art_2", "title": "Maggiore età. Capacità di agire" },
    { "id": "cc_art_322", "title": "Atti che il minore può compiere" },
    { "id": "cc_art_1425", "title": "Incapacità delle parti" },
    { "id": "cc_art_1441", "title": "Annullamento del contratto" }
  ],
  "total_norms_found": 8
}
```

**3. Router**
```json
{
  "expert_selection": {
    "selected": ["literal", "precedent"],
    "rationale": "Query di validità su norma chiara → interpretazione letterale + conferma giurisprudenziale"
  },
  "retrieval_plan": {
    "agents_selected": ["kg_agent", "api_agent"],
    "strategies": {
      "kg": "expand_related_norms",
      "api": "full_text_retrieval"
    }
  },
  "iteration_expectation": {
    "expected_iterations": 1
  }
}
```

**4. Retrieval**
- KG Agent: 8 norme + relazioni
- API Agent: 8 testi completi da Normattiva

**5. Reasoning (Iteration 1)**

**Literal Interpreter**:
```json
{
  "expert": "literal",
  "conclusion": "Contratto ANNULLABILE (salvo eccezioni Art. 322)",
  "confidence": 0.92,
  "reasoning": {
    "sillogismo": [
      "MAGGIORE: Il contratto stipulato da incapace è annullabile (Art. 1425)",
      "MINORE: Soggetto è minorenne (< 18 anni, Art. 2)",
      "CONCLUSIONE: Contratto ANNULLABILE salvo eccezioni espresse"
    ]
  },
  "sources": [
    { "norm": "cc_art_2", "weight": 0.4 },
    { "norm": "cc_art_1425", "weight": 0.4 },
    { "norm": "cc_art_322", "weight": 0.2 }
  ]
}
```

**Precedent Analyst**:
```json
{
  "expert": "precedent",
  "conclusion": "Contratto ANNULLABILE (orientamento consolidato)",
  "confidence": 0.88,
  "reasoning": {
    "precedents_analyzed": [
      {
        "court": "Cass. Civ. Sez. I",
        "number": "6234/2018",
        "massima": "Contratto minore annullabile su istanza rappresentante o minore dopo maggiore età",
        "orientation": "consolidata"
      }
    ]
  },
  "sources": [
    { "precedent": "Cass. 6234/2018", "weight": 0.6 },
    { "norm": "cc_art_1441", "weight": 0.4 }
  ]
}
```

**Convergence Analysis**:
```json
{
  "divergence_score": 0.04,
  "confidence_avg": 0.90,
  "aligned": true
}
```

**6. Loop Controller**
```json
{
  "decision": "STOP",
  "rationale": "Alta confidenza (0.90 > 0.85) + pieno consenso (divergenza 0.04 < 0.15)"
}
```

**7. Synthesis (Convergent Mode)**
```json
{
  "mode": "convergent",
  "conclusion": "Il contratto stipulato da un minorenne è ANNULLABILE (Art. 1425 CC), salvo eccezioni espresse dalla legge (Art. 322 CC).",
  "confidence": 0.938,
  "rationale": "La normativa stabilisce che la maggiore età si raggiunge a 18 anni (Art. 2) e che gli atti compiuti da incapaci sono annullabili (Art. 1425). Giurisprudenza consolidata conferma (Cass. 6234/2018).",
  "sources": [
    { "type": "norm", "id": "cc_art_2", "weight": 0.3 },
    { "type": "norm", "id": "cc_art_1425", "weight": 0.4 },
    { "type": "precedent", "id": "Cass. 6234/2018", "weight": 0.3 }
  ],
  "caveats": [
    "Eccezioni per atti espressamente consentiti (es. Art. 2238 CC per lavoro minore emancipato)",
    "Termine annullamento: 5 anni dalla maggiore età (Art. 1442 CC)"
  ]
}
```

**8. Output**
```
Il contratto stipulato da un minorenne è **ANNULLABILE** (Art. 1425 CC), salvo eccezioni espresse dalla legge (Art. 322 CC).

**Rationale**: La normativa civilistica stabilisce che la maggiore età si raggiunge a 18 anni (Art. 2 CC) e che gli atti compiuti da soggetti incapaci sono annullabili (Art. 1425 CC). La giurisprudenza consolidata conferma tale orientamento (Cass. Civ. Sez. I, n. 6234/2018).

**Attenzione**:
- Esistono eccezioni per atti espressamente consentiti dalla legge (es. Art. 2238 CC per contratti di lavoro del minore emancipato)
- Il termine per l'annullamento è di 5 anni dalla maggiore età (Art. 1442 CC)

**Fonti**: Art. 2 CC, Art. 322 CC, Art. 1425 CC, Art. 1442 CC, Cass. 6234/2018

**Confidence**: 93.8%
**Iterazioni**: 1
**Durata**: 5.1 secondi
```

---

#### 7.1.2 Esempio 2: Query Media (Interpretazione Norma)

**Query**: *"Un lavoratore licenziato per giusta causa può impugnare il licenziamento?"*

**Caratteristiche**:
- Intent: `interpretazione_norma`
- Complessità: `0.72` (media)
- Iterazioni attese: 1-2
- Esperti selezionati: Literal, Systemic, Precedent

---

##### Trace Semplificata

**Query Understanding**:
- Concepts: `licenziamento`, `giusta_causa`, `impugnazione_atto`
- Intent: `interpretazione_norma`
- Complexity: `0.72`

**KG Enrichment**:
- Norms: Art. 2119 CC, Art. 18 L. 300/1970, Art. 6 D.Lgs. 23/2015, Jobs Act

**Router**:
- Experts: `["literal", "systemic", "precedent"]`
- Retrieval: KG + API + VectorDB (per giurisprudenza)

**Reasoning (Iteration 1)**:

**Literal**:
- Conclusion: "Sì, impugnabile entro 60 giorni (Art. 6 D.Lgs. 23/2015)"
- Confidence: 0.85

**Systemic**:
- Conclusion: "Sì, impugnabile. Ratio: tutela contro arbitrarietà datore lavoro"
- Confidence: 0.79

**Precedent**:
- Conclusion: "Sì, sempre impugnabile (Cass. 24955/2019: onere prova giusta causa su datore)"
- Confidence: 0.91

**Convergence**: Aligned (divergenza 0.08)

**Loop**: STOP (alta confidenza)

**Synthesis (Convergent)**:
```
Sì, il lavoratore può SEMPRE impugnare il licenziamento per giusta causa entro 60 giorni (Art. 6 D.Lgs. 23/2015).

**Rationale**: L'ordinamento garantisce il diritto di difesa anche contro licenziamenti motivati da giusta causa. Spetta al datore di lavoro provare la sussistenza della giusta causa (Cass. 24955/2019). La ratio sistemica è tutelare il lavoratore contro possibili arbitrarietà.

**Procedura**:
1. Impugnazione scritta entro 60 giorni dalla comunicazione (Art. 6)
2. Onere della prova su datore di lavoro
3. Tutela reintegratoria o indennitaria a seconda gravità vizio

**Fonti**: Art. 2119 CC, Art. 18 L. 300/1970, Art. 6 D.Lgs. 23/2015, Cass. 24955/2019

**Confidence**: 91.2%
**Iterazioni**: 1
```

---

#### 7.1.3 Esempio 3: Query Complessa con Iterazioni (Bilanciamento Diritti)

**Query**: *"È legittimo il licenziamento di un dipendente che pubblica critiche all'azienda sui social media?"*

**Caratteristiche**:
- Intent: `bilanciamento_diritti`
- Complessità: `0.88` (alta)
- Iterazioni attese: 2-3
- Esperti selezionati: Literal, Systemic, Principles, Precedent (tutti 4)

---

##### Trace Semplificata

**Query Understanding**:
- Concepts: `licenziamento`, `libertà_espressione`, `dovere_fedeltà`, `social_media`
- Intent: `bilanciamento_diritti`
- Complexity: `0.88`

**KG Enrichment**:
- Norms: Art. 21 Cost. (libertà espressione), Art. 2105 CC (obbligo fedeltà), Art. 2119 CC (giusta causa)

**Router**:
- Experts: `["literal", "systemic", "principles", "precedent"]` (TUTTI E 4)
- Retrieval: KG + API + VectorDB

---

##### Iteration 1

**Literal**:
- Conclusion: "LEGITTIMO se viola Art. 2105 CC (obbligo fedeltà)"
- Confidence: 0.68
- Argomento: Interpretazione letterale Art. 2105 include riservatezza

**Systemic**:
- Conclusion: "DIPENDE dal contenuto critica e contesto"
- Confidence: 0.65
- Argomento: Bilanciamento libertà espressione (Art. 21 Cost.) vs obbligo fedeltà

**Principles**:
- Conclusion: "ILLEGITTIMO se critica legittima esercizio Art. 21 Cost."
- Confidence: 0.71
- Argomento: Test proporzionalità → licenziamento misura eccessiva se critica non diffamatoria

**Precedent**:
- Conclusion: "DIPENDE da gravità critica (Cass. 7155/2020: lecito se moderata)"
- Confidence: 0.82
- Argomento: Giurisprudenza distingue critica legittima vs diffamazione

**Convergence**: NOT aligned (divergenza 0.35)

**Loop Decision**: CONTINUE (divergenza alta, serve approfondimento)

---

##### Iteration 2

Gli Experts ricevono output dell'iterazione 1 + richiesta di convergenza:

**Literal** (rivisto):
- Conclusion: "DIPENDE: ILLEGITTIMO se critica moderata, LEGITTIMO se diffamatoria"
- Confidence: 0.78
- Update: Riconosce distinzione tra critica legittima e diffamazione

**Systemic** (rivisto):
- Conclusion: "ILLEGITTIMO se critica moderata su fatti pubblici"
- Confidence: 0.76
- Update: Ratio sistemica tutela libertà espressione lavoratore

**Principles** (rivisto):
- Conclusion: "ILLEGITTIMO salvo critica diffamatoria o danni gravi azienda"
- Confidence: 0.79
- Update: Test proporzionalità richiede gradualità sanzioni

**Precedent** (confermato):
- Conclusion: "DIPENDE da gravità: moderata → illegittimo, diffamatoria → legittimo"
- Confidence: 0.85
- Precedenti: Cass. 7155/2020, Cass. 28602/2019

**Convergence**: Partially aligned (divergenza 0.18)

**Loop Decision**: STOP (convergenza sufficiente, divergenza < 0.20)

---

##### Synthesis (Divergent Mode - Majority + Minority)

**Majority Position** (3 esperti: Systemic, Principles, Precedent):
```json
{
  "conclusion": "Licenziamento ILLEGITTIMO se critica MODERATA e su fatti pubblici (Art. 21 Cost. prevale su Art. 2105 CC)",
  "confidence": 0.815,
  "rationale": "La libertà di espressione (Art. 21 Cost.) tutela anche critiche moderate all'azienda. Il licenziamento è proporzionato solo per critiche diffamatorie o gravemente lesive. Giurisprudenza consolidata (Cass. 7155/2020, 28602/2019) richiede bilanciamento.",
  "test_proporzionalità": {
    "idoneità": "Licenziamento idoneo a tutelare reputazione azienda",
    "necessità": "NO - sanzione conservativa (ammonimento/sospensione) meno restrittiva",
    "proporzionalità_stretta": "NO - sacrificio libertà espressione > beneficio tutela reputazione"
  }
}
```

**Minority Position** (1 esperto: Literal - inizialmente):
```json
{
  "position": "Licenziamento LEGITTIMO anche per critica moderata se pubblica",
  "expert": "literal",
  "confidence": 0.68,
  "rationale": "Interpretazione letterale Art. 2105 CC include dovere non ledere reputazione azienda, anche con critica moderata pubblica",
  "weakness": "Interpretazione restrittiva non considera bilanciamento costituzionale Art. 21"
}
```

**Synthesis Output**:
```
La legittimità del licenziamento DIPENDE dalla GRAVITÀ della critica.

**POSIZIONE MAGGIORITARIA** (Confidence: 81.5%):
Il licenziamento è **ILLEGITTIMO** se la critica è MODERATA e riguarda fatti pubblici o di rilevanza sociale.

**Rationale**:
- La libertà di espressione (Art. 21 Cost.) tutela il diritto del lavoratore a esprimere opinioni anche critiche verso l'azienda
- Il licenziamento è proporzionato SOLO per critiche diffamatorie, false, o gravemente lesive della reputazione aziendale
- Test di proporzionalità: esistono sanzioni meno restrittive (ammonimento, sospensione) → licenziamento eccessivo
- Giurisprudenza consolidata richiede bilanciamento (Cass. 7155/2020, Cass. 28602/2019)

**Criteri di Valutazione**:
1. **Contenuto**: critica su fatti vs diffamazione personale
2. **Modalità**: linguaggio moderato vs insulti/volgarità
3. **Contesto**: fatti di rilevanza pubblica vs segreti aziendali
4. **Danno**: reputazionale grave vs lieve dissenso

**POSIZIONE MINORITARIA**:
Interpretazione letteralista considera qualsiasi critica pubblica come violazione obbligo fedeltà (Art. 2105 CC), anche se moderata. Tuttavia, questa posizione non considera il bilanciamento costituzionale con Art. 21 Cost.

**Conclusione pratica**:
- Critica moderata su orari/condizioni lavoro → Licenziamento ILLEGITTIMO
- Critica diffamatoria/falsa su dirigenti → Licenziamento LEGITTIMO
- Zona grigia → valutazione caso per caso con test proporzionalità

**Fonti**: Art. 21 Cost., Art. 2105 CC, Art. 2119 CC, Cass. 7155/2020, Cass. 28602/2019

**Confidence Majority**: 81.5%
**Confidence Minority**: 68.0%
**Iterazioni**: 2
**Durata**: 12.3 secondi
```

---

#### 7.1.4 Esempio 4: Query con 3 Iterazioni (Lacuna Ordinamento)

**Query**: *"È possibile brevettare un algoritmo di intelligenza artificiale in Italia?"*

**Caratteristiche**:
- Intent: `lacune_ordinamento`
- Complessità: `0.93` (molto alta)
- Iterazioni: 3 (materia innovativa, evoluzione giurisprudenziale)
- Esperti: Literal, Systemic, Principles, Precedent

---

##### Trace Ultra-Semplificata

**Iteration 1**:
- Literal: "NO - Art. 45 CPI esclude algoritmi"
- Systemic: "DIPENDE se algoritmo ha effetto tecnico"
- Principles: "Lacuna normativa su IA, serve bilanciamento innovazione/pubblico dominio"
- Precedent: "NO secondo EPO (European Patent Office), ma evoluzione in corso"
- Convergence: LOW (divergenza 0.42)
- Decision: CONTINUE

**Iteration 2**:
- Literal (aggiornato): "NO in generale, SÌ se effetto tecnico concreto"
- Systemic: "SÌ se risolve problema tecnico (criterio EPO)"
- Principles: "Bilanciamento: brevettabilità SE innovazione + applicazione industriale"
- Precedent: "SÌ se non solo 'algoritmo in quanto tale' (EPO G 3/08)"
- Convergence: MEDIUM (divergenza 0.25)
- Decision: CONTINUE (serve precisazione criteri)

**Iteration 3**:
- Tutti gli esperti convergono su: "SÌ con CONDIZIONI STRINGENTI"
- Convergence: HIGH (divergenza 0.12)
- Decision: STOP

**Synthesis (Convergent dopo 3 iter)**:
```
È possibile brevettare un algoritmo di IA in Italia, MA con CONDIZIONI STRINGENTI.

**Requisiti cumulativi**:
1. **Effetto tecnico concreto**: l'algoritmo deve risolvere un problema tecnico specifico (non solo matematico/astratto)
2. **Applicazione industriale**: deve avere utilizzo pratico in ambito industriale
3. **Non "algoritmo in quanto tale"**: deve essere incorporato in soluzione tecnica più ampia

**Fondamento normativo**:
- Art. 45 CPI esclude "programmi per elaboratore in quanto tali"
- Ma AMMETTE brevettabilità se "contributo tecnico" (interpretazione EPO recepita in Italia)

**Esempi**:
- ✅ BREVETTABILE: Algoritmo IA per ottimizzazione motore combustione (effetto tecnico misurabile)
- ❌ NON BREVETTABILE: Algoritmo IA generico per machine learning (astratto)

**Fonti**: Art. 45-52 CPI, EPO Guidelines G-II 3.6, EPO G 3/08

**Confidence**: 88.3%
**Iterazioni**: 3
**Durata**: 18.7 secondi
```

---

#### 7.1.5 Esempio 5: Query con Divergenza Persistente

**Query**: *"Il diritto all'oblio digitale prevale sulla libertà di stampa per fatti di cronaca giudiziaria?"*

**Caratteristiche**:
- Intent: `bilanciamento_diritti`
- Complessità: `0.91`
- Iterazioni: 2
- Synthesis: **DIVERGENTE** (no convergenza possibile, posizioni legittime inconciliabili)

---

##### Trace Ultra-Semplificata

**Iteration 1**:
- Principles: "DIPENDE: diritto oblio prevale se fatto non più attualità"
- Precedent: "DIPENDE da bilanciamento caso per caso (Corte UE C-131/12)"
- Divergence: 0.28
- Decision: CONTINUE

**Iteration 2**:
- Principles: "Diritto oblio PREVALE se decorso tempo sufficiente + fatto non rilevanza pubblica"
- Precedent: "Libertà stampa PREVALE se fatto rilevanza storica o pubblico interesse persistente"
- Divergence: 0.32 (aumenta!)
- Decision: STOP (divergenza strutturale, nessuna convergenza possibile)

**Synthesis (Divergent - Minority Report)**:
```
La risposta DIPENDE dal bilanciamento caso per caso. Esistono DUE ORIENTAMENTI LEGITTIMI.

**ORIENTAMENTO A - Prevalenza Diritto Oblio** (Confidence: 76%):
Il diritto all'oblio (Art. 17 GDPR, Art. 2 Cost.) prevale se:
- Decorso tempo sufficiente da evento (>5-10 anni)
- Fatto non ha più rilevanza pubblica attuale
- Richiesta di deindicizzazione (non cancellazione fonte)

**ORIENTAMENTO B - Prevalenza Libertà Stampa** (Confidence: 79%):
La libertà di stampa/informazione (Art. 21 Cost.) prevale se:
- Fatto ha rilevanza storica o pubblico interesse persistente
- Cronaca giudiziaria su fatti gravi (corruzione, mafia, crimini gravi)
- Trattasi di personaggio pubblico

**Criterio Dirimimento**:
La giurisprudenza richiede **bilanciamento caso per caso** considerando:
1. Tempo trascorso
2. Gravità fatti
3. Ruolo pubblico soggetto
4. Attualità interesse pubblico
5. Modalità trattamento dati (deindicizzazione vs cancellazione)

**Non esiste una regola assoluta**. Ogni caso richiede valutazione specifica.

**Fonti**: Art. 17 GDPR, Art. 21 Cost., Art. 2 Cost., Corte UE C-131/12 (Google Spain), Cass. 5525/2012

**Orientamento A Confidence**: 76%
**Orientamento B Confidence**: 79%
**Iterazioni**: 2
```

---

#### 7.1.6 Esempio 6: Query Impossibile (Fuori Ambito)

**Query**: *"Qual è la ricetta della carbonara autentica?"*

**Caratteristiche**:
- Intent: `fuori_ambito`
- Complessità: N/A
- Gestione: **Reject early** (Query Understanding)

---

##### Trace

**Query Understanding**:
```json
{
  "concepts": [],
  "intent": "fuori_ambito",
  "intent_confidence": 0.98,
  "entities": []
}
```

**Early Rejection**:
```json
{
  "status": "rejected",
  "reason": "Query fuori ambito giuridico",
  "output": "Mi dispiace, questa domanda non riguarda il diritto italiano. MERL-T è specializzato in questioni giuridiche. Posso aiutarti con domande su norme, contratti, diritti, giurisprudenza italiana."
}
```

**Durata**: 0.3 secondi (solo Query Understanding)

---

### 7.2 Bootstrap Strategy

La **Bootstrap Strategy** descrive come avviare MERL-T da zero fino a un sistema RLCF-optimized.

#### 7.2.1 Fasi di Bootstrap

```
┌────────────────────────────────────────────────────────────────┐
│                     BOOTSTRAP TIMELINE                         │
└────────────────────────────────────────────────────────────────┘

FASE 1: GENERIC (Settimana 1-4)
  ├─ Router: Regole hard-coded
  ├─ Experts: Prompt engineering generico
  ├─ Stop Criteria: Threshold fissi
  └─ Obiettivo: Sistema funzionante end-to-end

FASE 2: FINE-TUNED (Settimana 5-12)
  ├─ Router: Fine-tuning su dataset annotato (500 query)
  ├─ Experts: Prompt ottimizzati per dominio legale italiano
  ├─ Stop Criteria: Threshold adattivi per intent
  └─ Obiettivo: Precisione +20% vs generic

FASE 3: RLCF (Settimana 13+)
  ├─ Router: RLCF-trained su feedback community (1000+ feedback)
  ├─ Experts: RLCF per weighting argomenti
  ├─ Stop Criteria: ML-based learned
  └─ Obiettivo: User satisfaction > 4.0/5.0

FASE 4: CONTINUOUS LEARNING (Ongoing)
  ├─ Weekly RLCF training batches
  ├─ A/B testing nuovi checkpoint
  └─ Obiettivo: Miglioramento continuo
```

---

#### 7.2.2 Fase 1: Generic Bootstrap (Settimana 1-4)

**Obiettivo**: Sistema end-to-end funzionante con componenti **generici** (zero training iniziale).

##### Componenti Fase 1

**1. Query Understanding**:
- **Modello**: spaCy `it_core_news_lg` (pre-trained generico)
- **Intent Classifier**: Rule-based con keyword matching
  ```
  if "valido" or "validità" in query → intent = "validità_atto"
  if "interpretare" or "significato" in query → intent = "interpretazione_norma"
  if "diritto" and "vs" or "contrasto" in query → intent = "bilanciamento_diritti"
  ```
- **Complexity**: Euristica semplice (lunghezza query + numero entità)

**2. KG Enrichment**:
- **Database**: Neo4j popolato con **corpus minimo**:
  - Costituzione
  - Codice Civile (Libro I-VI)
  - Codice Penale (parte generale)
  - Leggi principali (L. 300/1970, Jobs Act)
- **Query**: Template Cypher fissi (no ottimizzazione)

**3. Router**:
- **Strategia**: **Regole hard-coded** deterministiche
  ```
  Router Rule Table:
  | Intent | Complessità | Esperti |
  |--------|-------------|---------|
  | validità_atto | < 0.7 | literal, precedent |
  | validità_atto | ≥ 0.7 | literal, systemic, precedent |
  | interpretazione_norma | qualsiasi | literal, systemic, precedent |
  | bilanciamento_diritti | qualsiasi | ALL (4 esperti) |
  ```
- **Retrieval**: Sempre KG + API (no ottimizzazione strategia)

**4. Experts**:
- **Prompt**: Generic legal reasoning prompts (non specializzati)
- **Modello**: GPT-4o (per qualità sufficiente senza fine-tuning)

**5. Stop Criteria**:
- **Strategia**: Threshold fissi uguali per tutti gli intent
  ```
  STOP se:
    - confidence_avg > 0.80 AND
    - divergence_score < 0.20 AND
    - iteration >= 1
  MAX iterations: 3 (hard limit)
  ```

**6. Synthesis**:
- **Weighting**: Pesi uniformi tra esperti (no preferenze)

##### Metriche Attese Fase 1

| Metrica | Target Fase 1 | Baseline |
|---------|---------------|----------|
| User Satisfaction | 3.0-3.5 / 5.0 | N/A |
| Router Accuracy | 60-70% | Random (25%) |
| Avg Iterations | 1.8 | N/A |
| P95 Latency | < 15s | N/A |
| LLM Cost/Query | ~$0.08 | N/A |

##### Deliverable Fase 1

✅ Sistema end-to-end funzionante
✅ 100 query di test annotate manualmente
✅ Baseline metrics per confronto fasi successive
✅ Trace logging completo per raccolta dati

---

#### 7.2.3 Fase 2: Fine-Tuned (Settimana 5-12)

**Obiettivo**: Ottimizzare componenti con **supervised learning** su dataset annotato.

##### Dataset Annotation (Settimana 5-6)

**Raccolta Dati**:
1. **500 query reali** da utenti beta (avvocati, praticanti)
2. **Annotation manuale** da esperti giuridici:
   - Intent corretto
   - Complessità (scala 0-1)
   - Expert selection ideale
   - Norme rilevanti
   - Risposta gold standard

**Esempio Annotazione**:
```json
{
  "query": "Un minorenne può stipulare un contratto valido?",
  "annotations": {
    "intent": "validità_atto",
    "complexity": 0.68,
    "experts_ideal": ["literal", "precedent"],
    "norms_relevant": ["cc_art_2", "cc_art_322", "cc_art_1425"],
    "answer_gold": "Contratto annullabile salvo eccezioni Art. 322",
    "sources_gold": ["cc_art_2", "cc_art_1425", "Cass. 6234/2018"]
  }
}
```

##### Fine-Tuning Componenti (Settimana 7-10)

**1. Intent Classifier**:
- **Modello**: Fine-tune BERT italiano (`dbmdz/bert-base-italian-cased`)
- **Training set**: 500 query annotate
- **Accuracy target**: > 85%

**2. Complexity Scorer**:
- **Modello**: Regressione (Random Forest o XGBoost)
- **Features**: lunghezza, entità, concetti, sentiment
- **MAE target**: < 0.15

**3. Router Expert Selection**:
- **Modello**: Multi-label classifier (BERT fine-tuned)
- **Input**: intent + complexity + concepts
- **Output**: probability per expert
- **Accuracy target**: > 75%

**4. Router Retrieval Planning**:
- **Strategia**: Decision tree basato su features query
- **Ottimizzazione**: Minimizza costi recupero mantenendo recall > 0.90

**5. Experts Prompts**:
- **Ottimizzazione**: Few-shot prompting con esempi italiani
- **Specializzazione**: Prompt diversi per intent type
- **Esempio**:
  ```
  Literal Expert Prompt (validità_atto):
  "Sei un esperto di interpretazione letterale del diritto civile italiano.
  Analizza la seguente query applicando sillogismo giuridico rigoroso.
  Cita articoli codice civile/penale con numerazione precisa.

  [Few-shot examples...]

  Query: {query}
  Norme rilevanti: {norms}
  ```

**6. Stop Criteria Adaptive Thresholds**:
- **Strategia**: Threshold diversi per intent (learned da data)
- **Training**: Analisi 500 trace → ottimizza threshold per minimizzare iterazioni inutili
- **Risultato**:
  ```
  Intent-Specific Thresholds:
  | Intent | Confidence | Divergence | Coverage |
  |--------|-----------|------------|----------|
  | validità_atto | 0.85 | 0.15 | 0.75 |
  | bilanciamento | 0.75 | 0.30 | 0.80 |
  | lacune | 0.70 | 0.35 | 0.85 |
  ```

##### Metriche Attese Fase 2

| Metrica | Target Fase 2 | Delta vs Fase 1 |
|---------|---------------|-----------------|
| User Satisfaction | 3.8-4.0 / 5.0 | +20-25% |
| Router Accuracy | 80-85% | +15-20pp |
| Avg Iterations | 1.4 | -22% |
| P95 Latency | < 12s | -20% |
| LLM Cost/Query | ~$0.06 | -25% |

##### Deliverable Fase 2

✅ Fine-tuned models deployed
✅ Intent classifier accuracy > 85%
✅ Router accuracy > 80%
✅ Adaptive thresholds per intent
✅ 500-query test set con gold standard

---

#### 7.2.4 Fase 3: RLCF (Settimana 13-24)

**Obiettivo**: Apprendere da **feedback community** per ottimizzare decisioni.

##### RLCF Setup (Settimana 13-14)

**1. Feedback Collection Interface**:
- UI per rating 1-5 stelle (overall + per componente)
- Preferenza comparativa (A vs B)
- Correzione testuale
- Segmentazione utenti (avvocato, giudice, giurista, studente)

**2. Reward Signal Design** (vedi Part 5.2):
- Mapping feedback → reward numerico
- Reward shaping per componente

**3. Training Infrastructure**:
- PostgreSQL per training data storage
- Offline RL training pipeline (PPO/DPO)
- A/B testing framework

##### RLCF Training Cycles (Settimana 15-24)

**Ciclo Settimanale**:
```
Week N:
  Day 1-7: Produzione (raccolta feedback)
          ├─ 200-300 query/settimana
          ├─ 100-150 feedback (50% feedback rate target)
          └─ Accumulo training data

Week N+1:
  Day 1: Data aggregation & cleaning
  Day 2-3: Offline RL training (PPO)
          ├─ Router expert selection
          ├─ Router retrieval planning
          ├─ Stop criteria
          └─ Synthesis weighting
  Day 4: Validation & A/B test setup
  Day 5-7: A/B test (10% traffic nuovo modello)
  Day 7: Deploy se A/B positivo (gradual rollout)
```

**Accumulo Feedback**:
- Week 13: 150 feedback → Router v2.0
- Week 14: 300 feedback → Router v2.1
- Week 16: 600 feedback → Router v2.2 + Stop Criteria v1.0
- Week 20: 1200 feedback → Full RLCF system (Router + Experts + Synthesis)
- Week 24: 2000+ feedback → Stable RLCF v1.0

##### RLCF Components Optimization

**1. Router Expert Selection** (priorità alta):
- **Obiettivo**: Apprendere quali esperti selezionare per massimizzare user satisfaction
- **Training data**: (intent, complexity, concepts) → experts → reward
- **Algoritmo**: PPO con policy network
- **Improvement atteso**: +10-15% accuracy vs rule-based

**2. Stop Criteria** (priorità alta):
- **Obiettivo**: Apprendere quando fermare iterazioni
- **Training data**: (iteration, expert_state, query_features) → STOP/CONTINUE → reward
- **Reward**: +1 se decisione corretta, -1 se iterazione inutile/mancante
- **Improvement atteso**: -20% iterazioni inutili

**3. Synthesis Weighting** (priorità media):
- **Obiettivo**: Apprendere come pesare conclusioni esperti
- **Training data**: expert_conclusions → final_weights → reward
- **Improvement atteso**: +5-10% user satisfaction

**4. Experts Argument Emphasis** (priorità bassa):
- **Obiettivo**: Apprendere quali argomenti enfatizzare
- **Complesso**: Richiede feedback granulare per argomento
- **Timeline**: Fase 4 (continuous learning)

##### Metriche Attese Fase 3

| Metrica | Target Fase 3 | Delta vs Fase 2 |
|---------|---------------|-----------------|
| User Satisfaction | > 4.2 / 5.0 | +10-15% |
| Router Accuracy | > 87% | +5-7pp |
| Avg Iterations | 1.2 | -15% |
| Iteration Efficiency | > 75% | +20pp |
| P95 Latency | < 10s | -15% |
| LLM Cost/Query | ~$0.05 | -15% |

##### Deliverable Fase 3

✅ RLCF pipeline completo (feedback → training → deploy)
✅ 2000+ feedback raccolti e processati
✅ Router RLCF v2.x deployed
✅ Stop Criteria ML-based deployed
✅ A/B testing framework operativo
✅ User satisfaction > 4.0/5.0

---

#### 7.2.5 Fase 4: Continuous Learning (Ongoing)

**Obiettivo**: Miglioramento continuo perpetuo.

##### Strategie Continuous Learning

**1. Weekly RLCF Batches**:
- Continua ciclo settimanale: produzione → feedback → training → deploy
- Accumulo graduale training data (target: 10K+ feedback dopo 1 anno)

**2. Quarterly Model Refresh**:
- Ogni 3 mesi: retrain completo su dataset cumulativo
- Previene overfitting su feedback recenti
- Mantiene memoria di pattern storici

**3. Drift Detection**:
- Monitoraggio metriche in produzione
- Alert se accuracy < baseline - 5%
- Trigger investigazione + potenziale rollback

**4. New Intent Detection**:
- Analisi query con `intent=altro` (catch-all)
- Se cluster significativo → crea nuovo intent
- Esempio: dopo 2 mesi, emerge cluster "diritto_digitale" → aggiungi intent

**5. Jurisprudence Updates**:
- Weekly crawling sentenze Cassazione/TAR
- Auto-update VectorDB con nuove sentenze
- Quarterly update KG con nuove norme

**6. Domain Expansion**:
- Anno 1: Diritto civile + lavoro (core)
- Anno 2: + Diritto penale, amministrativo
- Anno 3: + Diritto tributario, societario

##### Metriche Target Anno 1

| Metrica | Target Anno 1 | Baseline Fase 1 |
|---------|---------------|-----------------|
| User Satisfaction | > 4.3 / 5.0 | 3.2 |
| Router Accuracy | > 90% | 65% |
| Avg Iterations | < 1.2 | 1.8 |
| Coverage (intent) | 95% | 70% |
| Feedback Rate | > 40% | N/A |

---

### 7.3 Italian Legal Specifics

MERL-T è progettato **specificamente per il sistema giuridico italiano**. Aspetti peculiari:

#### 7.3.1 Fonti del Diritto Italiano

**Gerarchia Fonti** (implementata in KG):
```
1. Costituzione (rigida, prevalenza assoluta)
2. Leggi costituzionali
3. Regolamenti UE direttamente applicabili
4. Leggi ordinarie (Codici, Leggi speciali)
5. Decreti Legislativi (Art. 76-77 Cost.)
6. Decreti Legge (Art. 77 Cost.)
7. Regolamenti (governativi, ministeriali, regionali)
8. Usi e consuetudini
```

**Conflitto tra Fonti**:
- Expert "Principles Balancer" gestisce conflitti costituzionali
- KG Enrichment prioritizza norme superiori nella gerarchia

#### 7.3.2 Multivigenza Normativa

**Problema**: Stessa norma ha versioni diverse nel tempo.

**Soluzione MERL-T**:
- KG include `vigenza_inizio` e `vigenza_fine` per ogni articolo
- API Normattiva richiede versione **vigente alla data query** (default: oggi)
- Gestione **diritto intertemporale** (quale norma applicabile a fatto passato)

**Esempio**:
```cypher
// Query versione vigente oggi
MATCH (a:Article {id: "cc_art_2043"})
WHERE a.vigenza_inizio <= date() AND (a.vigenza_fine IS NULL OR a.vigenza_fine > date())
RETURN a
```

#### 7.3.3 Interpretazione Italiana

**Scuole interpretative** (riflesse nei 4 Experts):

| Expert | Scuola | Tradizione Italiana |
|--------|--------|---------------------|
| Literal | Esegesi | Scuola dell'Esegesi, positivismo giuridico |
| Systemic | Teleologica | Interpretazione sistematica (Codice Civile 1942) |
| Principles | Costituzionalista | Post-Costituzione 1948, bilanciamento valori |
| Precedent | Realismo | Nomofilachia Cassazione (SS.UU.) |

**Ruolo Cassazione**:
- Sezioni Unite: orientamento vincolante de facto
- Expert "Precedent" prioritizza SS.UU. vs sezioni semplici

#### 7.3.4 Codici Principali

**Coverage MERL-T**:
- ✅ Codice Civile (1942, Libri I-VI)
- ✅ Codice Penale (1930, Parte Generale + Speciale)
- ✅ Codice Procedura Civile
- ✅ Codice Procedura Penale
- ✅ Leggi speciali principali (L. 300/1970, Jobs Act, Codice Privacy, ecc.)
- ⚠️ Legislazione regionale (parziale, complessità federalismo)

---

### 7.4 Conclusioni

#### 7.4.1 Riepilogo Architettura MERL-T

MERL-T implementa uno **scenario ibrido avanzato** (Scenario 14):

**Pipeline Completa**:
```
Query Input
  ↓
[1] Query Understanding (ML-based: NER + intent + complexity)
  ↓
[2] KG Enrichment (Neo4j: concepts → norms mapping)
  ↓
[3] Router (RLCF-learned: expert selection + retrieval planning)
  ↓
[4] Retrieval (Parallel: KG + API Normattiva + VectorDB)
  ↓
[5] Reasoning Experts (Parallel: 2-4 esperti epistemologicamente separati)
  ↓
[6] Loop Controller (ML-based stop criteria, RLCF-learned)
  ↓ (se STOP)
[7] Synthesis (Convergent vs Divergent con Majority+Minority report)
  ↓
[8] Output + Trace Export (JSON + Markdown)
```

**Orchestrazione**: LangGraph StateGraph con state persistence

**Apprendimento**: RLCF continuo su feedback community legale

---

#### 7.4.2 Punti di Forza

**1. Trasparenza & Spiegabilità**:
- Trace completa di ogni decisione
- Rationale esplicito per ogni scelta
- Fonti citate con pesi
- Export human-readable + machine-readable

**2. Robustezza**:
- 4 Experts epistemologicamente diversi → copertura prospettive
- Iterative loop → approfondimento automatico se necessario
- Error handling con retry + fallback
- State persistence per resume

**3. Adattabilità**:
- RLCF → miglioramento continuo da feedback
- Routing dinamico → esperti/retrieval adattati alla query
- Threshold adattivi per intent → efficienza

**4. Accuratezza Dominio**:
- KG specializzato su diritto italiano
- API Normattiva → testi ufficiali sempre aggiornati
- Expert "Principles" → gestisce peculiarità costituzione italiana
- Multivigenza normativa gestita

**5. Scalabilità**:
- Architettura modulare (ogni componente sostituibile)
- Parallelizzazione (Retrieval + Experts)
- Caching multi-livello
- Deployment containerizzato

---

#### 7.4.3 Limitazioni & Sfide

**1. Dipendenza da Fonti Esterne**:
- **Rischio**: API Normattiva down → fallback a VectorDB (testi non ufficiali)
- **Mitigazione**: Cache + replica testi su storage locale

**2. Costi LLM**:
- **Stima**: $0.05-0.08 per query (4 Experts con GPT-4o)
- **Mitigazione**: Model selection dinamico (GPT-4o-mini per query semplici)

**3. Latenza**:
- **P95**: 10-15 secondi (2-3 iterazioni con 4 Experts)
- **Sfida**: Utenti si aspettano < 5s
- **Mitigazione**: Parallelizzazione + caching + pre-warming KG

**4. Coverage Legislazione**:
- **Gap**: Legislazione regionale, norme tecniche settoriali
- **Roadmap**: Espansione graduale corpus

**5. Bias nel RLCF**:
- **Rischio**: Feedback da utenti non rappresentativi (es. solo avvocati civilisti)
- **Mitigazione**: Segmentazione feedback per expertise + weight balancing

**6. Evoluzione Giurisprudenziale**:
- **Sfida**: Nuove sentenze Cassazione richiedono update continuo
- **Soluzione**: Weekly crawling + auto-update VectorDB

**7. Casi Edge**:
- **Limite**: Query che richiedono expertise ultra-specialistica (es. diritto tributario internazionale)
- **Gestione**: Confidence bassa + disclaimer "consulta esperto specializzato"

---

