# Query Understanding and Preprocessing

## 1. Introduction

Query understanding is the **first critical step** in the MERL-T legal reasoning pipeline, transforming raw user input into a structured, enriched query object that enables optimal routing and reasoning.

### 1.1 Purpose

The query understanding component serves multiple objectives:

1. **Normalize** user input (expand abbreviations, correct typos, standardize formats)
2. **Extract** structured entities (norm references, dates, legal concepts, parties)
3. **Understand** user intent (question type, complexity, required reasoning mode)
4. **Enrich** the query with semantic expansions and contextual information
5. **Prepare** a structured query object for downstream components

### 1.2 Position in the Pipeline

```
User Query
    ↓
┌───────────────────────────────────┐
│   QUERY UNDERSTANDING             │
│   (This Document)                 │
│                                   │
│  1. Normalization                 │
│  2. Entity Extraction             │
│  3. Intent Detection              │
│  4. Query Enrichment              │
└───────────────┬───────────────────┘
                ↓
        Structured Query Object
                ↓
┌───────────────────────────────────┐
│   KG ENRICHMENT                   │
│   (knowledge-graph.md)            │
└───────────────────────────────────┘
                ↓
┌───────────────────────────────────┐
│   LLM ROUTER                      │
│   (legal-reasoning.md)            │
└───────────────────────────────────┘
```

### 1.3 Architectural Principles

**Adaptive & Self-Evolving**:
- **NO hardcoded dictionaries** of legal terms
- **Auto-learning** from corpus and user feedback
- **RLCF-driven evolution** for continuous improvement
- **LLM + Knowledge Graph validation** for robustness

### 1.4 Challenges Specific to Legal Queries

Unlike general-purpose query understanding, legal queries present unique challenges:

- **Technical terminology**: Users mix formal legal terms with colloquial language
- **Abbreviations**: Heavy use of legal shorthand ("cc", "Cost.", "art.", "DL")
- **Temporal complexity**: References to specific dates, versions, historical periods (multivigenza)
- **Ambiguity**: Same term can mean different things in different legal contexts
- **Incompleteness**: Users often omit critical context (jurisdiction, time period, specific norm)
- **Mixed intent**: Single query may require both definition and application

**Example Transformation**:
```
User Input (raw):
"E valido contratto firmato minorenne 16 anni cc?"

After Query Understanding:
{
  "original_query": "E valido contratto firmato minorenne 16 anni cc?",
  "normalized_query": "È valido un contratto firmato da un minorenne di 16 anni secondo il codice civile?",
  "entities": {
    "norm_references": [{"law_name": "codice civile", "code": "cc"}],
    "legal_concepts": ["validità contratto", "minorenne", "capacità legale"],
    "numeric_values": [{"value": 16, "unit": "anni", "context": "età"}]
  },
  "intent": {
    "question_type": "validity_assessment",
    "requires_interpretation": true,
    "complexity": 0.68
  },
  "enrichment": {
    "related_norms": ["Art. 2 c.c.", "Art. 320 c.c.", "Art. 322 c.c."],
    "related_concepts": ["capacità di agire", "annullabilità", "rappresentanza legale"]
  }
}
```

---

## 2. Adaptive Architecture Overview

### 2.1 Six-Stage Pipeline

The Query Understanding system processes queries through six adaptive stages:

```
┌────────────────────────────────────────────────────────┐
│               QUERY UNDERSTANDING PIPELINE             │
└────────────────────────────────────────────────────────┘

Query Input: "È valido un contratto firmato da un sedicenne?"
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ 1. ABBREVIATION EXPANSION (Auto-Learning)              │
│ ──────────────────────────────────────────────────────│
│ Strategy: Auto-learning da corpus + feedback RLCF     │
│                                                         │
│ Corpus-Extracted Dictionary (auto-updated):            │
│   "c.c." → "codice civile" (freq: 15234, conf: 0.98) │
│   "TFR" → "Trattamento Fine Rapporto" (freq: 8932)   │
│                                                         │
│ Feedback Loop:                                          │
│   User correction → update dictionary + retrain        │
│                                                         │
│ Output: "È valido un contratto firmato da un sedicenne?"│
│         (no abbreviations detected in this query)      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 2. ENTITY EXTRACTION (Legal NER)                       │
│ ──────────────────────────────────────────────────────│
│ Model: Fine-tuned BERT on Italian legal corpus        │
│                                                         │
│ Entities Detected:                                      │
│   - "contratto" → LEGAL_OBJECT                         │
│   - "sedicenne" → PERSON (age: 16, inferred)           │
│   - "firmato" → ACTION                                 │
│                                                         │
│ Output JSON:                                            │
│ {                                                       │
│   "legal_object": "contratto",                         │
│   "person": {"age": 16, "descriptor": "sedicenne"},   │
│   "action": "firma_contratto"                          │
│ }                                                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CONCEPT MAPPING (Hybrid: LLM + KG Validation)      │
│ ──────────────────────────────────────────────────────│
│ Strategy: ZERO dizionari hardcodati, 100% adaptive    │
│                                                         │
│ Step 3.1: LLM Concept Extraction                      │
│ LLM Output (candidate concepts):                       │
│   ["capacità_di_agire", "validità_contrattuale",      │
│    "minore_età", "contratto", "annullabilità"]        │
│                                                         │
│ Step 3.2: KG Validation                                │
│ Neo4j Query: MATCH (c:LegalConcept) WHERE c.name IN...│
│   ✅ "capacità_di_agire" → EXISTS in KG               │
│   ✅ "validità_contrattuale" → EXISTS in KG           │
│   ❌ "contratto" → Too generic, filter out            │
│                                                         │
│ Step 3.3: Self-Evolution (concetti nuovi)             │
│ IF concept NOT in KG:                                  │
│   1. LLM validation: "È concetto giuridico?"          │
│   2. Mark for expert review                            │
│   3. If validated → ADD to KG + connect to norms      │
│                                                         │
│ Output: ["capacità_di_agire", "validità_contrattuale",│
│          "minore_età", "annullabilità"]                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 4. INTENT CLASSIFICATION (Multi-Label)                │
│ ──────────────────────────────────────────────────────│
│ Model: BERT multi-label classifier                     │
│                                                         │
│ Intents Detected:                                      │
│   - "validità_atto" (confidence: 0.92)                │
│   - "conseguenze_giuridiche" (confidence: 0.34) ← low │
│                                                         │
│ Threshold: 0.5 → Only "validità_atto" selected        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 5. TEMPORAL EXTRACTION                                 │
│ ──────────────────────────────────────────────────────│
│ No temporal references in query                        │
│ → Default: current law (vigente oggi)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 6. COMPLEXITY SCORING                                  │
│ ──────────────────────────────────────────────────────│
│ ML Model (Random Forest):                              │
│   Features: length, entities, concepts, intent         │
│   Output: Complexity score 0.0-1.0 → 0.68            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
                ┌──────────────┐
                │ FINAL OUTPUT │
                └──────────────┘
```

### 2.2 Output Schema

**Structured Query Object** (JSON format):

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

---

## 3. Stage 1: Abbreviation Expansion

### 3.1 Strategy: Auto-Learning from Corpus

**Challenge**: Italian legal text uses hundreds of abbreviations. Hardcoded dictionaries are:
- ❌ Unmaintainable (new abbreviations emerge)
- ❌ Domain-limited (civil vs criminal vs administrative)
- ❌ Context-insensitive ("cc" can mean "codice civile" or "comma comma")

**Solution**: Extract abbreviations automatically from legal corpus using pattern detection.

### 3.2 Pattern Extraction Algorithm

**Corpus Sources**:
- Costituzione, Codice Civile, Codice Penale
- Akoma Ntoso XML documents with structured metadata
- Jurisprudence from Cassazione, Corte Costituzionale
- Legal doctrine from academic publishers

**Extraction Pattern**:
```
Pattern: "Termine Completo (SIGLA)" or "SIGLA (Termine Completo)"

Examples from corpus:
  - "Codice Civile (c.c.)" → sigla: "c.c.", expansion: "Codice Civile", freq: 15234
  - "Trattamento di Fine Rapporto (TFR)" → sigla: "TFR", expansion: "...", freq: 8932
  - "Decreto-Legge (DL)" → sigla: "DL", expansion: "Decreto-Legge", freq: 7654
```

### 3.3 Auto-Generated Dictionary Structure

```json
{
  "abbreviations": [
    {
      "sigla": "c.c.",
      "espansione": "Codice Civile",
      "freq_corpus": 15234,
      "confidence": 0.98,
      "last_updated": "2025-01-02",
      "feedback_count": 234,
      "context_domain": "diritto_civile"
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

### 3.4 RLCF Feedback Loop

**Auto-Update Mechanism**:

```
Scenario: User query "Il TFR va pagato entro quanto?"

Step 1: Sistema espande "TFR" → "Trattamento Fine Rapporto" (confidence 0.95)
Step 2: User feedback: "Espansione corretta"
Step 3: RLCF signal → +1 reward → confidence aumenta a 0.96

Alternative Scenario: User correction
Step 1: Sistema sbaglia "CCNL" → "Codice Civile Nazionale Lavoro"
Step 2: User feedback: "Sbagliato, è 'Contratto Collettivo Nazionale Lavoro'"
Step 3: RLCF signal → -1 reward → dizionario aggiornato → retrain
```

**Evolution Metrics** (example 6 months):

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| Abbreviations Count | 120 | 280 | 520 |
| Average Confidence | 0.82 | 0.89 | 0.94 |
| User Corrections/Week | 15 | 8 | 3 |
| Coverage (queries with abbrev) | 68% | 85% | 94% |

---

## 4. Stage 2: Entity Extraction

### 4.1 Legal-Specific NER

**Challenge**: General-purpose NER (spaCy, Stanford NER) trained on news/Wikipedia fails on legal text:
- ❌ "Art. 1414 c.c." recognized as date/organization
- ❌ "Cassazione" not recognized as court
- ❌ "minorenne" not recognized as legal status

**Solution**: Fine-tune BERT on Italian legal corpus with specialized entity types.

### 4.2 Entity Types for Legal Domain

| Entity Type | Description | Examples |
|-------------|-------------|----------|
| **LEGAL_OBJECT** | Legal instruments, documents | "contratto", "testamento", "sentenza" |
| **PERSON** | Natural persons with legal status | "minorenne", "sedicenne", "maggiorenne" |
| **ORGANIZATION** | Legal entities | "S.p.A.", "associazione", "ente pubblico" |
| **COURT** | Judicial bodies | "Cassazione", "TAR", "Corte Costituzionale" |
| **NORM_REFERENCE** | Citations to norms | "Art. 1414 c.c.", "L. 194/1978" |
| **ACTION** | Legal acts | "firma", "stipula", "recesso", "disdetta" |
| **NUMERIC** | Ages, amounts, durations | "16 anni", "10.000 euro", "30 giorni" |
| **DATE** | Temporal references | "15 marzo 2020", "dal 2020 al 2023" |

### 4.3 Training Data Structure

**Annotated Example**:
```json
{
  "text": "È valido un contratto firmato da un sedicenne?",
  "entities": [
    {"start": 12, "end": 21, "label": "LEGAL_OBJECT", "text": "contratto"},
    {"start": 22, "end": 29, "label": "ACTION", "text": "firmato"},
    {"start": 37, "end": 46, "label": "PERSON", "text": "sedicenne", "attributes": {"age": 16}}
  ]
}
```

### 4.4 Output Schema

```json
{
  "entities": {
    "legal_object": "contratto",
    "person": {
      "age": 16,
      "descriptor": "sedicenne",
      "type": "natural_person"
    },
    "action": "firma_contratto",
    "courts": [],
    "organizations": [],
    "norm_references": [],
    "numeric_values": [
      {"value": 16, "unit": "anni", "context": "età"}
    ],
    "dates": []
  }
}
```

---

## 5. Stage 3: Concept Mapping

### 5.1 Hybrid Architecture: LLM + KG Validation

**Challenge**: Legal concepts are vast and evolving:
- ✅ Traditional concepts: "capacità di agire", "nullità", "prescrizione"
- ✅ Emerging concepts: "diritto all'oblio digitale" (2014), "revenge porn" (2019)
- ❌ Hardcoded dictionaries become obsolete

**Solution**: Use LLM to extract candidate concepts, then validate against Knowledge Graph.

### 5.2 Three-Step Process

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: LLM CONCEPT EXTRACTION                         │
│ ───────────────────────────────────────────────────────│
│ Prompt to LLM:                                          │
│   "Estrai concetti giuridici dalla query:              │
│    'È valido un contratto firmato da un sedicenne?'    │
│    Contesto: diritto civile italiano, focus su         │
│    capacità e validità."                                │
│                                                         │
│ LLM Output (candidate concepts):                        │
│   ["capacità_di_agire", "validità_contrattuale",       │
│    "minore_età", "contratto", "annullabilità"]         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: KG VALIDATION                                  │
│ ───────────────────────────────────────────────────────│
│ Neo4j Query:                                            │
│   MATCH (c:LegalConcept)                               │
│   WHERE c.name IN ["capacità_di_agire", ...]          │
│   RETURN c                                              │
│                                                         │
│ Validation Result:                                      │
│   ✅ "capacità_di_agire" → EXISTS in KG               │
│   ✅ "validità_contrattuale" → EXISTS in KG           │
│   ✅ "minore_età" → EXISTS in KG                      │
│   ❌ "contratto" → Too generic, filter out            │
│   ✅ "annullabilità" → EXISTS in KG                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 3: SELF-EVOLUTION (concetti nuovi)               │
│ ───────────────────────────────────────────────────────│
│ IF concept NOT in KG:                                  │
│   1. Check if legitimate legal concept (LLM)          │
│   2. Mark for expert review (human-in-the-loop)       │
│   3. If validated → ADD to KG + connect to norms      │
│                                                         │
│ Example: "diritto_oblio_digitale" (nuovo 2014)        │
│   → LLM: "Yes, valid concept (GDPR Art. 17)"         │
│   → Expert review: APPROVED                            │
│   → KG update: CREATE (:LegalConcept                  │
│                 {name: "diritto_oblio_digitale"})     │
│   → Connect to: GDPR Art. 17, Corte UE C-131/12      │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Colloquial → Legal Concept Mapping Examples

| User Query (Colloquiale) | LLM Candidates | KG Validation | Final Concepts |
|--------------------------|----------------|---------------|----------------|
| "Un sedicenne può comprare casa?" | `capacità_di_agire`, `acquisto_immobile`, `contratto_compravendita`, `minore_età`, `immobile` | ✅✅✅✅❌ (immobile too generic) | `capacità_di_agire`, `acquisto_immobile`, `contratto_compravendita`, `minore_età` |
| "È legale licenziare donna incinta?" | `licenziamento`, `tutela_maternità`, `discriminazione_genere`, `giusta_causa`, `gravidanza` | ✅✅✅✅❌ | `licenziamento`, `tutela_maternità`, `discriminazione_genere`, `giusta_causa` |
| "Posso disdire contratto telefonico?" | `recesso_contrattuale`, `contratto_consumo`, `diritto_ripensamento`, `telecomunicazioni` | ✅✅✅❌ | `recesso_contrattuale`, `contratto_consumo`, `diritto_ripensamento` |

### 5.4 RLCF-Driven Concept Expansion

**Feedback Loop**:

```
Scenario: Query "Il TFR spetta anche ai collaboratori?"

System Output (initial):
  concepts: ["TFR", "collaboratori", "subordinazione_lavoro"]

User Feedback: "Manca 'collaborazione_coordinata_continuativa'"

RLCF Signal:
  - Generate training example:
    (query: "TFR collaboratori",
     concepts_gold: [..., "collaborazione_coordinata_continuativa"])
  - Update LLM prompt with few-shot example
  - Next similar query → system includes correct concept
```

**Evolution Metrics** (6 months):

| Metric | Phase 1 (Generic) | Phase 2 (Fine-tuned) | Phase 3 (RLCF Month 6) |
|--------|------------------|---------------------|----------------------|
| Concept Mapping Accuracy | 65% | 78% | 89% |
| KG Concepts Count | 450 | 680 | 1250 |
| User Corrections/Week | 25 | 12 | 5 |
| Self-Evolution Events | 0 | 8 | 23 |

### 5.5 Output Schema

```json
{
  "concepts": [
    {
      "name": "capacità_di_agire",
      "confidence": 0.92,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_123"
    },
    {
      "name": "validità_contrattuale",
      "confidence": 0.88,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_456"
    },
    {
      "name": "minore_età",
      "confidence": 0.85,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_789"
    },
    {
      "name": "annullabilità",
      "confidence": 0.79,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_101"
    }
  ]
}
```

---

## 6. Stage 4: Intent Classification

### 6.1 Multi-Label Classification

**Challenge**: Legal queries often have **multiple intents** simultaneously:
- "Cos'è la simulazione contrattuale e quando è applicabile?"
  - Intent 1: `definition` (Cos'è?)
  - Intent 2: `validity_assessment` (quando applicabile?)

**Solution**: Multi-label BERT classifier trained on annotated legal Q&A corpus.

### 6.2 Intent Taxonomy

| Intent | Description | Example Queries |
|--------|-------------|-----------------|
| `validità_atto` | Validity/nullity/annullability assessment | "È valido contratto minorenne?" |
| `interpretazione_norma` | Meaning of norm | "Cosa significa Art. 2043 c.c.?" |
| `conseguenze_giuridiche` | Legal effects/consequences | "Cosa succede se non pago affitto?" |
| `requisiti_procedurali` | Formal requirements | "Quali documenti servono per testamento?" |
| `bilanciamento_diritti` | Conflict of rights/principles | "Prevale libertà espressione o privacy?" |
| `evoluzione_giurisprudenziale` | Case law trends | "Come interpreta Cassazione Art. X?" |
| `lacune_ordinamento` | Regulatory gaps | "Chi è responsabile per danno da IA?" |
| `conformità_costituzionale` | Constitutional compliance | "È costituzionale norma X?" |

### 6.3 Training Data Structure

**Annotated Examples**:
```json
[
  {
    "query": "Cos'è la simulazione contrattuale?",
    "intents": {"definition": 1.0}
  },
  {
    "query": "È valido un contratto firmato da un minorenne?",
    "intents": {"validità_atto": 1.0}
  },
  {
    "query": "Quali sono le principali modifiche alla L. 194/1978?",
    "intents": {"research": 0.9, "temporal_query": 0.7}
  },
  {
    "query": "Prevale l'art. 2 Cost. o l'art. 1414 c.c.?",
    "intents": {"conflict_resolution": 1.0, "bilanciamento_diritti": 0.8}
  }
]
```

### 6.4 RLCF Evolution: Emergent Intents

**New Intents from Feedback**:

```
Example: After 6 months, many queries on "diritto digitale" without specific intent

RLCF Analysis:
  - Cluster of 150 queries with intent="altro" (catch-all)
  - Common pattern: "algoritmo", "IA", "dati personali", "cookies"
  - Proposal: Create new intent "conformità_digitale"

Human Review: APPROVED

System Update:
  - Add intent "conformità_digitale" to classifier
  - Retrain BERT on 150 manually annotated queries
  - Deploy new model v2.1
```

### 6.5 Output Schema

```json
{
  "intent": {
    "primary": {
      "type": "validità_atto",
      "confidence": 0.92,
      "description": "User asks about validity/nullity/annullability"
    },
    "secondary": []
  }
}
```

**Multi-Intent Example**:
```json
{
  "intent": {
    "primary": {
      "type": "definition",
      "confidence": 0.92
    },
    "secondary": [
      {
        "type": "validity_assessment",
        "confidence": 0.71
      }
    ]
  }
}
```

---

## 7. Stage 5: Temporal Extraction

### 7.1 Multivigenza Support

**Challenge**: Italian law requires tracking **multiple temporal versions** of norms (multivigenza). Users may ask:
- "Cosa dice Art. 2 c.c.?" → current version
- "Cosa diceva Art. 5 DL 18/2020 il 15 marzo 2020?" → historical version
- "Quali modifiche ha subito L. 194/1978 dal 2000 al 2023?" → range query

**Solution**: NER-based temporal entity extraction + Knowledge Base for implicit references.

### 7.2 Temporal Entity Types

| Type | Pattern | Example | Normalized |
|------|---------|---------|------------|
| **Absolute Date** | "DD Month YYYY" | "15 marzo 2020" | 2020-03-15 |
| **Date Range** | "dal X al Y" | "dal 2020 al 2023" | range(2020-01-01, 2023-12-31) |
| **Relative Date** | "ieri", "settimana scorsa" | "ieri" | 2025-01-01 (if today is 2025-01-02) |
| **Implicit Temporal** | Legal event name | "primo lockdown" | 2020-03-09 to 2020-05-18 |
| **Current** | No temporal reference | (none) | current (oggi) |

### 7.3 Knowledge Base for Implicit Temporal References

**Structure**:
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
    },
    {
      "name": "riforma_cartabia",
      "effective_date": "2022-08-15",
      "source": "D.Lgs. 149/2022"
    }
  ]
}
```

### 7.4 Historical Context Detection

**Verb Tense Analysis**:

```
Query: "Cosa stabiliva l'art. 5 DL 18/2020 il 15 marzo 2020?"

Linguistic Analysis:
  - Verb: "stabiliva" (imperfect tense) → historical query
  - Date: "15 marzo 2020" → explicit past reference

Output:
{
  "temporal_scope": {
    "type": "historical",
    "reference_date": "2020-03-15",
    "requires_version_lookup": true
  }
}
```

**Temporal Indicators**:
- **Imperfect tense**: "stabiliva", "diceva", "prevedeva"
- **Past participle**: "ha modificato", "è stato abrogato"
- **Temporal adverbs**: "allora", "all'epoca", "in passato"

### 7.5 Output Schema

```json
{
  "temporal_scope": {
    "type": "current | historical | range",
    "reference_date": "2025-01-02",
    "end_date": null,
    "requires_version_lookup": false,
    "confidence": 1.0
  }
}
```

**Historical Example**:
```json
{
  "temporal_scope": {
    "type": "historical",
    "reference_date": "2020-03-15",
    "requires_version_lookup": true,
    "indicators": [
      {"type": "verb_tense", "text": "stabiliva", "tense": "imperfect"},
      {"type": "explicit_date", "text": "15 marzo 2020"}
    ]
  }
}
```

---

## 8. Stage 6: Complexity Scoring

### 8.1 ML-Based Complexity Assessment

**Challenge**: Complexity is **not** determinable by simple rules (e.g., word count). Legal complexity depends on:
- Conceptual depth (abstract principles vs concrete rules)
- Ambiguity (multiple valid interpretations)
- Required reasoning (literal vs systemic-teleological)
- Cross-domain interactions (constitutional + civil + criminal)

**Solution**: Train Random Forest regression model on manually annotated queries.

### 8.2 Features for ML Model

**Feature Vector** (no hardcoded thresholds):

```json
{
  "query_length": 50,
  "entities_count": 3,
  "concepts_count": 4,
  "intent_complexity": 0.6,
  "has_temporal_constraint": false,
  "has_bilanciamento": false,
  "avg_concept_specificity": 0.75,
  "norm_references_count": 0,
  "ambiguity_score": 0.2
}
```

**Training Data** (500 queries annotated):
```json
[
  {
    "query": "È valido contratto minorenne?",
    "features": {"length": 50, "entities": 3, "concepts": 4, ...},
    "complexity_label": 0.68
  },
  {
    "query": "In caso di conflitto tra libertà espressione e privacy...",
    "features": {"length": 120, "entities": 8, "concepts": 12, ...},
    "complexity_label": 0.92
  }
]
```

### 8.3 Complexity Score Interpretation

| Range | Level | Routing Implication |
|-------|-------|---------------------|
| 0.0 - 0.3 | **Very Simple** | Literal Interpreter only |
| 0.3 - 0.6 | **Simple** | Literal + Precedent |
| 0.6 - 0.8 | **Medium** | Literal + Systemic + Precedent |
| 0.8 - 1.0 | **Complex** | All 4 experts + iteration likely |

### 8.4 RLCF Refinement

**Feedback Loop**:

```
Scenario: Query predicted as 0.45 (simple) but required complex reasoning

User Feedback: "Risposta insufficiente, serviva analisi costituzionale"
Ground Truth: Complexity should be 0.75 (medium-high)

RLCF Signal:
  - Add to training data: (features, true_complexity=0.75)
  - Retrain Random Forest model
  - Model learns: queries with "constitutional" concepts → higher complexity
```

**Evolution Metrics** (6 months):

| Metric | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| MAE (Mean Absolute Error) | 0.18 | 0.12 | 0.08 |
| Correct Routing % | 72% | 84% | 91% |
| User Satisfaction (complexity) | 3.1/5 | 3.8/5 | 4.3/5 |

### 8.5 Output Schema

```json
{
  "complexity": {
    "score": 0.68,
    "level": "medium",
    "factors": [
      "Multiple concepts (4) → +0.2",
      "Intent requires reasoning → +0.15",
      "No temporal complexity → 0.0",
      "No constitutional conflict → 0.0"
    ],
    "confidence": 0.85
  }
}
```

---

## 9. Complete Output Example

### 9.1 End-to-End Example

**Input Query**:
```
"È valido un contratto di compravendita immobiliare firmato da un sedicenne?"
```

**Query Understanding Output**:
```json
{
  "original_query": "È valido un contratto di compravendita immobiliare firmato da un sedicenne?",

  "normalized_query": "È valido un contratto di compravendita immobiliare firmato da un sedicenne?",

  "entities": {
    "legal_object": "contratto_compravendita",
    "legal_object_specifier": "immobiliare",
    "person": {
      "age": 16,
      "descriptor": "sedicenne",
      "type": "natural_person"
    },
    "action": "firma_contratto"
  },

  "concepts": [
    {
      "name": "capacità_di_agire",
      "confidence": 0.94,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_123"
    },
    {
      "name": "validità_contrattuale",
      "confidence": 0.91,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_456"
    },
    {
      "name": "acquisto_immobile",
      "confidence": 0.88,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_789"
    },
    {
      "name": "minore_età",
      "confidence": 0.86,
      "source": "llm_extracted",
      "kg_validated": true,
      "kg_node_id": "concept_234"
    },
    {
      "name": "rappresentanza_legale",
      "confidence": 0.72,
      "source": "kg_expansion",
      "kg_validated": true,
      "kg_node_id": "concept_567"
    }
  ],

  "intent": {
    "primary": {
      "type": "validità_atto",
      "confidence": 0.93,
      "description": "Assessment of legal validity of act"
    },
    "secondary": [
      {
        "type": "requisiti_procedurali",
        "confidence": 0.64,
        "description": "Formal requirements for real estate transaction"
      }
    ]
  },

  "temporal_scope": {
    "type": "current",
    "reference_date": "2025-01-02",
    "requires_version_lookup": false
  },

  "complexity": {
    "score": 0.74,
    "level": "medium-high",
    "factors": [
      "Multiple concepts (5) → +0.25",
      "Real estate specificity → +0.15",
      "Intent requires reasoning → +0.18",
      "Secondary intent present → +0.10"
    ],
    "confidence": 0.87
  },

  "metadata": {
    "processing_time_ms": 245,
    "stages_completed": [
      "abbreviation_expansion",
      "entity_extraction",
      "concept_mapping",
      "intent_classification",
      "temporal_extraction",
      "complexity_scoring"
    ],
    "rlcf_model_version": "v2.3",
    "trace_id": "QU_20250102_143022_abc456"
  }
}
```

### 9.2 Subsequent Processing

This structured output becomes input for:

1. **KG Enrichment** (knowledge-graph.md)
   - Maps `concepts` to concrete norms via Neo4j queries
   - Expands related concepts (e.g., "rappresentanza_legale" → Art. 320 c.c.)
   - Identifies relevant jurisprudence

2. **LLM Router** (legal-reasoning.md)
   - Uses `intent` and `complexity` to select experts
   - Plans retrieval strategy based on `entities` and `concepts`
   - Determines iteration strategy

---

## 10. RLCF Integration and Evolution

### 10.1 Continuous Learning Architecture

**Feedback Collection**:
```json
{
  "query_id": "QU_20250102_143022_abc456",
  "feedback": {
    "user_id": "user_789",
    "rating": 4,
    "corrections": [
      {
        "stage": "concept_mapping",
        "issue": "Missing concept: 'forma_scritta_atto_pubblico'",
        "correction": {
          "action": "add_concept",
          "concept": "forma_scritta_atto_pubblico",
          "confidence": 0.85
        }
      }
    ],
    "timestamp": "2025-01-02T14:35:00Z"
  }
}
```

### 10.2 Training Dataset Generation

**Weekly Update Cycle**:
```
Week N: Production Usage
  - 500 queries processed
  - 200 user feedback (40% feedback rate)
  - 150 positive (concept mapping correct)
  - 30 corrections (missing concepts)
  - 20 new abbreviations discovered

Week N+1: Training Update
  1. Abbreviation Dictionary Update:
     - Add 5 new abbreviations from corpus
     - Update confidence scores based on feedback

  2. Concept Mapping LLM Prompt Enhancement:
     - Add 30 new few-shot examples from corrections
     - Retrain prompt with RLCF signal

  3. KG Evolution:
     - Add 3 new concepts validated by expert review
     - Connect to 12 new norms

  4. Intent Classifier Retrain:
     - Fine-tune BERT on 200 new annotated queries
     - Accuracy improvement: 85% → 87%

  5. Complexity Model Retrain:
     - Add 50 new labeled examples
     - MAE improvement: 0.12 → 0.10

Week N+1 Friday: A/B Test
  - 10% traffic → new Query Understanding v2.1
  - 90% traffic → stable v2.0
  - Monitor: accuracy, latency, user satisfaction

Week N+2: Deploy (if A/B positive)
  - Gradual rollout: 10% → 50% → 100%
  - Version: v2.0 → v2.1
```

### 10.3 Evolution Metrics Dashboard

**6-Month Evolution Example**:

| Metric | Month 1 (Generic) | Month 3 (Fine-tuned) | Month 6 (RLCF) |
|--------|------------------|---------------------|----------------|
| **Concept Mapping Accuracy** | 65% | 78% | 89% |
| **Abbreviation Coverage** | 120 sigles | 280 sigles | 520 sigles |
| **Intent Classification Acc** | 72% | 85% | 91% |
| **Complexity MAE** | 0.18 | 0.12 | 0.08 |
| **KG Concepts Count** | 450 | 680 | 1250 |
| **Processing Time (p95)** | 320ms | 280ms | 245ms |
| **User Satisfaction** | 3.2/5 | 3.9/5 | 4.4/5 |

### 10.4 Self-Evolution Examples

**Example 1: New Legal Concept Discovery**

```
Query: "Il datore di lavoro può monitorare le email con IA?"

Initial Processing:
  LLM Concepts: ["monitoraggio_dipendenti", "privacy_lavoratore", "IA_workplace"]
  KG Validation: ✅ ✅ ❌ ("IA_workplace" NOT in KG)

Self-Evolution Trigger:
  1. LLM Validation: "È concetto giuridico legittimo?"
     → Response: "Yes, emerging concept (GDPR + Statuto Lavoratori)"
  2. Mark for expert review
  3. Expert review: APPROVED
  4. KG Update:
     CREATE (:LegalConcept {
       name: "IA_workplace",
       description: "Uso di intelligenza artificiale nel contesto lavorativo",
       introduced_date: "2023-05-20",
       source: "Interpretazione GDPR Art. 88 + Art. 4 Statuto Lavoratori"
     })
  5. Connect to norms:
     MATCH (c:LegalConcept {name: "IA_workplace"}),
           (n1:Norm {id: "gdpr_art_88"}),
           (n2:Norm {id: "statuto_lav_art_4"})
     CREATE (n1)-[:REGULATES]->(c), (n2)-[:REGULATES]->(c)

Next Query: "IA_workplace" now in KG → ✅ validated automatically
```

**Example 2: Abbreviation Auto-Discovery**

```
Corpus Analysis (weekly):
  - Pattern found: "Testo Unico Edilizia (TUE)" in 45 documents
  - Frequency: 234 occurrences
  - Context: diritto_urbanistico

Auto-Add to Dictionary:
{
  "sigla": "TUE",
  "espansione": "Testo Unico Edilizia",
  "freq_corpus": 234,
  "confidence": 0.88,
  "auto_discovered": true,
  "requires_validation": true
}

User Query (next week): "Secondo il TUE..."
  → Expansion: "Secondo il Testo Unico Edilizia..."
  → User feedback: "Correct!"
  → Confidence: 0.88 → 0.92
```

---

## 11. Performance and Scalability

### 11.1 Performance Benchmarks

**Query Understanding Latency** (p95):

| Stage | Latency (ms) | Bottleneck | Optimization |
|-------|-------------|-----------|--------------|
| **Abbreviation Expansion** | 15ms | Dictionary lookup | Redis cache |
| **Entity Extraction (NER)** | 80ms | BERT inference | Batch processing |
| **Concept Mapping (LLM)** | 120ms | LLM API call | Parallel LLM + KG |
| **Intent Classification** | 45ms | BERT inference | Model quantization |
| **Temporal Extraction** | 20ms | NER + KB lookup | KB in-memory |
| **Complexity Scoring** | 5ms | Random Forest | Pre-loaded model |
| **Total (p95)** | **245ms** | LLM latency | Async + caching |

### 11.2 Optimization Strategies

**1. Caching Layer** (Redis):
```
Cache Key: hash(query_normalized + model_version)
Cache TTL: 24 hours
Hit Rate Target: > 35% (frequently asked legal questions)

Example:
  Query: "È valido contratto minorenne?"
  Cache Key: "qu_v2.3_hash_abc123"
  Cache Hit: Yes → Return cached result (5ms vs 245ms)
```

**2. Parallel Processing**:
```
Stages that can run in parallel:
  - Abbreviation Expansion || Entity Extraction (independent)
  - LLM Concept Extraction || KG Warm-up (async)
  - Intent Classification || Temporal Extraction (independent)

Sequential Dependencies:
  - Concept Mapping (Step 2: KG validation) depends on (Step 1: LLM extraction)
  - Complexity Scoring depends on all previous stages (uses features)
```

**3. Model Optimization**:
```
- BERT quantization: INT8 → 2.3x faster, -3% accuracy (acceptable)
- Batch processing: Process 16 queries together (throughput +250%)
- Model distillation: BERT-base → DistilBERT (-40% params, -10ms latency)
```

### 11.3 Scalability

**Horizontal Scaling**:
- Query Understanding is **stateless** → can scale horizontally
- Load balancer distributes queries across N workers
- Each worker has own model instances (NER, Intent, Complexity)
- Shared resources: Redis cache, Neo4j KG (read-only)

**Throughput** (per worker):
- Sequential: ~4 queries/second (245ms/query)
- Parallel batch (16 queries): ~65 queries/second

**Target**: 1000 queries/second → ~16 workers (with batching)

---

## 12. Integration with Downstream Components

### 12.1 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ Query Understanding Output                              │
│ {entities, concepts, intent, temporal, complexity}      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ KG ENRICHMENT                                           │
│ • Maps concepts → norms via Cypher queries              │
│ • Expands related concepts (depth 2)                    │
│ • Identifies jurisprudence clusters                     │
│                                                         │
│ Output: EnrichedContext                                 │
│ {mapped_norms, related_concepts, jurisprudence}        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ LLM ROUTER                                              │
│ • Uses intent + complexity to select experts            │
│ • Plans retrieval (KG Agent, API Agent, VectorDB)      │
│ • Determines iteration strategy                         │
│                                                         │
│ Output: RouterDecision                                  │
│ {retrieval_plan, reasoning_plan, iteration_strategy}   │
└─────────────────────────────────────────────────────────┘
```

### 12.2 Cross-Document References

**See also**:
- **[Knowledge Graph](./knowledge-graph.md)** - KG schema and enrichment logic
- **[Legal Reasoning](./legal-reasoning.md)** - Complete reasoning pipeline
- **[Data Ingestion](./data-ingestion.md)** - Corpus processing for auto-learning
- **[RLCF Framework](./rlcf-framework.md)** - Feedback loop architecture

---

## 13. Summary

### 13.1 Key Innovations

1. **Zero Hardcoded Dictionaries**
   - Abbreviations: Auto-learned from corpus
   - Concepts: LLM extraction + KG validation
   - Intents: Multi-label classifier with emergent categories

2. **Self-Evolution**
   - New legal concepts discovered automatically
   - Expert review for validation (human-in-the-loop)
   - KG updated dynamically

3. **RLCF-Driven Continuous Improvement**
   - User corrections → training data
   - Weekly model updates
   - Metrics show 65% → 89% accuracy improvement (6 months)

4. **Adaptive Complexity Assessment**
   - ML-based (Random Forest), not rule-based
   - Learns from routing success/failure
   - Improves expert selection accuracy

### 13.2 Design Principles Maintained

✅ **Theoretical/Agnostic**: No implementation code, only conceptual models
✅ **Adaptive**: All components learn from data and feedback
✅ **Traceable**: Every decision logged with rationale
✅ **Scalable**: Stateless, horizontally scalable architecture
✅ **Robust**: Hybrid LLM + symbolic validation prevents hallucination

---

**Document Version**: 2.0 (Adaptive Architecture)
**Last Updated**: 2025-01-02
**Replaces**: query-understanding.md v1.0 (rule-based approach)
