# Preprocessing Layer Architecture

**Implementation Status**: ✅ **COMPLETATO**
**Current Version**: v0.7.0
**Last Updated**: November 2025

**Implemented Components**:
- ✅ Query Understanding: Entity extraction, NER, intent classification
- ✅ KG Enrichment Service: 5 data sources (Normattiva, Cassazione, Dottrina, Community, RLCF)
- ✅ NER Feedback Loop: 4 correction types, automatic training dataset generation
- ✅ LangGraph Integration: Preprocessing node in workflow
- ✅ Graceful Degradation: Fallback when KG unavailable
- ✅ Test Suite: 33 tests (93.9% success rate)

**Code Location**: `backend/preprocessing/`
**Tests**: `tests/orchestration/test_preprocessing_integration.py`, `test_workflow_with_preprocessing.py`, `test_graceful_degradation.py`

---

## 1. Introduction

The **Preprocessing Layer** is the entry point of the MERL-T pipeline, responsible for transforming raw user queries into structured, enriched representations that enable precise legal reasoning. This layer consists of two major subsystems:

1. **Query Understanding Pipeline** (6-stage adaptive process)
2. **KG Enrichment Engine** (concept-to-norm mapping via graph traversal)

**Design Principles**:
- **Adaptive**: Components self-evolve via RLCF feedback
- **Composable**: Each stage is independently deployable and testable
- **Traceable**: Every transformation is logged with trace IDs
- **Agnostic**: Abstract interfaces allow technology swapping

**Performance Targets**:
- Query Understanding: < 300ms (6 stages sequential)
- KG Enrichment: < 50ms (parallel graph queries, no LLM)
- Total Preprocessing: < 350ms (sequential pipeline)

**Reference**: See `docs/02-methodology/query-understanding.md` for theoretical foundation.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY (raw text)                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│              QUERY UNDERSTANDING PIPELINE (6 stages)                 │
│                                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │Abbreviation│→ │  Entity    │→ │  Concept   │→ │   Intent   │  │
│  │ Expansion  │  │ Extraction │  │  Mapping   │  │ Classifier │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│                                        ↓                             │
│                        ┌────────────┐  ┌────────────┐              │
│                        │  Temporal  │→ │ Complexity │              │
│                        │ Extraction │  │   Scoring  │              │
│                        └────────────┘  └────────────┘              │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
                     QueryContext Object
                     (entities, concepts, intent,
                      temporal_scope, complexity)
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   KG ENRICHMENT ENGINE (parallel)                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Concept-to-  │  │   Related    │  │Jurisprudence │             │
│  │Norm Mapping  │  │   Concepts   │  │  Clustering  │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                      ┌──────────────┐                               │
│                      │ Hierarchical │                               │
│                      │   Context    │                               │
│                      └──────────────┘                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
                     EnrichedContext Object
                     (mapped_norms, related_concepts,
                      jurisprudence_clusters, hierarchical_context)
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    OUTPUT TO ORCHESTRATION LAYER                     │
│              (Router receives QueryContext + EnrichedContext)        │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Characteristics**:
- Query Understanding stages execute **sequentially** (each depends on previous)
- KG Enrichment queries execute **in parallel** (independent graph queries)
- No LLM calls in KG Enrichment (pure graph traversal)
- Total latency dominated by Query Understanding (KG is fast)

---

## 3. Query Understanding Pipeline

**Reference**: `docs/02-methodology/query-understanding.md`

The Query Understanding Pipeline transforms raw text into a structured `QueryContext` object through 6 adaptive stages. Each stage is independently deployable and learns from RLCF feedback.

### 3.1 Abbreviation Expansion Engine

**Purpose**: Expand legal abbreviations to full forms using corpus-extracted dictionary.

**Component Interface**:

```json
{
  "component": "abbreviation_expansion_engine",
  "type": "auto_learning_nlp",
  "interface": {
    "input": {
      "raw_query": "string",
      "language": "it | en"
    },
    "output": {
      "expanded_query": "string",
      "expansions": [
        {
          "abbreviation": "c.c.",
          "expansion": "codice civile",
          "confidence": 0.98,
          "position": [12, 16]
        }
      ],
      "trace_id": "ABB-{timestamp}-{uuid}"
    }
  }
}
```

**Processing Logic**:

```
┌──────────────────────────────────────┐
│ 1. Tokenize query                    │
│    Split into words/phrases          │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 2. Pattern Matching                  │
│    Match against abbreviation dict   │
│    (trained on Costituzione, Codici) │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 3. Context-Aware Selection           │
│    If ambiguous, select by frequency │
│    (e.g., "c.c." → codice civile     │
│     vs codice di commercio)          │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 4. Confidence Scoring                │
│    Score based on:                   │
│    - Frequency in corpus             │
│    - Surrounding context match       │
└────────────┬─────────────────────────┘
             ↓
     Expanded Query
```

**Data Schema**:

Abbreviation dictionary format:
```json
{
  "abbreviation": "c.c.",
  "expansions": [
    {
      "full_form": "codice civile",
      "frequency": 0.95,
      "contexts": ["art.", "comma", "contratto"]
    },
    {
      "full_form": "codice di commercio",
      "frequency": 0.05,
      "contexts": ["società", "fallimento"]
    }
  ]
}
```

**Technology Mapping**:

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **Regex + Dictionary** | Pattern matching with static dictionary | Bootstrap (Phase 1) | 1 |
| **spaCy PhraseMatcher** | Fast token-based matching | Production (Phase 2+) | 2+ |
| **RLCF-learned Dictionary** | Dictionary updated from community feedback | Continuous evolution | 3+ |

**RLCF Integration**:
- Community corrects misexpansions → New entries added to dictionary
- Frequency scores updated based on validated expansions
- Weekly dictionary refresh

**Error Handling**:
- Unknown abbreviation → Pass through unchanged (no blocking)
- Ambiguous abbreviation → Select highest frequency option
- Malformed input → Return original query + warning log

---

### 3.2 Entity Extraction (Legal NER)

**Purpose**: Extract structured legal entities from normalized query text.

**Component Interface**:

```json
{
  "component": "entity_extraction",
  "type": "fine_tuned_bert_ner",
  "interface": {
    "input": {
      "normalized_query": "string",
      "language": "it"
    },
    "output": {
      "entities": [
        {
          "text": "Art. 1453 c.c.",
          "type": "NORM_REFERENCE",
          "start": 20,
          "end": 34,
          "confidence": 0.96,
          "metadata": {
            "norm_id": "art_1453_cc",
            "article": "1453",
            "source": "codice civile"
          }
        },
        {
          "text": "contratto",
          "type": "LEGAL_OBJECT",
          "start": 45,
          "end": 54,
          "confidence": 0.89
        }
      ],
      "trace_id": "ENT-{timestamp}-{uuid}"
    }
  }
}
```

**Entity Types** (8 categories):

| Entity Type | Description | Examples |
|------------|-------------|----------|
| **NORM_REFERENCE** | References to legal norms | "Art. 1453 c.c.", "L. 241/1990" |
| **LEGAL_OBJECT** | Legal concepts/objects | "contratto", "proprietà", "servitù" |
| **PERSON** | Physical/legal persons | "creditore", "società", "amministratore" |
| **ORGANIZATION** | Legal entities | "Ministero", "Consiglio di Stato" |
| **COURT** | Judicial bodies | "Cassazione", "TAR Lazio", "CGUE" |
| **ACTION** | Legal actions/procedures | "ricorso", "impugnazione", "risoluzione" |
| **NUMERIC** | Numeric values with legal meaning | "30 giorni", "maggiore età", "€10.000" |
| **DATE** | Temporal references | "31/12/2023", "entro il 2025" |

**Processing Logic**:

```
┌──────────────────────────────────────┐
│ 1. BERT Tokenization                 │
│    Tokenize with BERT tokenizer      │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 2. BERT Inference                    │
│    Fine-tuned BERT on Italian legal  │
│    corpus (Costituzione, Codici,     │
│    Sentenze, Leggi)                  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 3. BIO Tagging                       │
│    B-NORM_REFERENCE                  │
│    I-NORM_REFERENCE                  │
│    O (outside entity)                │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 4. Entity Aggregation                │
│    Combine B-I tokens into entities  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 5. Confidence Filtering              │
│    Filter entities < threshold       │
│    (default: 0.7)                    │
└────────────┬─────────────────────────┘
             ↓
   Structured Entities Array
```

**Technology Mapping**:

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **spaCy it_core_news_lg** | Pretrained Italian NER | Bootstrap (Phase 1) | 1 |
| **dbmdz/bert-base-italian-cased** | Italian BERT base | Fine-tuning foundation | 2 |
| **Fine-tuned BERT** | Trained on 10K annotated legal queries | Production (Phase 2+) | 2+ |
| **Distilled Legal NER** | Knowledge distillation from BERT | Optimized performance (Phase 5) | 5 |

**Fine-Tuning Data**:
- 10,000 annotated legal queries (ALIS community + RLCF)
- Corpus: Costituzione, Codice Civile, Codice Penale, Leggi, Sentenze
- Annotation format: BIO tagging

**RLCF Integration**:
- Community corrects entity boundaries and types
- Corrections added to fine-tuning dataset
- Monthly model retraining with accumulated feedback

**Error Handling**:
- Low confidence entity → Include with warning flag
- Overlapping entities → Select higher confidence
- Malformed entity span → Log and skip

---

### 3.3 Concept Mapping Engine (Hybrid LLM + KG)

**Purpose**: Map colloquial/ambiguous language to precise legal concepts validated in Knowledge Graph.

**Component Interface**:

```json
{
  "component": "concept_mapping_engine",
  "type": "hybrid_llm_kg",
  "interface": {
    "input": {
      "entities": "array",
      "raw_query": "string"
    },
    "output": {
      "concepts": [
        {
          "concept_id": "risoluzione_contratto",
          "label": "Risoluzione del contratto",
          "confidence": 0.92,
          "source": "kg_validated",
          "context": "Inadempimento di una parte",
          "related_norms": ["art_1453_cc", "art_1454_cc"]
        }
      ],
      "trace_id": "CON-{timestamp}-{uuid}"
    }
  }
}
```

**Processing Logic** (3-step hybrid approach):

```
┌───────────────────────────────────────────────┐
│ STEP 1: LLM Candidate Generation              │
│   Input: Raw query + entities                 │
│   Prompt: "Extract legal concepts from query" │
│   Output: Candidate concepts (unvalidated)    │
└────────────┬──────────────────────────────────┘
             ↓
┌───────────────────────────────────────────────┐
│ STEP 2: KG Validation (Cypher queries)        │
│   For each candidate concept:                 │
│   MATCH (c:ConcettoGiuridico)                 │
│   WHERE c.label CONTAINS "concept"            │
│   RETURN c.id, c.label, c.definition          │
│                                               │
│   If match found → Validated concept          │
│   If no match → Rejected candidate            │
└────────────┬──────────────────────────────────┘
             ↓
┌───────────────────────────────────────────────┐
│ STEP 3: Enrichment (KG traversal)             │
│   For each validated concept:                 │
│   MATCH (c:ConcettoGiuridico)-[:DISCIPLINATO_│
│   DA]->(n:Norma)                              │
│   RETURN n.id, n.article                      │
│                                               │
│   Attach related norms to concept             │
└────────────┬──────────────────────────────────┘
             ↓
      Validated Concepts Array
```

**LLM Prompt Structure**:

```json
{
  "system": "You are a legal concept extraction expert for Italian law.",
  "user_template": "Given the query: \"{query}\"\nAnd entities: {entities}\n\nExtract the core legal concepts (max 5). Return JSON array with concept labels only.",
  "output_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "label": {"type": "string"}
      }
    }
  }
}
```

**KG Validation Query**:

```cypher
// Match candidate concept against KG
MATCH (c:ConcettoGiuridico)
WHERE c.label CONTAINS $candidate_label
  OR $candidate_label CONTAINS c.label
WITH c,
     size(c.label) AS concept_length,
     size($candidate_label) AS candidate_length
WHERE abs(concept_length - candidate_length) < 10
RETURN c.id AS concept_id,
       c.label AS label,
       c.definition AS definition,
       c.area_giuridica AS legal_area
ORDER BY concept_length ASC
LIMIT 1
```

**Enrichment Query** (for validated concepts):

```cypher
// Get related norms for validated concept
MATCH (c:ConcettoGiuridico {id: $concept_id})-[:DISCIPLINATO_DA]->(n:Norma)
RETURN n.id AS norm_id,
       n.article AS article,
       n.source AS source,
       n.hierarchical_level AS level
LIMIT 10
```

**Technology Mapping**:

| Component | Technology | Rationale | Phase |
|-----------|-----------|-----------|-------|
| **LLM** | GPT-4o-mini | Cost-effective for extraction | 1-2 |
| **LLM** | GPT-4o | Higher accuracy for complex queries | 3+ |
| **KG Database** | Neo4j | Property graph for concept validation | All |
| **Query Language** | Cypher | Native Neo4j query language | All |

**RLCF Integration**:
- Community adds missing concepts to KG
- Community corrects concept-to-query mappings
- LLM prompt evolves based on correction patterns
- Weekly KG schema evolution

**Error Handling**:
- No LLM candidates → Return empty concepts array (non-blocking)
- No KG validation → Log unvalidated concept + warning
- Ambiguous KG match → Return multiple candidates with confidence scores

---

### 3.4 Intent Classifier

**Purpose**: Classify user intent into predefined categories to guide expert selection.

**Component Interface**:

```json
{
  "component": "intent_classifier",
  "type": "multi_label_bert_classifier",
  "interface": {
    "input": {
      "query_text": "string",
      "entities": "array"
    },
    "output": {
      "primary_intent": "validità_atto",
      "secondary_intents": ["requisiti_procedurali"],
      "confidence": {
        "validità_atto": 0.88,
        "requisiti_procedurali": 0.62
      },
      "trace_id": "INT-{timestamp}-{uuid}"
    }
  }
}
```

**Intent Taxonomy** (7 categories):

| Intent | Description | Example Queries | Expert Mapping |
|--------|-------------|----------------|----------------|
| **validità_atto** | Validity of legal acts | "È valido un contratto firmato da un minorenne?" | Literal Interpreter |
| **interpretazione_norma** | Interpretation of norms | "Cosa significa 'giusta causa' nell'Art. 2119 c.c.?" | Systemic-Teleological |
| **conseguenze_giuridiche** | Legal consequences | "Cosa succede se non pago l'affitto per 3 mesi?" | Rules Expert |
| **requisiti_procedurali** | Procedural requirements | "Quali documenti servono per costituire una SRL?" | Rules Expert |
| **bilanciamento_diritti** | Balancing of rights | "Privacy vs libertà di stampa: quale prevale?" | Principles Balancer |
| **evoluzione_giurisprudenziale** | Case law evolution | "Come è cambiata la Cassazione su clausole vessatorie?" | Precedent Analyst |
| **lacune_ordinamento** | Legal gaps | "Cosa dice il diritto italiano sugli NFT?" | Systemic-Teleological |

**Processing Logic**:

```
┌──────────────────────────────────────┐
│ 1. Feature Extraction                │
│    - Query text embedding (BERT)     │
│    - Entity types (from stage 3.2)   │
│    - Sentence structure features     │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 2. BERT Classification Head          │
│    Fine-tuned multi-label classifier │
│    Output: 7 sigmoid probabilities   │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 3. Threshold Application             │
│    Primary: max(probabilities)       │
│    Secondary: probs > threshold      │
│    (default threshold: 0.5)          │
└────────────┬─────────────────────────┘
             ↓
   Intent Classification Result
```

**Training Data**:

```json
{
  "query": "È valido un contratto firmato da un minorenne?",
  "labels": {
    "validità_atto": 1,
    "requisiti_procedurali": 1,
    "interpretazione_norma": 0,
    "conseguenze_giuridiche": 0,
    "bilanciamento_diritti": 0,
    "evoluzione_giurisprudenziale": 0,
    "lacune_ordinamento": 0
  },
  "source": "rlcf_annotation"
}
```

**Technology Mapping**:

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **Rule-based classifier** | Keyword matching (TF-IDF + rules) | Bootstrap (Phase 1) | 1 |
| **dbmdz/bert-base-italian-cased** | Italian BERT for embeddings | Phase 2+ | 2+ |
| **Multi-label classification head** | 7-way sigmoid output | Production | 2+ |
| **RLCF-tuned classifier** | Retrained on validated queries | Continuous evolution | 3+ |

**RLCF Integration**:
- Community annotates intent for ambiguous queries
- Corrections feed monthly model retraining
- Intent taxonomy evolves (new categories added based on community needs)

**Error Handling**:
- Low confidence (<0.5 on all intents) → Default to "interpretazione_norma"
- Multiple high-confidence intents → Return all as secondary_intents
- Empty query → Return error with trace ID

---

### 3.5 Temporal Extraction Module

**Purpose**: Extract and normalize temporal references to support multivigenza (multiple valid versions of norms over time).

**Component Interface**:

```json
{
  "component": "temporal_extraction",
  "type": "ner_plus_knowledge_base",
  "interface": {
    "input": {
      "query_text": "string",
      "entities": "array"
    },
    "output": {
      "temporal_scope": {
        "type": "specific_date | date_range | current | historical",
        "reference_date": "2024-01-15",
        "date_range": {
          "start": "2020-01-01",
          "end": "2024-12-31"
        },
        "validity_period": "at_date | in_range | always_current",
        "is_retrospective": false
      },
      "extracted_dates": [
        {
          "text": "1 gennaio 2024",
          "normalized": "2024-01-15",
          "type": "explicit_date"
        }
      ],
      "trace_id": "TMP-{timestamp}-{uuid}"
    }
  }
}
```

**Temporal Scope Types**:

| Scope Type | Description | Example Query | Filter Strategy |
|-----------|-------------|---------------|----------------|
| **current** | Current law (no temporal ref) | "È valido un contratto verbale?" | `is_current = true` |
| **specific_date** | Specific date mentioned | "Quali erano i requisiti nel 2010?" | `date_effective <= 2010 AND (date_end IS NULL OR date_end >= 2010)` |
| **date_range** | Range of dates | "Come è cambiata la norma tra 2015 e 2020?" | `date_effective <= 2020 AND date_end >= 2015` |
| **historical** | Historical reference (no specific date) | "Prima della riforma del lavoro..." | Manual disambiguation or default to current |

**Processing Logic**:

```
┌──────────────────────────────────────┐
│ 1. Explicit Date Extraction (NER)    │
│    - "1 gennaio 2024"                │
│    - "nel 2010"                      │
│    - "31/12/2023"                    │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 2. Verb Tense Analysis               │
│    - Present tense → current         │
│    - Past tense → historical         │
│    - Future tense → planned changes  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 3. Knowledge Base Lookup             │
│    - "riforma del lavoro" → 2012     │
│    - "legge Fornero" → 2012-06-28    │
│    - Event KB maps phrases to dates  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 4. Temporal Scope Classification     │
│    Combine signals to determine type │
└────────────┬─────────────────────────┘
             ↓
     Temporal Scope Object
```

**Event Knowledge Base Example**:

```json
{
  "event": "riforma del lavoro",
  "formal_name": "Legge Fornero (L. 92/2012)",
  "reference_date": "2012-06-28",
  "effective_date": "2012-07-18",
  "description": "Riforma del mercato del lavoro"
}
```

**Technology Mapping**:

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **spaCy DateParser** | Rule-based date extraction | Bootstrap | 1 |
| **BERT NER** | Fine-tuned for DATE entity | Improved accuracy | 2+ |
| **Custom Event KB** | Manually curated legal events | Italian legal context | All |
| **RLCF-expanded KB** | Community-added events | Continuous expansion | 3+ |

**RLCF Integration**:
- Community corrects temporal interpretations
- Community adds missing events to KB (e.g., "decreto Cura Italia" → 2020-03-17)
- Weekly KB updates

**Error Handling**:
- No temporal reference → Default to `type: "current"`
- Ambiguous date → Return multiple interpretations with confidence scores
- Invalid date format → Log warning, attempt to parse

---

### 3.6 Complexity Scoring Model

**Purpose**: Assess query complexity to guide expert selection and iteration strategy.

**Component Interface**:

```json
{
  "component": "complexity_scoring",
  "type": "random_forest_ml",
  "interface": {
    "input": {
      "query_text": "string",
      "entities": "array",
      "concepts": "array",
      "intent": "string",
      "temporal_scope": "object"
    },
    "output": {
      "complexity_score": 0.68,
      "complexity_level": "medium",
      "features": {
        "query_length": 45,
        "entity_count": 3,
        "concept_count": 2,
        "temporal_complexity": 0.2,
        "legal_area_count": 1
      },
      "trace_id": "CPX-{timestamp}-{uuid}"
    }
  }
}
```

**Complexity Levels**:

| Level | Score Range | Description | Expert Strategy |
|-------|-------------|-------------|----------------|
| **low** | 0.0 - 0.4 | Simple factual query | Single expert (Literal Interpreter) |
| **medium** | 0.4 - 0.7 | Moderate interpretation needed | 2 experts (Literal + Systemic) |
| **high** | 0.7 - 1.0 | Complex multi-faceted query | 3+ experts + iteration |

**Feature Engineering**:

```
┌──────────────────────────────────────┐
│ Feature Vector (12 features)         │
├──────────────────────────────────────┤
│ 1. query_length (chars)              │
│ 2. entity_count                      │
│ 3. concept_count                     │
│ 4. unique_entity_types               │
│ 5. intent_confidence (inverse)       │
│ 6. has_temporal_reference (bool)     │
│ 7. temporal_complexity (0-1)         │
│ 8. has_multiple_norms (bool)         │
│ 9. legal_area_count                  │
│ 10. has_negation (bool)              │
│ 11. has_conditional (bool)           │
│ 12. has_comparison (bool)            │
└──────────────────────────────────────┘
             ↓
     Random Forest Regression
     (100 trees, max_depth=10)
             ↓
   Complexity Score (0.0-1.0)
```

**Training Data**:

```json
{
  "query": "È valido un contratto?",
  "features": {
    "query_length": 25,
    "entity_count": 1,
    "concept_count": 1,
    "unique_entity_types": 1,
    "intent_confidence": 0.95,
    "has_temporal_reference": false,
    "temporal_complexity": 0.0,
    "has_multiple_norms": false,
    "legal_area_count": 1,
    "has_negation": false,
    "has_conditional": false,
    "has_comparison": false
  },
  "complexity_label": 0.25,
  "source": "expert_annotated"
}
```

**Technology Mapping**:

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **Rule-based heuristics** | Query length + entity count | Bootstrap | 1 |
| **Random Forest** | Ensemble ML on 12 features | Production | 2+ |
| **XGBoost** | Gradient boosting (optional upgrade) | Higher accuracy | 4+ |
| **RLCF-tuned model** | Retrained on expert assessments | Continuous improvement | 3+ |

**RLCF Integration**:
- Experts rate actual complexity after answering query
- Discrepancies (predicted vs actual) feed model retraining
- Monthly model updates

**Error Handling**:
- Missing features → Use defaults (conservative: mark as higher complexity)
- Score out of range → Clamp to [0.0, 1.0]
- Model inference error → Default to medium complexity (0.5)

---

### 3.7 Query Understanding Integration & Data Flow

**Output Schema** (QueryContext object):

```json
{
  "query_context": {
    "trace_id": "QU-20241103-abc123",
    "original_query": "È valido un contratto firmato da un minorenne nel 2010?",
    "normalized_query": "È valido un contratto firmato da un minorenne nel 2010?",
    "entities": [
      {
        "text": "contratto",
        "type": "LEGAL_OBJECT",
        "start": 11,
        "end": 20,
        "confidence": 0.89
      },
      {
        "text": "minorenne",
        "type": "PERSON",
        "start": 35,
        "end": 44,
        "confidence": 0.93
      },
      {
        "text": "2010",
        "type": "DATE",
        "start": 49,
        "end": 53,
        "confidence": 0.98
      }
    ],
    "concepts": [
      {
        "concept_id": "capacità_agire",
        "label": "Capacità di agire",
        "confidence": 0.91,
        "source": "kg_validated",
        "related_norms": ["art_2_cc", "art_1425_cc"]
      },
      {
        "concept_id": "validità_contratto",
        "label": "Validità del contratto",
        "confidence": 0.88,
        "source": "kg_validated",
        "related_norms": ["art_1325_cc", "art_1418_cc"]
      }
    ],
    "intent": {
      "primary": "validità_atto",
      "secondary": ["requisiti_procedurali"],
      "confidence": {
        "validità_atto": 0.92,
        "requisiti_procedurali": 0.58
      }
    },
    "temporal_scope": {
      "type": "specific_date",
      "reference_date": "2010-01-01",
      "validity_period": "at_date",
      "is_retrospective": true
    },
    "complexity": {
      "score": 0.62,
      "level": "medium",
      "features": {
        "query_length": 54,
        "entity_count": 3,
        "concept_count": 2,
        "temporal_complexity": 0.4,
        "legal_area_count": 1
      }
    },
    "metadata": {
      "language": "it",
      "processing_time_ms": 285,
      "component_trace_ids": {
        "abbreviation": "ABB-20241103-xyz",
        "entity": "ENT-20241103-xyz",
        "concept": "CON-20241103-xyz",
        "intent": "INT-20241103-xyz",
        "temporal": "TMP-20241103-xyz",
        "complexity": "CPX-20241103-xyz"
      }
    }
  }
}
```

**Data Flow Diagram**:

```
┌─────────────┐
│ Raw Query   │
└──────┬──────┘
       │
       ↓ (285ms total)
┌──────────────────────────────────────────┐
│ Stage 1: Abbreviation Expansion (20ms)   │  → expanded_query
└──────┬───────────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│ Stage 2: Entity Extraction (80ms)        │  → entities[]
└──────┬───────────────────────────────────┘
       │
       ↓ (entities passed to stages 3, 4, 5)
       ├──────────────────┬──────────────────┬────────────────┐
       ↓                  ↓                  ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Stage 3:     │  │ Stage 4:     │  │ Stage 5:     │  │ Stage 6:     │
│ Concept      │  │ Intent       │  │ Temporal     │  │ Complexity   │
│ Mapping      │  │ Classifier   │  │ Extraction   │  │ Scoring      │
│ (120ms)      │  │ (25ms)       │  │ (15ms)       │  │ (25ms)       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                  │                  │                  │
       ↓                  ↓                  ↓                  ↓
    concepts[]         intent            temporal_scope    complexity
       │                  │                  │                  │
       └──────────────────┴──────────────────┴──────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  QueryContext       │
                    │  Object Assembly    │
                    └──────────┬──────────┘
                               ↓
                    Output to KG Enrichment
```

**Performance Characteristics**:

| Stage | Latency | Technology | Bottleneck |
|-------|---------|-----------|-----------|
| Abbreviation | 20ms | Regex/spaCy | Dictionary lookup |
| Entity | 80ms | BERT | BERT inference |
| Concept | 120ms | LLM + KG | LLM API call |
| Intent | 25ms | BERT | BERT inference |
| Temporal | 15ms | NER + KB | KB lookup |
| Complexity | 25ms | Random Forest | Feature engineering |
| **Total** | **285ms** | - | LLM call in Concept stage |

**Optimization Strategies**:

1. **Caching**: Cache QueryContext for identical queries (TTL: 1 hour)
2. **Batch Processing**: Batch BERT inferences for Entity + Intent stages
3. **Async LLM**: Use async LLM calls in Concept stage
4. **Model Quantization**: Quantize BERT models for faster inference (Phase 4+)

---

## 4. KG Enrichment Engine

**Reference**: `docs/02-methodology/knowledge-graph.md`, `docs/02-methodology/legal-reasoning.md` §2

The KG Enrichment Engine executes **parallel graph queries** (no LLM) to map concepts to concrete norms and fetch contextual information from the Knowledge Graph.

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    QueryContext (from QU Pipeline)          │
│                  (concepts, entities, intent)               │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │     KG Enrichment Orchestrator        │
        │   (Dispatch 4 parallel Cypher queries)│
        └───────────────────┬───────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
        ↓                                       ↓
┌────────────────┐                    ┌────────────────┐
│ Query 1:       │                    │ Query 2:       │
│ Concept-to-    │  ← NEO4J KG →     │ Related        │
│ Norm Mapping   │                    │ Concepts       │
└────────┬───────┘                    └────────┬───────┘
         │                                      │
         ↓                                      ↓
┌────────────────┐                    ┌────────────────┐
│ Query 3:       │                    │ Query 4:       │
│ Jurisprudence  │                    │ Hierarchical   │
│ Clustering     │                    │ Context        │
└────────┬───────┘                    └────────┬───────┘
         │                                      │
         └──────────────┬───────────────────────┘
                        ↓
                ┌──────────────────┐
                │  EnrichedContext │
                │     Object       │
                └──────────────────┘
```

**Key Characteristics**:
- **Parallel Execution**: 4 queries execute simultaneously
- **No LLM**: Pure graph traversal (fast: ~50ms total)
- **Read-Only**: No graph mutations during retrieval
- **Traceable**: Each query logs execution time + results

---

### 4.1 Concept-to-Norm Mapping

**Purpose**: Map validated concepts to concrete norms that discipline them.

**Cypher Query**:

```cypher
// For each concept in QueryContext.concepts[]
MATCH (c:ConcettoGiuridico {id: $concept_id})-[:DISCIPLINATO_DA]->(n:Norma)
OPTIONAL MATCH (n)-[:HA_VERSIONE]->(v:Versione)
WHERE (v.date_effective <= $reference_date OR v.date_effective IS NULL)
  AND (v.date_end >= $reference_date OR v.date_end IS NULL OR v.is_current = true)
WITH n, v
ORDER BY v.date_effective DESC
RETURN n.id AS norm_id,
       n.article AS article,
       n.source AS source,
       n.title AS title,
       v.id AS version_id,
       v.text AS norm_text,
       v.date_effective AS effective_date
LIMIT 10
```

**Input**:
```json
{
  "concept_id": "validità_contratto",
  "reference_date": "2024-01-01"
}
```

**Output**:
```json
{
  "concept_id": "validità_contratto",
  "mapped_norms": [
    {
      "norm_id": "art_1325_cc",
      "article": "1325",
      "source": "codice civile",
      "title": "Requisiti del contratto",
      "version_id": "art_1325_cc_v1",
      "norm_text": "I requisiti del contratto sono: 1) l'accordo delle parti...",
      "effective_date": "1942-03-16"
    },
    {
      "norm_id": "art_1418_cc",
      "article": "1418",
      "source": "codice civile",
      "title": "Cause di nullità del contratto",
      "version_id": "art_1418_cc_v2",
      "norm_text": "Il contratto è nullo quando...",
      "effective_date": "1942-03-16"
    }
  ],
  "trace_id": "KGE-CON-20241103-abc"
}
```

**Performance**: ~15ms per concept (parallel execution)

---

### 4.2 Related Concepts Discovery

**Purpose**: Discover related concepts via graph traversal to enrich context.

**Cypher Query**:

```cypher
// For each concept in QueryContext.concepts[]
MATCH (c:ConcettoGiuridico {id: $concept_id})-[r:RELAZIONE_CONCETTUALE]-(related:ConcettoGiuridico)
WHERE r.relationship_type IN ['prerequisito', 'conseguenza', 'alternativa', 'eccezione']
RETURN related.id AS related_concept_id,
       related.label AS label,
       related.definition AS definition,
       r.relationship_type AS relationship,
       r.strength AS strength
ORDER BY r.strength DESC
LIMIT 5
```

**Input**:
```json
{
  "concept_id": "validità_contratto"
}
```

**Output**:
```json
{
  "concept_id": "validità_contratto",
  "related_concepts": [
    {
      "related_concept_id": "capacità_agire",
      "label": "Capacità di agire",
      "definition": "Idoneità del soggetto a compiere atti giuridici",
      "relationship": "prerequisito",
      "strength": 0.95
    },
    {
      "related_concept_id": "nullità_contratto",
      "label": "Nullità del contratto",
      "definition": "Invalidità del contratto per difetto di requisiti",
      "relationship": "conseguenza",
      "strength": 0.88
    }
  ],
  "trace_id": "KGE-REL-20241103-abc"
}
```

**Performance**: ~10ms per concept (parallel execution)

---

### 4.3 Jurisprudence Clustering

**Purpose**: Fetch relevant case law from KG (sentenze linked to norms/concepts).

**Cypher Query**:

```cypher
// For each norm in mapped_norms[]
MATCH (n:Norma {id: $norm_id})<-[:INTERPRETA]-(s:AttoGiudiziario)
WHERE s.document_type = 'sentenza'
  AND s.court IN ['Cassazione', 'Corte Costituzionale', 'CGUE']
WITH s
ORDER BY s.date_published DESC
RETURN s.id AS sentenza_id,
       s.court AS court,
       s.date_published AS date,
       s.summary AS summary,
       s.binding_force AS binding_force
LIMIT 5
```

**Input**:
```json
{
  "norm_id": "art_1453_cc"
}
```

**Output**:
```json
{
  "norm_id": "art_1453_cc",
  "jurisprudence": [
    {
      "sentenza_id": "cass_2023_12345",
      "court": "Cassazione",
      "date": "2023-06-15",
      "summary": "Risoluzione per inadempimento: necessaria la gravità...",
      "binding_force": 0.85
    }
  ],
  "trace_id": "KGE-JUR-20241103-abc"
}
```

**Performance**: ~12ms per norm (parallel execution)

---

### 4.4 Hierarchical Context

**Purpose**: Fetch hierarchical context (Costituzione → Legge → Regolamento) for norms.

**Cypher Query**:

```cypher
// For each norm in mapped_norms[]
MATCH path = (parent:Norma)-[:GERARCHIA_KELSENIANA*1..3]->(n:Norma {id: $norm_id})
WHERE parent.hierarchical_level IN ['Costituzione', 'Legge Costituzionale']
RETURN parent.id AS parent_norm_id,
       parent.article AS parent_article,
       parent.source AS parent_source,
       parent.hierarchical_level AS level,
       length(path) AS distance
ORDER BY distance ASC
LIMIT 3
```

**Input**:
```json
{
  "norm_id": "art_1453_cc"
}
```

**Output**:
```json
{
  "norm_id": "art_1453_cc",
  "hierarchical_context": [
    {
      "parent_norm_id": "art_24_cost",
      "parent_article": "24",
      "parent_source": "Costituzione",
      "level": "Costituzione",
      "distance": 2
    }
  ],
  "trace_id": "KGE-HIE-20241103-abc"
}
```

**Performance**: ~13ms per norm (parallel execution)

---

### 4.5 KG Enrichment Integration

**Output Schema** (EnrichedContext object):

```json
{
  "enriched_context": {
    "trace_id": "KGE-20241103-abc123",
    "concepts_enriched": [
      {
        "concept_id": "validità_contratto",
        "mapped_norms": [
          {
            "norm_id": "art_1325_cc",
            "article": "1325",
            "source": "codice civile",
            "title": "Requisiti del contratto",
            "version_id": "art_1325_cc_v1",
            "norm_text": "I requisiti del contratto sono...",
            "effective_date": "1942-03-16"
          }
        ],
        "related_concepts": [
          {
            "related_concept_id": "capacità_agire",
            "label": "Capacità di agire",
            "relationship": "prerequisito",
            "strength": 0.95
          }
        ],
        "jurisprudence": [
          {
            "sentenza_id": "cass_2023_12345",
            "court": "Cassazione",
            "date": "2023-06-15",
            "summary": "Risoluzione per inadempimento...",
            "binding_force": 0.85
          }
        ],
        "hierarchical_context": [
          {
            "parent_norm_id": "art_24_cost",
            "parent_article": "24",
            "parent_source": "Costituzione",
            "level": "Costituzione",
            "distance": 2
          }
        ]
      }
    ],
    "metadata": {
      "processing_time_ms": 48,
      "queries_executed": 4,
      "kg_nodes_traversed": 127,
      "component_trace_ids": {
        "concept_to_norm": "KGE-CON-20241103-xyz",
        "related_concepts": "KGE-REL-20241103-xyz",
        "jurisprudence": "KGE-JUR-20241103-xyz",
        "hierarchical": "KGE-HIE-20241103-xyz"
      }
    }
  }
}
```

**Data Flow**:

```
QueryContext (from QU Pipeline)
   ↓
┌──────────────────────────────────────┐
│ KG Enrichment Orchestrator           │
│ - Parse concepts from QueryContext   │
│ - Dispatch 4 parallel queries        │
│ - Aggregate results                  │
└──────────────────┬───────────────────┘
                   ↓
         Parallel Cypher Queries
         (4 queries × N concepts)
                   ↓
┌──────────────────────────────────────┐
│ Neo4j Graph Database                 │
│ - Execute read-only queries          │
│ - Return JSON results                │
└──────────────────┬───────────────────┘
                   ↓
         Result Aggregation
         (Combine into EnrichedContext)
                   ↓
    Output to Orchestration Layer
```

**Performance Characteristics**:

| Query Type | Latency | Complexity | Optimization |
|-----------|---------|-----------|-------------|
| Concept-to-Norm | 15ms | O(concepts × norms) | Index on concept_id |
| Related Concepts | 10ms | O(concepts × relations) | Index on relationship_type |
| Jurisprudence | 12ms | O(norms × sentenze) | Index on court + date |
| Hierarchical | 13ms | O(norms × depth) | Index on hierarchical_level |
| **Total (parallel)** | **~50ms** | - | Parallel execution |

---

## 5. Technology Mapping

### 5.1 Query Understanding Components

| Component | Abstract Interface | Technology Options | Recommended (Phase 2+) | Rationale |
|-----------|-------------------|-------------------|----------------------|-----------|
| **Abbreviation Expansion** | Text normalization service | • Regex + Dictionary<br>• spaCy PhraseMatcher<br>• Custom ML model | **spaCy PhraseMatcher** | Fast, battle-tested, low latency |
| **Entity Extraction** | NER service with BIO tagging | • spaCy it_core_news_lg<br>• dbmdz/bert-base-italian-cased<br>• Fine-tuned BERT | **Fine-tuned BERT** | Highest accuracy for Italian legal entities |
| **Concept Mapping (LLM)** | LLM inference service | • GPT-4o-mini<br>• GPT-4o<br>• Claude Sonnet<br>• Local fine-tuned | **GPT-4o-mini** (Phase 2)<br>**GPT-4o** (Phase 3+) | Balance cost/accuracy |
| **Concept Mapping (KG)** | Graph database | • Neo4j<br>• AWS Neptune<br>• TigerGraph | **Neo4j** | Best Cypher support, mature ecosystem |
| **Intent Classifier** | Multi-label classifier | • TF-IDF + Logistic Regression<br>• BERT fine-tuned<br>• SetFit | **BERT fine-tuned** | Best accuracy for multi-label |
| **Temporal Extraction** | Date NER + KB | • spaCy DateParser<br>• BERT NER<br>• Custom KB | **BERT NER + Custom KB** | Legal-specific events require custom KB |
| **Complexity Scoring** | ML regression model | • Rule-based<br>• Random Forest<br>• XGBoost | **Random Forest** | Good accuracy, fast inference, interpretable |

### 5.2 KG Enrichment Components

| Component | Abstract Interface | Technology Options | Recommended | Rationale |
|-----------|-------------------|-------------------|------------|-----------|
| **Graph Database** | Property graph with Cypher | • Neo4j<br>• AWS Neptune<br>• JanusGraph | **Neo4j** | Industry standard, best tooling |
| **Query Orchestrator** | Async query dispatcher | • Python asyncio<br>• Celery<br>• Custom | **Python asyncio** | Native async support, low overhead |
| **Caching Layer** | Query result cache | • Redis<br>• Memcached<br>• Local LRU | **Redis** | Persistent, fast, supports TTL |

### 5.3 Infrastructure

| Component | Abstract Interface | Technology Options | Recommended | Rationale |
|-----------|-------------------|-------------------|------------|-----------|
| **API Framework** | Async HTTP server | • FastAPI<br>• Flask + Gunicorn<br>• Django | **FastAPI** | Async, OpenAPI auto-gen, type hints |
| **Message Queue** | Async task queue | • Celery + RabbitMQ<br>• Redis Queue<br>• AWS SQS | **Celery + RabbitMQ** | Mature, scalable, retry logic |
| **Observability** | Logging + Metrics | • Prometheus + Grafana<br>• ELK Stack<br>• DataDog | **Prometheus + Grafana** | Open-source, Docker-friendly |

---

## 6. Docker Compose Architecture

### 6.1 Service Definitions

```yaml
version: '3.8'

services:
  # Query Understanding Service
  query-understanding:
    build: ./services/query-understanding
    ports:
      - "8001:8000"
    environment:
      - MODEL_PATH=/models
      - LLM_API_KEY=${OPENAI_API_KEY}
      - NEO4J_URI=bolt://neo4j:7687
    volumes:
      - ./models:/models
    depends_on:
      - neo4j
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # KG Enrichment Service
  kg-enrichment:
    build: ./services/kg-enrichment
    ports:
      - "8002:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - REDIS_URI=redis://redis:6379
    depends_on:
      - neo4j
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Neo4j Knowledge Graph
  neo4j:
    image: neo4j:5.13-enterprise
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_initial__size=2G
      - NEO4J_dbms_memory_heap_max__size=4G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  neo4j_data:
  neo4j_logs:
  redis_data:
```

### 6.2 Network Topology

```
┌──────────────────────────────────────────────────────┐
│               Docker Bridge Network                  │
│                  (merl-t-network)                    │
│                                                      │
│  ┌──────────────────┐         ┌──────────────────┐ │
│  │ query-           │         │ kg-              │ │
│  │ understanding    │────────▶│ enrichment       │ │
│  │ :8001            │         │ :8002            │ │
│  └────────┬─────────┘         └────────┬─────────┘ │
│           │                             │           │
│           │ Neo4j Bolt (7687)          │           │
│           ├─────────────────────────────┤           │
│           │                             │           │
│           ↓                             ↓           │
│  ┌──────────────────┐         ┌──────────────────┐ │
│  │ neo4j            │         │ redis            │ │
│  │ :7474, :7687     │         │ :6379            │ │
│  └──────────────────┘         └──────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘

External Access:
- Query Understanding API: http://localhost:8001
- KG Enrichment API: http://localhost:8002
- Neo4j Browser: http://localhost:7474
- Redis: redis://localhost:6379
```

### 6.3 Service Communication

| Source | Target | Protocol | Port | Purpose |
|--------|--------|---------|------|---------|
| query-understanding | neo4j | Bolt | 7687 | Concept validation (Step 2 of Concept Mapping) |
| query-understanding | redis | Redis | 6379 | Query caching |
| kg-enrichment | neo4j | Bolt | 7687 | All graph queries (4 parallel queries) |
| kg-enrichment | redis | Redis | 6379 | Result caching |
| External | query-understanding | HTTP | 8001 | API requests |
| External | kg-enrichment | HTTP | 8002 | API requests (usually from Orchestration Layer) |

---

## 7. Error Handling & Resilience

### 7.1 Error Propagation Strategy

**Principle**: **Non-blocking errors** - Components degrade gracefully without stopping the pipeline.

```
┌───────────────────────────────────────────────────────────┐
│ Error Severity Classification                             │
├───────────────────────────────────────────────────────────┤
│ CRITICAL: Stop pipeline, return error to user             │
│   - Neo4j database unreachable                            │
│   - All BERT models fail to load                          │
│                                                           │
│ WARNING: Degrade gracefully, log + continue               │
│   - Entity extraction low confidence → Include entities   │
│   - Concept mapping no LLM candidates → Skip concepts     │
│   - KG query timeout → Return partial results             │
│                                                           │
│ INFO: Expected edge case, handle silently                │
│   - No temporal reference → Default to current            │
│   - Low complexity score → Default to medium (0.5)        │
└───────────────────────────────────────────────────────────┘
```

### 7.2 Retry Logic

**Query Understanding Components**:
- **BERT Inference**: Retry 2 times with exponential backoff (100ms, 200ms)
- **LLM API Call** (Concept Mapping): Retry 3 times with exponential backoff (1s, 2s, 4s)
- **Neo4j Query** (Concept Validation): Retry 2 times with 500ms delay

**KG Enrichment**:
- **Cypher Query**: Retry 2 times with 200ms delay
- **Connection Pool**: Maintain 10 connections, recreate on failure

### 7.3 Circuit Breaker Pattern

```json
{
  "circuit_breaker_config": {
    "component": "concept_mapping_llm",
    "failure_threshold": 5,
    "timeout_seconds": 10,
    "reset_timeout_seconds": 60
  }
}
```

**States**:
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Failures exceed threshold, reject requests immediately (return empty concepts)
- **HALF_OPEN**: After reset timeout, allow 1 test request

### 7.4 Fallback Strategies

| Component | Primary | Fallback 1 | Fallback 2 |
|-----------|---------|-----------|-----------|
| **Entity Extraction** | Fine-tuned BERT | spaCy it_core_news_lg | Regex patterns |
| **Concept Mapping (LLM)** | GPT-4o | GPT-4o-mini | Skip concepts (empty array) |
| **Concept Validation (KG)** | Neo4j Cypher | Cached results | Skip validation |
| **Intent Classification** | BERT classifier | Rule-based (keywords) | Default: "interpretazione_norma" |
| **Complexity Scoring** | Random Forest | Rule-based heuristic | Default: 0.5 (medium) |

---

## 8. Performance Characteristics

### 8.1 Latency Breakdown

```
Total Preprocessing Latency: ~335ms (P95)

┌─────────────────────────────────────────────────────┐
│ Query Understanding: 285ms                          │
│ ├─ Abbreviation: 20ms                               │
│ ├─ Entity Extraction: 80ms                          │
│ ├─ Concept Mapping: 120ms (LLM bottleneck)          │
│ ├─ Intent Classification: 25ms                      │
│ ├─ Temporal Extraction: 15ms                        │
│ └─ Complexity Scoring: 25ms                         │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ KG Enrichment: 50ms (parallel queries)              │
│ ├─ Concept-to-Norm: 15ms                            │
│ ├─ Related Concepts: 10ms                           │
│ ├─ Jurisprudence: 12ms                              │
│ └─ Hierarchical: 13ms                               │
└─────────────────────────────────────────────────────┘
```

### 8.2 Throughput

| Metric | Value | Conditions |
|--------|-------|-----------|
| **Requests/sec** | 15 req/s | Single instance, no caching |
| **Requests/sec** | 80 req/s | Single instance, 70% cache hit rate |
| **Requests/sec** | 300 req/s | 5 instances (horizontal scaling) |

### 8.3 Resource Requirements

**Query Understanding Service** (per instance):
- CPU: 2 cores
- RAM: 4GB (BERT models loaded)
- Storage: 2GB (models)

**KG Enrichment Service** (per instance):
- CPU: 1 core
- RAM: 1GB
- Storage: 100MB

**Neo4j**:
- CPU: 4 cores
- RAM: 8GB (heap: 4GB)
- Storage: 50GB (KG data)

**Redis**:
- CPU: 1 core
- RAM: 2GB
- Storage: 10GB (AOF persistence)

---

## 9. Cross-References

### Section 02 Methodology
- **Query Understanding**: `docs/02-methodology/query-understanding.md`
  - §3: 6-Stage Pipeline (Abbreviation → Entity → Concept → Intent → Temporal → Complexity)
  - §4: Adaptive Components & RLCF Integration
  - §5: QueryContext Output Schema

- **Knowledge Graph**: `docs/02-methodology/knowledge-graph.md`
  - §2: KG Schema (23 node types, 65 relationships)
  - §3: Graph Query Patterns (Concept-to-Norm, Hierarchical Traversal)
  - §4: Multivigenza Support (Temporal Versioning)

- **Legal Reasoning**: `docs/02-methodology/legal-reasoning.md`
  - §2: Query Understanding → KG Enrichment → Router flow
  - §5: QueryContext + EnrichedContext as Router inputs

### Section 03 Architecture (next docs)
- **Orchestration Layer**: `docs/03-architecture/02-orchestration-layer.md`
  - LLM Router consumes QueryContext + EnrichedContext from Preprocessing Layer

### Section 04 Implementation
- **Query Understanding Service**: `docs/04-implementation/query-understanding-service.md` (future)
- **KG Enrichment Service**: `docs/04-implementation/kg-enrichment-service.md` (future)

---

## 10. Appendices

### A. Observability

**Logging**:
- **Format**: JSON structured logs
- **Fields**: `trace_id`, `component`, `timestamp`, `level`, `message`, `metadata`
- **Aggregation**: ELK Stack or Grafana Loki

**Metrics**:
- **Latency**: Per-component latency histograms (P50, P95, P99)
- **Throughput**: Requests per second per component
- **Errors**: Error rate by component and error type
- **Cache**: Cache hit rate for Redis

**Tracing**:
- **Format**: OpenTelemetry
- **Propagation**: trace_id propagated through all components
- **Spans**: One span per stage + sub-spans for LLM/Neo4j calls

### B. Security

**Authentication**:
- **Internal services**: Mutual TLS between services
- **External API**: JWT bearer tokens

**Authorization**:
- **Query Understanding**: Public access (no PII in queries)
- **KG Enrichment**: Internal-only (not exposed externally)

**Data Protection**:
- **PII**: No PII stored in queries (anonymized before storage)
- **Secrets**: Environment variables, never hardcoded

### C. Scalability

**Horizontal Scaling**:
- **Query Understanding**: Stateless, can scale to N instances behind load balancer
- **KG Enrichment**: Stateless, can scale to N instances
- **Neo4j**: Single-writer, read replicas for scaling reads
- **Redis**: Cluster mode for horizontal scaling

**Vertical Scaling**:
- **BERT Models**: Quantization reduces RAM (4GB → 2GB)
- **Neo4j**: Increase heap size for larger graphs

---

**Document Version**: 1.0
**Last Updated**: 2024-11-03
**Status**: ✅ Complete
