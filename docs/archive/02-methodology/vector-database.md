# Vector Database Architecture

## Table of Contents
1. [Introduction](#introduction)
2. [Architectural Role](#architectural-role)
3. [Metadata Schema Design](#metadata-schema-design)
4. [Embedding Strategy Architecture](#embedding-strategy-architecture)
5. [Retrieval Pattern Catalog](#retrieval-pattern-catalog)
6. [Performance Optimization Patterns](#performance-optimization-patterns)
7. [Integration Protocols](#integration-protocols)
8. [Agent Interface Protocol](#agent-interface-protocol)
9. [Technology Selection Framework](#technology-selection-framework)
10. [Validation Examples](#validation-examples)
11. [Evolution & RLCF Integration](#evolution--rlcf-integration)
12. [Summary](#summary)

---

## Introduction

The Vector Database is a critical component of MERL-T that enables **semantic search** over legal text. While the Knowledge Graph provides structured relationships between legal entities (norms, articles, cases, concepts), the Vector Database enables **similarity-based retrieval** of relevant text passages based on meaning rather than exact keyword matches.

### Core Capabilities

1. **Semantic Search**: Find legally relevant passages even when exact terminology differs
2. **Rich Metadata Filtering**: Temporal queries, hierarchical filtering, legal domain constraints
3. **Hybrid Retrieval**: Combine semantic similarity with keyword matching for precision
4. **Scalability**: Handle millions of text chunks with sub-second query times
5. **Flexible Schema**: Support diverse document types (norme, sentenze, dottrina) with unified metadata

### Complementary to Knowledge Graph

The Vector Database and Knowledge Graph serve **complementary roles**:

| Aspect | Knowledge Graph | Vector Database |
|--------|----------------|-----------------|
| **Primary Function** | Structured relationships | Semantic similarity |
| **Query Type** | "What modifies this norm?" | "What discusses this concept?" |
| **Data Structure** | Nodes + edges | Text chunks + embeddings |
| **Reasoning Type** | Logical traversal | Similarity-based retrieval |
| **Temporal Handling** | Explicit version nodes | Metadata filtering |
| **Best For** | Precise relationships | Open-ended research |

**Example Query**: "È valido un contratto firmato da un minorenne?"

**Knowledge Graph retrieval**:
- Precise article retrieval: Art. 2 c.c., Art. 322 c.c., Art. 1442 c.c.
- Explicit norm relationships: modifies, abrogates, implements

**Vector Database retrieval**:
- Case law discussing minor contracts (semantic similarity)
- Doctrinal commentary on capacity (conceptual relevance)
- Legal scholarship on voidable contracts (contextual enrichment)

### Design Principles

1. **Technology-Agnostic**: Architecture independent of specific vector DB implementation
2. **Adaptive Evolution**: Embedding models improve through RLCF feedback
3. **Metadata-Rich**: Unified schema supports heterogeneous legal sources
4. **Performance-Oriented**: Sub-second retrieval at scale through optimization patterns
5. **Agent-Orchestrated**: Accessed through VectorDB Agent, coordinated by LLM Router

---

## Architectural Role

### Position in MERL-T Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    MERL-T Query Pipeline                     │
└─────────────────────────────────────────────────────────────┘

User Query
    ↓
┌──────────────────────────────────────────┐
│ Query Understanding                      │
│ (normalize, extract entities, complexity)│
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ LLM Router (100% LLM-Based)              │
│ Decision: KG? VectorDB? Both? API?      │
│ Output: Execution plan with task schemas│
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────────┐
│              Parallel Retrieval                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │ KG Agent       │  │ VectorDB Agent │  │ API Agent  │ │
│  │ (structured)   │  │ (semantic)     │  │ (external) │ │
│  └────────────────┘  └────────────────┘  └────────────┘ │
└──────────────┬───────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ Expert LLMs (Principles, Rules, Cases)   │
│ Context: combined KG + VectorDB results  │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ Synthesizer (unified answer)             │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│ RLCF Loop (community feedback)           │
│ Refine: routing, retrieval, embeddings   │
└──────────────────────────────────────────┘
```

### When Vector Database is Activated

The **LLM Router** determines VectorDB Agent activation based on query characteristics:

| Query Pattern | VectorDB Activation | Rationale |
|---------------|---------------------|-----------|
| **Research queries** | ✅ High priority | Broad semantic coverage needed across doctrinal sources |
| **Case law retrieval** | ✅ High priority | Semantic similarity finds relevant jurisprudence despite terminology variations |
| **Doctrinal commentary** | ✅ High priority | Conceptual discussions require semantic understanding |
| **Precise article lookup** | ⚠️ Secondary | KG better for exact norm references, VectorDB for contextual enrichment |
| **Temporal queries** | ✅ With filters | Metadata filtering isolates correct norm versions |
| **Ambiguous queries** | ✅ High priority | Semantic search compensates for underspecified entities |
| **Definition queries** | ⚠️ Hybrid | KG for norm text, VectorDB for doctrinal explanations |

**Decision Logic** (Router output schema):

```json
{
  "execution_plan": {
    "agents": [
      {
        "agent_type": "vectordb_agent",
        "priority": "high",
        "task": {
          "retrieval_strategy": "semantic_search",
          "query_normalized": "È valido un contratto firmato da un minorenne?",
          "filters": {
            "temporal_metadata.is_current": true,
            "classification.legal_area": "civil",
            "document_type": ["norm", "jurisprudence"]
          },
          "top_k": 20,
          "rerank": true
        }
      },
      {
        "agent_type": "kg_agent",
        "priority": "high",
        "task": {
          "cypher_template": "capacity_norms_query",
          "entities": ["capacità_di_agire", "contratto", "minorenne"]
        }
      }
    ],
    "execution_mode": "parallel"
  }
}
```

### Use Case Taxonomy

**Category 1: Research Queries**
- Pattern: "Quali sono le principali modifiche allo smart working dal 2020?"
- Strategy: Multi-query retrieval with broad temporal filters
- Expected Sources: Norms + jurisprudence + doctrine
- Top-k: 30-50 chunks

**Category 2: Case Law Retrieval**
- Pattern: "Ci sono precedenti su contratti firmati da minori?"
- Strategy: Semantic search with case law filter
- Expected Sources: Sentenze (court decisions)
- Top-k: 15-20 chunks

**Category 3: Doctrinal Commentary**
- Pattern: "Cosa dice la dottrina sulla simulazione contrattuale?"
- Strategy: Semantic search with doctrine filter
- Expected Sources: Legal scholarship, textbooks, articles
- Top-k: 20-30 chunks

**Category 4: Contextual Enrichment**
- Pattern: Complex query requiring both KG structure and VectorDB context
- Strategy: Hybrid retrieval → KG enrichment with VectorDB passages
- Expected Sources: All types
- Top-k: 10-15 chunks (focused context)

**Category 5: Temporal-Constrained Queries**
- Pattern: "Cosa stabiliva il DL 18/2020 sullo smart working il 15 marzo 2020?"
- Strategy: Temporal filtered search with exact date range
- Expected Sources: Norms (specific version)
- Top-k: 5-10 chunks (precision over recall)

---

## Metadata Schema Design

### Unified Chunk Schema

Every text chunk stored in the Vector Database follows a **unified metadata schema** that supports heterogeneous legal sources while maintaining queryability:

```json
{
  "chunk_id": "uuid",
  "doc_id": "hash",

  "text": "string (500-1500 tokens)",
  "embedding": [
    "array of floats (1536 or 3072 dimensions)",
    "generated by embedding model (Phase 1-5)"
  ],

  "document_type": "norm | jurisprudence | doctrine",

  "temporal_metadata": {
    "date_published": "ISO-8601",
    "date_effective": "ISO-8601",
    "date_end": "ISO-8601 | null",
    "is_current": "boolean"
  },

  "classification": {
    "legal_area": "civil | penal | administrative | constitutional | labor",
    "legal_domain_tags": ["contratti", "nullità", "capacità"],
    "complexity_level": "basic | intermediate | advanced"
  },

  "authority_metadata": {
    "source_type": "primary_legislation | case_law | doctrine | commentary",
    "hierarchical_level": "integer (1=Costituzione, 2=Legge, 3=Regolamento, etc.)",
    "binding_force": "mandatory | persuasive | informational",
    "authority_score": "float (0-1, RLCF-calculated)",
    "citation_count": "integer"
  },

  "kg_links": {
    "primary_article_id": "uuid | null",
    "referenced_norm_ids": ["uuid"],
    "referenced_case_ids": ["uuid"],
    "related_concept_ids": ["uuid"]
  },

  "entities_extracted": {
    "norm_references": [
      {"type": "article", "article": "2", "code": "cc", "text": "art. 2 c.c."}
    ],
    "case_references": [
      {"court": "Cassazione", "number": "18210", "year": "2015"}
    ],
    "legal_concepts": ["capacità di agire", "annullabilità"],
    "parties": []
  },

  "source_metadata": {
    "norm_metadata": {
      "frbrwork_uri": "string (Akoma Ntoso URI)",
      "publication_gazette": "string"
    },
    "jurisprudence_metadata": {
      "court_name": "Corte di Cassazione",
      "chamber": "Sezione I Civile",
      "case_number": "18210/2015"
    },
    "doctrine_metadata": {
      "author": "string",
      "publication_title": "string",
      "publisher": "string",
      "isbn": "string"
    }
  },

  "chunking_metadata": {
    "chunk_index": "integer (0-indexed)",
    "total_chunks": "integer",
    "chunk_strategy": "semantic | fixed | hybrid",
    "semantic_coherence_score": "float (0-1)"
  },

  "retrieval_metadata": {
    "keyword_boost_terms": ["contratto", "minorenne", "capacità"],
    "retrieval_priority": "float (0-1, usage-based)",
    "last_retrieved": "ISO-8601"
  }
}
```

### Schema Inheritance from Data Ingestion

Metadata flows from data-ingestion pipeline to Vector Database:

| Data Ingestion Stage | Vector DB Field | Source |
|----------------------|-----------------|--------|
| Akoma Ntoso parsing | `source_metadata.frbrwork_uri` | XML/JSON parser |
| Temporal tracking | `temporal_metadata.*` | Multivigenza extractor |
| Entity extraction | `entities_extracted.*` | NER pipeline (BERT fine-tuned) |
| KG population | `kg_links.*` | Neo4j node IDs |
| Authority calculation | `authority_metadata.authority_score` | RLCF citation analysis |
| Semantic chunking | `chunking_metadata.*` | Chunking algorithm |

### Schema Flexibility

The unified schema supports **document type polymorphism**:

```
┌─────────────────────────────────────────────────┐
│         All Document Types (Required Fields)    │
├─────────────────────────────────────────────────┤
│ • chunk_id, text, embedding                     │
│ • document_type                                 │
│ • temporal_metadata                             │
│ • classification                                │
│ • authority_metadata                            │
└─────────────────────────────────────────────────┘
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
┌─────────┐   ┌──────────────┐  ┌──────────┐
│ Norms   │   │Jurisprudence │  │ Doctrine │
├─────────┤   ├──────────────┤  ├──────────┤
│+ Akoma  │   │+ Court info  │  │+ Author  │
│  Ntoso  │   │+ Chamber     │  │+ ISBN    │
│+ Gazette│   │+ Case number │  │+ Publisher│
└─────────┘   └──────────────┘  └──────────┘
```

**Query Interface**: All document types queryable through unified filter syntax, regardless of source-specific metadata.

### Metadata Validation Rules

| Field | Constraint | Validation Rule |
|-------|-----------|-----------------|
| `temporal_metadata.date_effective` | Required for norms | Must be ≤ current date |
| `temporal_metadata.date_end` | Optional | If present, must be ≥ date_effective |
| `temporal_metadata.is_current` | Required | Auto-calculated: (date_end == null OR date_end ≥ today) |
| `classification.legal_area` | Required | Must be in controlled vocabulary |
| `authority_metadata.hierarchical_level` | Required | Integer 1-5 (Kelsenian hierarchy) |
| `kg_links.primary_article_id` | Optional | If present, must exist in Neo4j KG |
| `entities_extracted.*` | Optional | Must match data-ingestion.md schema |
| `embedding` | Required | Array length must match model dimension (1536 or 3072) |

---

## Embedding Strategy Architecture

### Bootstrap Evolution Model

MERL-T follows a **phased evolution strategy** for embedding models, progressing from generic to specialized as RLCF data accumulates:

```
┌──────────────────────────────────────────────────────────┐
│            EMBEDDING MODEL EVOLUTION PHASES               │
└──────────────────────────────────────────────────────────┘

PHASE 1: Generic Multilingual Embeddings
┌──────────────────────────────────────┐
│ Model: OpenAI text-embedding-3-large │
│ Dimensions: 3072                     │
│ Training: Off-the-shelf              │
│ Italian Support: ✅ Multilingual      │
│ Legal Domain: ❌ General purpose     │
│ Duration: Months 1-3                 │
└──────────────┬───────────────────────┘
               ↓ (Collect RLCF data)

PHASE 2: RLCF Data Collection
┌──────────────────────────────────────┐
│ Collect query-document pairs         │
│ Track user feedback on relevance     │
│ Build training dataset:               │
│  • Positive pairs (query → relevant) │
│  • Hard negatives (similar but wrong)│
│ Target: 10K-50K labeled pairs        │
│ Duration: Months 2-6                 │
└──────────────┬───────────────────────┘
               ↓ (Sufficient data)

PHASE 3: Fine-Tuned Italian Legal Embeddings
┌──────────────────────────────────────┐
│ Base: multilingual-e5-large          │
│ Fine-tune: Contrastive learning      │
│ Training Data: RLCF query-doc pairs  │
│ Legal Corpus: Italian norms + cases  │
│ Expected Improvement: +15-20% recall │
│ Duration: Months 6-12                │
└──────────────┬───────────────────────┘
               ↓ (Optimize efficiency)

PHASE 4: Domain-Specific Embeddings
┌──────────────────────────────────────┐
│ Specialization: Civil vs Penal law   │
│ Multi-model approach or shared base  │
│ Enhanced domain terminology          │
│ Expected Improvement: +10-15% precision│
│ Duration: Months 12-18               │
└──────────────┬───────────────────────┘
               ↓ (Deployment optimization)

PHASE 5: Distilled Small Models
┌──────────────────────────────────────┐
│ Knowledge Distillation: Large → Small│
│ Dimensions: 768 (4x reduction)       │
│ Self-hosted deployment               │
│ Inference: 3-5x faster               │
│ Quality: 90-95% of large model       │
│ Duration: Months 18+                 │
└──────────────────────────────────────┘
```

### Phase Transition Criteria

| From Phase | To Phase | Trigger Criteria | Validation Metrics |
|------------|----------|------------------|-------------------|
| 1 → 2 | 2 → 3 | • 10K+ labeled query-doc pairs<br>• User feedback rate >30%<br>• Baseline metrics established | • A/B test: fine-tuned vs generic<br>• Recall improvement ≥15%<br>• User satisfaction delta ≥0.3 |
| 2 → 3 | 3 → 4 | • Phase 3 deployed for 6+ months<br>• Domain-specific gaps identified<br>• 50K+ labeled pairs per domain | • Domain-specific recall ≥85%<br>• Cross-domain performance stable<br>• Latency acceptable |
| 3 → 4 | 4 → 5 | • Infrastructure cost optimization needed<br>• Self-hosting capability available<br>• Quality threshold achieved | • Distilled model quality ≥90% of large<br>• Inference latency <50ms p95<br>• Cost reduction ≥60% |

### Model Selection Decision Matrix

**Phase 1 Options**:

| Model | Dimensions | Cost (per 1M tokens) | Italian Quality | Legal Domain | Deployment |
|-------|-----------|---------------------|-----------------|--------------|------------|
| `text-embedding-3-large` | 3072 | $0.13 | ⭐⭐⭐⭐ | ⭐⭐ | API |
| `text-embedding-3-small` | 1536 | $0.02 | ⭐⭐⭐ | ⭐⭐ | API |
| `multilingual-e5-large` | 1024 | Free (self-hosted) | ⭐⭐⭐⭐ | ⭐⭐ | Self-hosted |
| `multilingual-e5-base` | 768 | Free (self-hosted) | ⭐⭐⭐ | ⭐⭐ | Self-hosted |

**Recommendation Phase 1**: `text-embedding-3-large`
- Rationale: Best quality for initial deployment, API ease, acceptable cost at early scale
- Trade-off: Higher cost at scale → Phase 5 distillation addresses this

**Phase 3+ Fine-Tuning Strategy**:

```json
{
  "training_objective": "contrastive_learning",
  "training_data_schema": {
    "anchor": "user_query (Italian legal question)",
    "positive": "relevant_chunk (high user satisfaction)",
    "hard_negative": "topically_similar_but_irrelevant_chunk"
  },
  "data_sources": [
    "RLCF query-document pairs with positive feedback",
    "Norm citations in case law (explicit relevance)",
    "Expert-curated legal concept mappings"
  ],
  "expected_improvements": {
    "terminology_precision": "annullabilità vs nullità distinction",
    "temporal_awareness": "distinguish norms by validity period",
    "domain_specialization": "civil law vs penal law semantics"
  }
}
```

### Embedding Generation Protocol

**Input Schema**:
```json
{
  "text": "string (chunk text or query)",
  "context_metadata": {
    "document_type": "norm | jurisprudence | doctrine",
    "legal_area": "civil | penal | administrative",
    "is_query": "boolean (true for user query, false for chunk)"
  }
}
```

**Processing Logic**:
```
┌──────────────────────────────────────┐
│ 1. Text Preprocessing                │
│    • Normalize whitespace            │
│    • Preserve legal terminology      │
│    • NO lowercasing (Art. vs art.)   │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ 2. Context Enrichment (Phase 3+)    │
│    IF fine-tuned model:              │
│      Prepend metadata for context    │
│      "Tipo: norm | Area: civil"      │
│    ELSE:                             │
│      Use raw text                    │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ 3. Model Inference                   │
│    • Pass to embedding model         │
│    • Generate dense vector           │
│    • Dimensions: 768-3072            │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ 4. Normalization (Optional)          │
│    • L2 normalization for cosine     │
│    • Vector quantization if Phase 5  │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ 5. Return Embedding Vector           │
│    Output: [0.023, -0.089, ...]      │
└──────────────────────────────────────┘
```

**Output Schema**:
```json
{
  "embedding": [
    "array of floats, length 768-3072"
  ],
  "model_version": "phase_1_text_embedding_3_large | phase_3_finetuned_v2",
  "generation_timestamp": "ISO-8601"
}
```

### RLCF Integration Points

**Feedback Loop Architecture**:

```
User Interaction
    ↓
┌──────────────────────────────────────┐
│ User rates retrieval quality         │
│ • Relevant: thumbs up                │
│ • Irrelevant: thumbs down            │
│ • Missing: suggest better result     │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Aggregate Feedback (Weekly)          │
│ • Build query-document pairs         │
│ • Identify hard negatives            │
│ • Calculate embedding drift          │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Model Update Decision                │
│ IF drift > threshold:                │
│   Trigger fine-tuning cycle          │
│ ELSE:                                │
│   Continue monitoring                │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Fine-Tuning Cycle (Monthly)          │
│ • Train on new RLCF data             │
│ • A/B test new model vs current      │
│ • Gradual rollout if successful      │
└──────────────────────────────────────┘
```

**Training Data Schema**:
```json
{
  "training_triplet": {
    "anchor": "È valido un contratto firmato da un minorenne di 16 anni?",
    "positive": {
      "chunk_id": "uuid",
      "text": "Art. 2 c.c. - La maggiore età è fissata al compimento del diciottesimo anno...",
      "user_feedback_score": 0.95
    },
    "hard_negative": {
      "chunk_id": "uuid",
      "text": "Art. 1325 c.c. - I requisiti del contratto sono: 1) accordo delle parti...",
      "similarity_to_anchor": 0.78,
      "user_feedback_score": 0.15
    }
  }
}
```

---

## Retrieval Pattern Catalog

### Pattern Taxonomy

MERL-T defines **6 core retrieval patterns** for Vector Database queries, each optimized for specific use cases:

| Pattern ID | Name | Use Case | Complexity | Recall Priority |
|------------|------|----------|------------|-----------------|
| P1 | Semantic Search | Conceptual similarity queries | Low | High |
| P2 | Hybrid Search | Balanced keyword + semantic | Medium | Very High |
| P3 | Filtered Retrieval | Constrained by metadata | Medium | Medium |
| P4 | Reranked Retrieval | Two-stage precision boost | High | High |
| P5 | Multi-Query Retrieval | Multiple query variations | High | Very High |
| P6 | Cross-Modal Retrieval | Enrich with KG traversal | Very High | Medium |

### P1: Semantic Search Pattern

**Objective**: Retrieve chunks by semantic similarity to query, regardless of keyword overlap.

**Input Schema**:
```json
{
  "query": "È valido un contratto firmato da un minorenne?",
  "top_k": 20,
  "filters": {
    "temporal_metadata.is_current": true,
    "classification.legal_area": "civil"
  }
}
```

**Processing Logic**:
```
┌──────────────────────────────────────┐
│ Step 1: Query Embedding Generation   │
│   Input: query string                │
│   Output: query_vector [3072 dims]   │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Step 2: Filter Expression Build      │
│   Parse filters dict                 │
│   Construct metadata constraints     │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Step 3: Vector Similarity Search     │
│   Metric: cosine similarity          │
│   Index: HNSW approximate NN         │
│   Apply filters during search        │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Step 4: Rank & Return                │
│   Sort by: similarity DESC           │
│   Limit: top_k results               │
│   Return with metadata               │
└──────────────────────────────────────┘
```

**Output Schema**:
```json
{
  "results": [
    {
      "chunk_id": "uuid-1",
      "text": "Art. 2 c.c. - La maggiore età è fissata al compimento del diciottesimo anno...",
      "score": 0.89,
      "metadata": {
        "document_type": "norm",
        "temporal_metadata": {"is_current": true},
        "classification": {"legal_area": "civil"}
      }
    },
    {
      "chunk_id": "uuid-2",
      "text": "Cass. 18210/2015 - Il contratto stipulato da minorenne è annullabile...",
      "score": 0.85,
      "metadata": {
        "document_type": "jurisprudence",
        "temporal_metadata": {"is_current": true}
      }
    }
  ],
  "retrieval_stats": {
    "total_candidates": 1500000,
    "post_filter_candidates": 85000,
    "returned": 20,
    "latency_ms": 245
  }
}
```

**Trade-offs**:
- ✅ High recall for conceptual similarity
- ✅ Handles synonyms and paraphrases naturally
- ✅ Robust to terminology variations
- ❌ May retrieve topically similar but legally distinct content
- ❌ Less precise for specific article lookups
- ❌ Sensitive to embedding model quality

**When to Use**: Research queries, ambiguous queries, doctrinal commentary search

---

### P2: Hybrid Search Pattern

**Objective**: Combine semantic similarity with keyword matching for balanced recall + precision.

**Input Schema**:
```json
{
  "query": "art. 1325 c.c. requisiti contratto",
  "top_k": 20,
  "alpha": 0.7,
  "filters": {
    "temporal_metadata.is_current": true
  }
}
```

**Alpha Parameter**:
- `alpha = 1.0`: Pure vector search (100% semantic)
- `alpha = 0.7`: Balanced (70% semantic, 30% keyword)
- `alpha = 0.5`: Equal weight
- `alpha = 0.0`: Pure keyword search (100% BM25)

**Processing Logic**:
```
┌────────────────────────────────────────────────────┐
│ Step 1: Parallel Execution                         │
│   ┌──────────────────┐  ┌──────────────────┐      │
│   │ Vector Search    │  │ Keyword Search   │      │
│   │ (cosine sim)     │  │ (BM25 scoring)   │      │
│   └────────┬─────────┘  └────────┬─────────┘      │
└────────────┼────────────────────┼─────────────────┘
             ↓                    ↓
┌────────────────────────────────────────────────────┐
│ Step 2: Score Normalization                        │
│   vector_scores: [0.89, 0.85, ...] → [1.0, 0.95]  │
│   keyword_scores: [12.3, 10.1, ...] → [1.0, 0.82] │
└──────────────┬─────────────────────────────────────┘
               ↓
┌────────────────────────────────────────────────────┐
│ Step 3: Fusion                                     │
│   For each chunk:                                  │
│     combined_score = alpha * vector_score +        │
│                      (1-alpha) * keyword_score     │
└──────────────┬─────────────────────────────────────┘
               ↓
┌────────────────────────────────────────────────────┐
│ Step 4: Rerank & Return                            │
│   Sort by: combined_score DESC                     │
│   Return: top_k results                            │
└────────────────────────────────────────────────────┘
```

**Keyword Matching Logic**:
- Tokenization: Italian legal tokenizer (preserve "c.c.", "art.", etc.)
- Algorithm: BM25 (industry standard for keyword relevance)
- Boost: Legal entities (article numbers, court names) get 2x weight

**Output Schema**: Same as P1, with additional `keyword_score` field

**Trade-offs**:
- ✅ Best of both worlds: semantic + exact matches
- ✅ Excellent for queries with specific references ("art. 1325")
- ✅ More robust than pure vector or pure keyword
- ⚠️ Slightly higher latency (parallel execution required)
- ⚠️ Alpha tuning required for optimal balance

**When to Use**: Queries with specific legal references, balanced precision-recall needs

---

### P3: Filtered Retrieval Pattern

**Objective**: Constrain retrieval to specific subsets based on legal requirements.

**Filter Expression Schema**:
```json
{
  "temporal_filter": {
    "mode": "point_in_time | current | range",
    "reference_date": "2020-03-15",
    "start_date": "2020-01-01",
    "end_date": "2023-12-31"
  },
  "hierarchical_filter": {
    "max_level": 3,
    "include_levels": [1, 2, 3]
  },
  "domain_filter": {
    "legal_area": "civil",
    "legal_domain_tags": {
      "$in": ["contratti", "capacità"]
    }
  },
  "document_type_filter": {
    "$in": ["norm", "jurisprudence"]
  },
  "authority_filter": {
    "binding_force": "mandatory",
    "min_authority_score": 0.7
  }
}
```

**Filter Pattern Examples**:

**Temporal Filter (Multivigenza)**:
```
Query: "What did DL 18/2020 say on March 15, 2020?"

Filter Logic:
  date_effective <= 2020-03-15
  AND (date_end >= 2020-03-15 OR date_end IS NULL)

Result: Only norm versions valid on that specific date
```

**Hierarchical Filter (Kelsenian Pyramid)**:
```
Query: "What are employer obligations in smart working?"

Filter Logic:
  hierarchical_level <= 3

Result: Only binding sources (Costituzione, Legge, Regolamento)
Excludes: Case law (level 4), Doctrine (level 5)
```

**Decision Table for Filter Application**:

| Query Characteristic | Filter Type | Filter Value | Rationale |
|---------------------|-------------|--------------|-----------|
| Explicit date mentioned | Temporal (point) | Exact date | User wants specific version |
| "Current law" / "oggi" | Temporal (current) | is_current = true | Latest version only |
| Time range ("dal 2020 al 2023") | Temporal (range) | start_date, end_date | All versions in period |
| "Quali sono gli obblighi" (binding) | Hierarchical | max_level = 3 | Mandatory sources only |
| "Cosa dice la dottrina" | Document type | "doctrine" | Scholarly sources only |
| "Precedenti giurisprudenziali" | Document type | "jurisprudence" | Case law only |
| Legal area obvious | Domain | Detect from query | Scope reduction |

**Trade-offs**:
- ✅ Precision increase by scoping search space
- ✅ Faster retrieval (fewer candidates)
- ✅ Legally defensible (e.g., only binding sources)
- ❌ Risk of over-filtering (missing relevant results)
- ❌ Requires accurate filter extraction from query

**When to Use**: Temporal queries, hierarchical constraints, domain-specific research

---

### P4: Reranked Retrieval Pattern

**Objective**: Two-stage retrieval for precision optimization (fast initial retrieval + slow accurate reranking).

**Architecture**:
```
Stage 1: Fast Retrieval (Bi-Encoder)
    ↓ (retrieve top 50-100)
Stage 2: Precise Reranking (Cross-Encoder or LLM)
    ↓ (rerank to top 10-20)
```

**Stage 1: Initial Retrieval**
- Method: Semantic search or hybrid search
- Top-k: 50-100 candidates (over-retrieve for recall)
- Speed: <300ms

**Stage 2: Reranking Strategies**

| Strategy | Method | Accuracy | Latency | Cost |
|----------|--------|----------|---------|------|
| Cross-Encoder | BERT pairwise scoring | ⭐⭐⭐⭐⭐ | ~2s (50 pairs) | Free (self-hosted) |
| Authority Boost | Metadata-based rescoring | ⭐⭐⭐ | <10ms | Free |
| Temporal Boost | Recency/currency weighting | ⭐⭐⭐ | <10ms | Free |
| Citation Boost | Citation count weighting | ⭐⭐⭐⭐ | <10ms | Free |
| LLM Reranking | GPT-4 relevance scoring | ⭐⭐⭐⭐⭐ | ~5s (50 pairs) | High ($) |

**Reranking Logic (Cross-Encoder)**:
```
┌──────────────────────────────────────┐
│ Input: query + 50 candidate chunks   │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ For each chunk:                      │
│   pair = (query, chunk.text)         │
│   relevance_score = cross_encoder(pair)│
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Sort by relevance_score DESC         │
│ Return top 20                        │
└──────────────────────────────────────┘
```

**Reranking Logic (Authority Boost)**:
```
For each chunk:
  authority_score = chunk.authority_metadata.authority_score
  original_score = chunk.vector_similarity_score

  boosted_score = original_score * (1 + authority_score * boost_factor)

  where boost_factor = 0.5 (tunable)

Example:
  Chunk A: vector_score=0.80, authority=0.9 → boosted=0.80*(1+0.9*0.5)=1.16
  Chunk B: vector_score=0.85, authority=0.3 → boosted=0.85*(1+0.3*0.5)=0.98

  Result: Chunk A now ranks higher despite lower vector score
```

**Trade-offs**:
- ✅ Significant precision improvement (+10-20%)
- ✅ Can incorporate non-semantic signals (authority, citations)
- ✅ Flexible (multiple reranking strategies)
- ❌ Higher latency (2-5s total)
- ❌ Cross-encoder not cached (each query recomputes)

**When to Use**: High-value queries where precision matters more than latency

---

### P5: Multi-Query Retrieval Pattern

**Objective**: Generate multiple query variations to improve recall through diversification.

**Architecture**:
```
Original Query: "È valido un contratto firmato da un minorenne?"
    ↓
┌──────────────────────────────────────┐
│ LLM Query Variation Generator        │
│ Prompt: "Genera 3 variazioni della   │
│         seguente domanda legale..."  │
└──────────────┬───────────────────────┘
               ↓
Generated Variations:
  1. "È valido un contratto firmato da un minorenne?"
  2. "Un minore può stipulare validamente un contratto?"
  3. "Quali sono le conseguenze di un contratto firmato da persona incapace?"
  4. "Contratto stipulato da minorenne: validità o annullabilità?"
    ↓
┌──────────────────────────────────────┐
│ Parallel Retrieval (4 queries)       │
│ Each query → top 15 chunks           │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Fusion: Reciprocal Rank Fusion (RRF)│
│ Combine rankings, deduplicate        │
└──────────────┬───────────────────────┘
               ↓
Top 20 merged results
```

**Reciprocal Rank Fusion (RRF) Algorithm**:
```
For each chunk appearing in ANY query results:
  RRF_score(chunk) = Σ (1 / (k + rank_in_query_i))

  where:
    k = 60 (standard constant)
    rank_in_query_i = position of chunk in query i results (0-indexed)
    Σ = sum over all queries where chunk appears

Example:
  Chunk X appears in:
    Query 1: rank 2 → 1/(60+2) = 0.0161
    Query 3: rank 5 → 1/(60+5) = 0.0154
  RRF_score(X) = 0.0161 + 0.0154 = 0.0315

  Chunk Y appears in:
    Query 1: rank 10 → 1/(60+10) = 0.0143
  RRF_score(Y) = 0.0143

  Result: Chunk X ranks higher (appears in multiple queries)
```

**Query Variation Strategies**:

| Strategy | Example Transformation | Purpose |
|----------|----------------------|---------|
| Synonym substitution | "contratto" → "negozio giuridico" | Vocabulary diversity |
| Reformulation | Question → Statement | Syntactic diversity |
| Perspective shift | "È valido?" → "Quali conseguenze?" | Intent diversity |
| Generalization | "minorenne" → "incapace" | Broader concept |
| Specification | "contratto" → "contratto di compravendita" | Narrow focus |

**Trade-offs**:
- ✅ Significantly higher recall (+20-30%)
- ✅ Robust to query phrasing issues
- ✅ Discovers relevant results missed by single query
- ❌ Higher latency (4x retrieval operations)
- ❌ Increased LLM cost for query generation
- ❌ Risk of query drift (variation too different from intent)

**When to Use**: Research queries, ambiguous queries, high-recall requirements

---

### P6: Cross-Modal Retrieval Pattern

**Objective**: Enrich VectorDB results with KG traversal for comprehensive context.

**Architecture**:
```
User Query
    ↓
┌──────────────────────────────────────┐
│ VectorDB Semantic Search             │
│ Retrieve top 20 chunks               │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Extract KG Node IDs from chunks      │
│ • primary_article_id                 │
│ • referenced_norm_ids                │
│ • related_concept_ids                │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ KG Enrichment Traversal              │
│ For each article:                    │
│   Find: modifying articles           │
│         cited cases                  │
│         related concepts             │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Combine Results                      │
│ • VectorDB chunks (semantic)         │
│ • KG traversal nodes (structural)    │
└──────────────────────────────────────┘
```

**Workflow Example**:

Query: "È valido un contratto firmato da un minorenne?"

**Step 1: VectorDB Retrieval**
```json
{
  "vectordb_results": [
    {
      "chunk_id": "chunk-1",
      "text": "Art. 2 c.c. - La maggiore età...",
      "kg_links": {
        "primary_article_id": "article-cc-2",
        "related_concept_ids": ["concept-capacità-agire"]
      }
    },
    {
      "chunk_id": "chunk-2",
      "text": "Art. 1442 c.c. - Il contratto è annullabile...",
      "kg_links": {
        "primary_article_id": "article-cc-1442",
        "referenced_norm_ids": ["article-cc-2"]
      }
    }
  ]
}
```

**Step 2: KG Traversal**
```
Extracted KG IDs: ["article-cc-2", "article-cc-1442", "concept-capacità-agire"]

Neo4j Cypher Queries:
  1. MATCH (a:Article {id: 'article-cc-2'})<-[:MODIFIES]-(m:Article)
     RETURN m
     → Find articles that modified Art. 2

  2. MATCH (a:Article {id: 'article-cc-1442'})-[:CITES]->(c:Case)
     RETURN c
     → Find cases citing Art. 1442

  3. MATCH (c:Concept {id: 'concept-capacità-agire'})-[:RELATES_TO]->(n:Norm)
     RETURN n
     → Find all norms related to capacity concept
```

**Step 3: Combined Output**
```json
{
  "combined_results": {
    "vectordb_chunks": [
      "/* 20 semantically similar chunks */"
    ],
    "kg_enrichment": {
      "modifying_articles": [
        {"article_id": "article-cc-2-mod-2018", "title": "Modifica età maggiore"}
      ],
      "cited_cases": [
        {"case_id": "cass-18210-2015", "summary": "Contratto minorenne annullabile"}
      ],
      "related_norms": [
        {"norm_id": "article-cc-322", "title": "Capacità limitata minori"}
      ]
    }
  }
}
```

**Trade-offs**:
- ✅ Comprehensive context (semantic + structural)
- ✅ Discovers relationships not visible in VectorDB
- ✅ Enriches LLM context with precise references
- ❌ Higher latency (sequential operations)
- ❌ Requires KG population
- ⚠️ Complexity in result presentation

**When to Use**: Complex queries requiring both semantic understanding and structural relationships

---

## Performance Optimization Patterns

### Optimization Pattern Catalog

| Pattern ID | Name | Use Case | Performance Gain | Implementation Complexity |
|------------|------|----------|------------------|---------------------------|
| OP1 | Query Caching | Repeated queries | 100x faster (cache hit) | Low |
| OP2 | HNSW Index Tuning | Improve recall/latency trade-off | 2-5x faster | Medium |
| OP3 | Quantization | Reduce storage/memory | 4x smaller index | Medium |
| OP4 | Batch Processing | Bulk operations | 10-50x throughput | Low |
| OP5 | Sharding | Horizontal scaling | Linear scaling | High |
| OP6 | Embedding Caching | Avoid re-embedding | 50x faster embedding | Low |

---

### OP1: Query Caching Pattern

**Objective**: Cache frequent queries to avoid redundant vector searches.

**Cache Strategy**:
```
Cache Key = hash(query_text + filters_json)
Cache Value = {results: [...], timestamp: "ISO-8601"}
TTL = 3600 seconds (1 hour)

Lookup Flow:
  1. Compute cache key
  2. IF key exists AND timestamp < TTL:
       RETURN cached results
     ELSE:
       Execute query → cache result → return
```

**Cache Invalidation Rules**:
- Time-based: TTL expiration (default 1 hour)
- Event-based: New document ingestion → invalidate all caches
- Selective: RLCF updates → invalidate affected queries only

**Performance Metrics**:
- Cache hit rate target: >40% for production traffic
- Cache hit latency: <10ms
- Cache miss latency: Same as non-cached (300ms)
- Storage: ~10MB per 1000 cached queries

---

### OP2: HNSW Index Tuning Pattern

**HNSW Parameters**:

| Parameter | Description | Default | Legal Use Case Recommendation | Impact |
|-----------|-------------|---------|-------------------------------|--------|
| `M` | Connections per layer | 16 | **32** | Recall ↑, Memory ↑ |
| `ef_construction` | Construction search depth | 100 | **200** | Build time ↑, Recall ↑ |
| `ef_search` | Query search depth | 50 | **100** | Query latency ↑, Recall ↑ |

**Rationale for Legal Domain**:
- **Recall priority**: Missing a relevant norm is unacceptable
- **Memory acceptable**: Legal corpus is finite (millions, not billions of chunks)
- **Latency tolerance**: 200-500ms acceptable for complex queries

**Trade-off Analysis**:

```
Scenario 1: Low Resources (M=16, ef=50)
  Recall: 85%
  Query Latency: 150ms
  Memory: 4GB (1M chunks)
  Risk: Misses 15% of relevant norms ❌

Scenario 2: Balanced (M=32, ef=100) ← RECOMMENDED
  Recall: 95%
  Query Latency: 250ms
  Memory: 8GB (1M chunks)
  Risk: Misses 5% of relevant norms ✅ Acceptable

Scenario 3: Max Recall (M=64, ef=200)
  Recall: 98%
  Query Latency: 450ms
  Memory: 16GB (1M chunks)
  Risk: Minimal misses, but latency high ⚠️
```

---

### OP3: Quantization Pattern

**Objective**: Reduce embedding dimensionality while preserving semantic similarity.

**Quantization Strategy**:
```
Original: 3072 dimensions × 4 bytes (float32) = 12KB per embedding
Quantized: 768 dimensions × 2 bytes (float16) = 1.5KB per embedding
Reduction: 8x smaller
```

**Methods**:

| Method | Technique | Quality Loss | Implementation |
|--------|-----------|--------------|----------------|
| Dimensionality Reduction | Random projection (Johnson-Lindenstrauss) | ~5% recall | Fit projector on sample, apply to all |
| Precision Reduction | Float32 → Float16 | <1% recall | Direct conversion |
| Product Quantization | Vector decomposition | ~3% recall | Train codebook, encode vectors |

**Recommended Approach**: Random Projection (3072 → 768)
- Quality loss: 5-8% recall (acceptable)
- Storage reduction: 4x
- Query latency: 2-3x faster (smaller index)

**Validation Protocol**:
```
1. Fit projector on 10K sample embeddings
2. Transform all embeddings
3. A/B test: original vs quantized
4. IF recall_delta < 10%:
     Deploy quantized
   ELSE:
     Increase target dimensions (768 → 1536)
```

---

### OP4: Batch Processing Pattern

**Objective**: Optimize throughput for bulk operations (ingestion, re-embedding).

**Batch Ingestion**:
```
Single Insert: 1 chunk per request → 50ms per chunk → 20 chunks/second
Batch Insert: 100 chunks per request → 500ms per batch → 200 chunks/second

Speedup: 10x throughput improvement
```

**Optimal Batch Size Decision Table**:

| Operation | Optimal Batch Size | Rationale |
|-----------|-------------------|-----------|
| Embedding generation | 32-64 chunks | GPU utilization sweet spot |
| Vector DB insertion | 100-500 chunks | Network overhead amortization |
| Query variations | 3-5 queries | Diminishing returns beyond 5 |
| Reranking | 50-100 candidates | Cross-encoder batch limit |

---

### OP5: Sharding Pattern

**Objective**: Horizontal scaling for large corpora (>10M chunks).

**Sharding Strategy**: **Legal Domain Sharding**

```
┌─────────────────────────────────────────────┐
│          Shard Router                       │
└─────────────────┬───────────────────────────┘
                  ↓
      ┌───────────┴───────────┐
      ↓                       ↓
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Civil    │  │ Penal    │  │ Admin    │
│ Shard    │  │ Shard    │  │ Shard    │
│ 3M chunks│  │ 2M chunks│  │ 1.5M chunks│
└──────────┘  └──────────┘  └──────────┘
```

**Routing Logic**:
```
IF query.filters.legal_area specified:
  Route to single shard (legal_area)
ELSE:
  Route to all shards, merge results
```

**Merge Strategy**: RRF (Reciprocal Rank Fusion)
- Each shard returns top-k with scores
- Combine using RRF algorithm
- Return top-k from merged results

**Scaling Characteristics**:
- Linear scaling: 3 shards → 3x throughput
- Fault tolerance: Shard failure affects only 1 legal domain
- Maintenance: Re-indexing per shard (smaller operations)

---

### OP6: Embedding Caching Pattern

**Objective**: Cache embeddings for frequently embedded texts (e.g., common queries).

**Cache Strategy**:
```
Cache Key = hash(text)
Cache Value = {embedding: [...], model_version: "phase_3_v2"}
TTL = 7 days (queries), infinite (chunks)

Lookup:
  IF text in cache AND model_version matches:
    RETURN cached embedding
  ELSE:
    Generate embedding → cache → return
```

**Use Cases**:
- Query embeddings: Cache common legal questions
- Chunk embeddings: Never re-embed (immutable)
- Model updates: Invalidate cache on model version change

**Performance**:
- Cache hit latency: <1ms (in-memory)
- Cache miss latency: 50-200ms (model inference)
- Speedup: 50-200x for cache hits

---

## Integration Protocols

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  OFFLINE: Data Ingestion → Vector Database                  │
└─────────────────────────────────────────────────────────────┘

Legal Documents (norms, cases, doctrine)
    ↓
┌──────────────────────────────────────┐
│ Parse & Structure                    │
│ (Akoma Ntoso, PDF, XML)              │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Semantic Chunking                    │
│ Strategy: semantic coherence         │
│ Size: 500-1500 tokens                │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Entity Extraction (NER)              │
│ Extract: norms, concepts, dates      │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Metadata Enrichment                  │
│ Add: temporal, authority, KG links   │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Embedding Generation                 │
│ Model: Phase 1-5 (current phase)    │
│ Output: Dense vector (768-3072 dim) │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Vector DB Ingestion                  │
│ Batch insert with metadata           │
│ Create indexes (HNSW)                │
└──────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│  ONLINE: Query Processing → Expert LLMs                     │
└─────────────────────────────────────────────────────────────┘

User Query
    ↓
┌──────────────────────────────────────┐
│ Query Understanding                  │
│ Output: structured_query             │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ LLM Router                           │
│ Decision: Activate VectorDB Agent?   │
│ Output: Task schema for agent        │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ VectorDB Agent                       │
│ Execute: Retrieval pattern (P1-P6)  │
│ Apply: Filters, reranking            │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Results → Expert LLMs                │
│ Context: Retrieved chunks            │
│ Task: Answer synthesis               │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Synthesizer                          │
│ Combine: KG + VectorDB + Expert      │
└──────────────┬───────────────────────┘
               ↓
User Answer


┌─────────────────────────────────────────────────────────────┐
│  FEEDBACK LOOP: RLCF → Embedding Model Evolution            │
└─────────────────────────────────────────────────────────────┘

User Feedback (relevance ratings)
    ↓
┌──────────────────────────────────────┐
│ Aggregate Feedback (weekly)          │
│ Build: query-document pairs          │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Model Update Decision                │
│ IF drift > threshold: retrain        │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Fine-Tune Embeddings (Phase 3+)      │
│ Training: Contrastive learning       │
│ Validation: A/B test                 │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Re-Embed Corpus (if model updated)   │
│ Gradual rollout (10% → 50% → 100%)  │
└──────────────────────────────────────┘
```

### Cross-Component Communication Schemas

#### VectorDB → Expert LLM Context Schema

```json
{
  "retrieved_context": {
    "source": "vectordb_agent",
    "retrieval_pattern": "P2_hybrid_search",
    "query_normalized": "È valido un contratto firmato da un minorenne?",
    "chunks": [
      {
        "chunk_id": "uuid-1",
        "text": "Art. 2 c.c. - La maggiore età è fissata...",
        "score": 0.89,
        "document_type": "norm",
        "authority_score": 0.95,
        "temporal_metadata": {
          "is_current": true,
          "date_effective": "1942-04-21"
        },
        "citation_text": "[1] Art. 2 c.c."
      },
      {
        "chunk_id": "uuid-2",
        "text": "Il contratto stipulato da minorenne è annullabile...",
        "score": 0.85,
        "document_type": "jurisprudence",
        "source_metadata": {
          "court_name": "Cassazione",
          "case_number": "18210/2015"
        },
        "citation_text": "[2] Cass. 18210/2015"
      }
    ],
    "retrieval_stats": {
      "total_retrieved": 20,
      "context_window_used": 5,
      "latency_ms": 245
    }
  }
}
```

#### KG + VectorDB Fusion Schema

```json
{
  "combined_context": {
    "kg_results": {
      "source": "kg_agent",
      "entities": [
        {
          "article_id": "article-cc-2",
          "title": "Maggiore età. Capacità di agire",
          "text": "La maggiore età è fissata al compimento del diciottesimo anno...",
          "relationships": {
            "modified_by": ["article-cc-2-mod-2018"],
            "related_concepts": ["concept-capacità-agire"]
          }
        }
      ]
    },
    "vectordb_results": {
      "source": "vectordb_agent",
      "chunks": [
        "/* See schema above */"
      ]
    },
    "fusion_strategy": "kg_structure_vectordb_enrichment",
    "presentation": {
      "primary_sources": "kg_articles",
      "contextual_sources": "vectordb_chunks"
    }
  }
}
```

### Error Handling Patterns

| Error Type | Cause | Handling Strategy | Fallback |
|------------|-------|-------------------|----------|
| **Empty Results** | No matches for query+filters | Relax filters incrementally | Semantic search only |
| **Timeout** | Query exceeded latency budget | Return partial results | Use cached results |
| **Model Unavailable** | Embedding service down | Use cached embeddings | Skip VectorDB agent |
| **Index Corruption** | Vector DB index error | Rebuild index (background) | Use KG agent only |
| **OOM** | Large batch operation | Reduce batch size | Sequential processing |

**Error Response Schema**:
```json
{
  "status": "partial_failure",
  "error": {
    "type": "timeout",
    "message": "VectorDB query exceeded 5000ms budget",
    "timestamp": "ISO-8601"
  },
  "partial_results": {
    "chunks": [],
    "retrieved_count": 8,
    "requested_count": 20
  },
  "fallback_used": "cached_results",
  "retry_recommended": true
}
```

---

## Agent Interface Protocol

### VectorDB Agent Specification

**Agent Identity**:
```json
{
  "agent_id": "vectordb_agent",
  "agent_type": "retrieval",
  "capabilities": [
    "semantic_search",
    "hybrid_search",
    "filtered_retrieval",
    "reranking",
    "multi_query_expansion"
  ],
  "data_sources": ["vector_database"],
  "parallel_compatible": true
}
```

### Router → VectorDB Agent Task Schema

**Input Schema** (Router sends to VectorDB Agent):
```json
{
  "task_id": "uuid",
  "agent_target": "vectordb_agent",
  "priority": "high | medium | low",
  "timeout_ms": 5000,

  "task_definition": {
    "retrieval_pattern": "P2_hybrid_search",
    "query_normalized": "È valido un contratto firmato da un minorenne?",
    "query_entities": {
      "legal_concepts": ["contratto", "minorenne", "validità"],
      "norm_references": []
    },
    "filters": {
      "temporal_metadata.is_current": true,
      "classification.legal_area": "civil",
      "document_type": ["norm", "jurisprudence"]
    },
    "top_k": 20,
    "rerank": {
      "enabled": true,
      "strategy": "authority_boost",
      "boost_factor": 0.5
    },
    "context_budget": {
      "max_chunks": 10,
      "max_tokens": 8000
    }
  }
}
```

### VectorDB Agent → Expert LLM Output Schema

**Output Schema** (VectorDB Agent returns):
```json
{
  "task_id": "uuid",
  "agent_id": "vectordb_agent",
  "status": "success | partial | failure",
  "execution_time_ms": 245,

  "results": {
    "chunks": [
      {
        "chunk_id": "uuid-1",
        "text": "Art. 2 c.c. - La maggiore età...",
        "score": 0.89,
        "metadata": {
          "document_type": "norm",
          "authority_score": 0.95,
          "is_current": true
        },
        "citation_reference": "[1] Art. 2 c.c."
      }
    ],
    "total_retrieved": 20,
    "total_returned": 10,
    "context_tokens_used": 6800
  },

  "retrieval_metadata": {
    "pattern_used": "P2_hybrid_search",
    "alpha": 0.7,
    "filters_applied": {
      "is_current": true,
      "legal_area": "civil"
    },
    "rerank_applied": "authority_boost"
  }
}
```

### Parallel Execution Protocol

**Scenario**: Router activates KG Agent + VectorDB Agent + API Agent in parallel

```
Router Decision:
  {
    "execution_mode": "parallel",
    "agents": ["kg_agent", "vectordb_agent", "api_agent"]
  }

Orchestration:
  ┌──────────────────────────────────────┐
  │ Router broadcasts tasks              │
  └──────────────┬───────────────────────┘
                 ↓
       ┌─────────┴─────────┐
       ↓                   ↓                   ↓
  ┌─────────┐      ┌─────────────┐     ┌─────────┐
  │ KG Agent│      │VectorDB Agent│     │API Agent│
  │ 150ms   │      │ 245ms       │     │ 1200ms  │
  └────┬────┘      └──────┬──────┘     └────┬────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                          ↓
              ┌────────────────────────┐
              │ Await all (max 1200ms) │
              └────────────┬───────────┘
                           ↓
              ┌────────────────────────┐
              │ Merge results          │
              │ • KG: 5 articles       │
              │ • VectorDB: 10 chunks  │
              │ • API: 3 definitions   │
              └────────────┬───────────┘
                           ↓
              Pass to Expert LLMs
```

**Synchronization Schema**:
```json
{
  "parallel_execution": {
    "tasks": [
      {"agent": "kg_agent", "status": "completed", "latency_ms": 150},
      {"agent": "vectordb_agent", "status": "completed", "latency_ms": 245},
      {"agent": "api_agent", "status": "completed", "latency_ms": 1200}
    ],
    "total_latency_ms": 1200,
    "bottleneck": "api_agent"
  },
  "merged_context": {
    "kg_results": [],
    "vectordb_results": [],
    "api_results": []
  }
}
```

### Failure Handling in Parallel Execution

| Scenario | Handling | Impact |
|----------|----------|--------|
| **1 agent fails** | Continue with other agents | Partial context |
| **2+ agents fail** | Abort query, return error | No context |
| **1 agent timeout** | Use partial results from agent | Reduced context |
| **All agents timeout** | Return cached results if available | Stale context |

---

## Technology Selection Framework

### Selection Dimensions

| Dimension | Weight | Evaluation Criteria |
|-----------|--------|---------------------|
| **Hybrid Search** | High | Native vector + keyword fusion capability |
| **Metadata Filtering** | High | Rich boolean expressions, nested fields, range queries |
| **Performance at Scale** | High | Query latency p95 <500ms at 1M+ chunks |
| **Schema Flexibility** | Medium | Support for heterogeneous document types |
| **Deployment Options** | Medium | Self-hosted vs managed trade-off |
| **Cost Efficiency** | Medium | Total cost of ownership at target scale |
| **Ecosystem Maturity** | Low | Community support, documentation, integrations |

### Comparison Matrix

| Technology | Hybrid Search | Metadata | Performance | Flexibility | Deployment | Cost | Maturity |
|------------|--------------|----------|-------------|-------------|------------|------|----------|
| **Weaviate** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Qdrant** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Pinecone** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **pgvector** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Elasticsearch** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Decision Tree

```
START: Choose Vector Database for MERL-T

Q1: Do you need hybrid search (vector + keyword)?
    ├─ Yes → Q2
    └─ No → Q3

Q2: Is deployment complexity a concern?
    ├─ Low concern (can manage complex setup) → Weaviate ✅
    └─ High concern (prefer simple) → Elasticsearch

Q3: Is performance the top priority?
    ├─ Yes → Qdrant ✅
    └─ No → Q4

Q4: Do you already use PostgreSQL?
    ├─ Yes → pgvector ✅
    └─ No → Q5

Q5: Is managed service preferred over self-hosted?
    ├─ Yes → Pinecone ✅
    └─ No → Qdrant ✅
```

### Abstract Interface Requirements

**Core Operations**:
```json
{
  "required_operations": [
    {
      "operation": "ingest",
      "input_schema": {
        "chunks": "Array<ChunkSchema>",
        "batch_size": "integer (max 1000)"
      },
      "output_schema": {
        "inserted_count": "integer",
        "errors": "Array<Error>"
      },
      "constraints": {
        "max_batch_size": 1000,
        "idempotent": true
      }
    },
    {
      "operation": "search",
      "input_schema": {
        "query_vector": "Array<float>",
        "filters": "FilterExpression",
        "limit": "integer"
      },
      "output_schema": {
        "results": "Array<ResultSchema>"
      },
      "constraints": {
        "response_time_p95": "<500ms"
      }
    },
    {
      "operation": "hybrid_search",
      "input_schema": {
        "query_text": "string",
        "query_vector": "Array<float>",
        "alpha": "float (0.0-1.0)",
        "filters": "FilterExpression"
      },
      "output_schema": {
        "results": "Array<ResultSchema>"
      },
      "constraints": {
        "alpha_range": [0.0, 1.0],
        "response_time_p95": "<800ms"
      }
    },
    {
      "operation": "delete",
      "input_schema": {
        "chunk_ids": "Array<uuid>"
      },
      "output_schema": {
        "deleted_count": "integer"
      },
      "constraints": {
        "idempotent": true
      }
    },
    {
      "operation": "update_metadata",
      "input_schema": {
        "chunk_id": "uuid",
        "metadata": "Partial<ChunkSchema>"
      },
      "output_schema": {
        "success": "boolean"
      },
      "constraints": {
        "partial_updates": true
      }
    }
  ]
}
```

**Filter Expression Specification**:
```json
{
  "filter_expression_schema": {
    "$and": [
      {
        "field": "temporal_metadata.is_current",
        "operator": "==",
        "value": true
      },
      {
        "field": "classification.legal_area",
        "operator": "==",
        "value": "civil"
      },
      {
        "field": "authority_metadata.hierarchical_level",
        "operator": "<=",
        "value": 2
      }
    ]
  },
  "supported_operators": ["==", "!=", "<", "<=", ">", ">=", "in", "not_in"],
  "supported_combinators": ["$and", "$or", "$not"]
}
```

### Implementation Reference

For technology-specific implementation details (code examples, API usage, deployment configurations), refer to:

**→ `/docs/03-implementation/vector-db-technologies.md`**

This companion document contains:
- Weaviate setup and code examples
- Qdrant integration patterns
- Pinecone deployment guide
- pgvector PostgreSQL configuration
- Performance tuning code
- Monitoring and observability

---

## Validation Examples

### Example 1: Simple Definition Query

**Query**: "Cos'è la simulazione contrattuale?"

**Query Understanding Output**:
```json
{
  "normalized_query": "Cos'è la simulazione contrattuale?",
  "intent": {
    "primary": {"type": "definition", "confidence": 0.95}
  },
  "complexity": {"level": "simple", "score": 0.25},
  "entities_extracted": {
    "legal_concepts": ["simulazione contrattuale"]
  }
}
```

**Router Decision**:
```json
{
  "execution_plan": {
    "agents": [
      {
        "agent_type": "vectordb_agent",
        "priority": "high",
        "rationale": "Definition query requires semantic search for norm text + doctrinal explanation"
      }
    ]
  }
}
```

**VectorDB Agent Task**:
```json
{
  "task_definition": {
    "retrieval_pattern": "P1_semantic_search",
    "query_normalized": "Cos'è la simulazione contrattuale?",
    "filters": {
      "temporal_metadata.is_current": true,
      "classification.legal_area": "civil"
    },
    "top_k": 10
  }
}
```

**Retrieval Flow**:
```
Step 1: Query Embedding
   Input: "Cos'è la simulazione contrattuale?"
   Output: [0.023, -0.089, 0.102, ..., -0.045] (3072 dims)

Step 2: Filter Application
   is_current = true AND legal_area = 'civil'
   Candidates reduced: 1.5M → 85K chunks

Step 3: Vector Similarity Search
   Metric: cosine similarity
   HNSW traversal (ef=100)
   Time: 180ms

Step 4: Top-K Selection
   Rank by similarity score DESC
   Return top 10 results
```

**Results**:
```json
{
  "results": [
    {
      "chunk_id": "uuid-art-1414",
      "text": "Art. 1414 c.c. - Simulazione. Il contratto simulato non produce effetto tra le parti. Se le parti hanno voluto concludere un contratto diverso da quello apparente, ha effetto tra esse il contratto dissimulato, purché ne sussistano i requisiti di sostanza e di forma.",
      "score": 0.92,
      "metadata": {
        "document_type": "norm",
        "authority_score": 0.95
      },
      "citation_reference": "[1] Art. 1414 c.c."
    },
    {
      "chunk_id": "uuid-doctrine-sim",
      "text": "La simulazione è un accordo tra le parti volto a creare un'apparenza giuridica diversa dalla realtà. Si distingue in assoluta (nessun contratto reale) e relativa (contratto dissimulato)...",
      "score": 0.88,
      "metadata": {
        "document_type": "doctrine",
        "author": "Trabucchi"
      },
      "citation_reference": "[2] Trabucchi, Istituzioni"
    },
    {
      "chunk_id": "uuid-case-sim",
      "text": "Cass. 12345/2020 - Per simulazione si intende l'accordo simulatorio con cui le parti creano una divergenza intenzionale tra dichiarazione e volontà...",
      "score": 0.85,
      "metadata": {
        "document_type": "jurisprudence"
      },
      "citation_reference": "[3] Cass. 12345/2020"
    }
  ]
}
```

**Decision Walkthrough**:

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| Retrieval pattern | P1 (Semantic search) | Simple query, no specific references, semantic understanding sufficient |
| Filters | is_current=true, legal_area=civil | Definition should use current law only, civil law context |
| Top-k | 10 | Small result set sufficient for definition |
| Rerank | No | Not needed for simple query |

**Outcome**: VectorDB retrieval sufficient. Top 3 chunks (Art. 1414, doctrinal explanation, case law) provide complete definition.

---

### Example 2: Temporal Query with Precise Date

**Query**: "Cosa stabiliva l'art. 5 del DL 18/2020 sullo smart working il 15 marzo 2020?"

**Query Understanding Output**:
```json
{
  "normalized_query": "Cosa stabiliva l'art. 5 del DL 18/2020 sullo smart working il 15 marzo 2020?",
  "intent": {
    "primary": {"type": "temporal_query", "confidence": 0.92}
  },
  "complexity": {"level": "high", "score": 0.75},
  "entities_extracted": {
    "norm_references": [
      {"type": "article", "article": "5", "code": "DL 18/2020"}
    ],
    "temporal_entities": [
      {"type": "absolute_date", "value": "2020-03-15"}
    ],
    "legal_concepts": ["smart working"]
  }
}
```

**Router Decision**:
```json
{
  "execution_plan": {
    "agents": [
      {
        "agent_type": "kg_agent",
        "priority": "high",
        "rationale": "Precise article reference → KG for structure"
      },
      {
        "agent_type": "vectordb_agent",
        "priority": "high",
        "rationale": "Temporal filtering → VectorDB for correct version"
      }
    ],
    "execution_mode": "parallel"
  }
}
```

**VectorDB Agent Task**:
```json
{
  "task_definition": {
    "retrieval_pattern": "P3_filtered_retrieval",
    "query_normalized": "art. 5 DL 18/2020 smart working",
    "filters": {
      "document_type": "norm",
      "temporal_metadata": {
        "date_effective": {"$lte": "2020-03-15"},
        "$or": [
          {"date_end": {"$gte": "2020-03-15"}},
          {"date_end": null}
        ]
      },
      "source_metadata.norm_id": "DL-18-2020"
    },
    "top_k": 5
  }
}
```

**Temporal Filter Logic**:
```
Constraint: Find norm version valid on 2020-03-15

SQL-like expression:
  WHERE date_effective <= '2020-03-15'
    AND (date_end >= '2020-03-15' OR date_end IS NULL)
    AND norm_id = 'DL-18-2020'

Multivigenza handling:
  DL 18/2020 published: 2020-03-17
  Original version effective: 2020-03-17
  BUT query asks for 2020-03-15 → NO RESULTS

  Fallback: Relax to first available version after query date
  Result: Version effective 2020-03-17 (2 days after query date)
```

**Results**:
```json
{
  "results": [
    {
      "chunk_id": "uuid-dl-18-2020-art-5-v1",
      "text": "Art. 5 DL 18/2020 - Modalità ordinaria di lavoro agile. Fino alla data del 30 aprile 2020, i lavoratori dipendenti hanno diritto a svolgere la prestazione di lavoro in modalità agile, anche in assenza degli accordi individuali...",
      "score": 0.95,
      "metadata": {
        "document_type": "norm",
        "temporal_metadata": {
          "date_effective": "2020-03-17",
          "date_end": "2020-07-31",
          "is_current": false
        },
        "version_note": "Original version (superseded by DL 34/2020)"
      },
      "citation_reference": "[1] Art. 5 DL 18/2020 (vers. originale)"
    }
  ],
  "retrieval_metadata": {
    "temporal_adjustment": "Query date 2020-03-15 predates norm publication; returned first version (2020-03-17)",
    "multivigenza_detected": true,
    "later_versions_exist": [
      {"date_effective": "2020-08-01", "modified_by": "DL 34/2020"}
    ]
  }
}
```

**Decision Walkthrough**:

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| Retrieval pattern | P3 (Filtered retrieval) | Temporal constraint is primary requirement |
| Temporal filter mode | Point-in-time | Specific date mentioned (2020-03-15) |
| Document type filter | norm | Query explicitly asks for norm article |
| Norm ID filter | DL-18-2020 | Explicit norm reference |
| Top-k | 5 | Precision over recall (specific version) |
| Fallback on date mismatch | Return nearest version | Better than empty result |

**KG Enrichment**:
```json
{
  "kg_enrichment": {
    "norm_timeline": [
      {"version": 1, "date_effective": "2020-03-17", "status": "original"},
      {"version": 2, "date_effective": "2020-08-01", "modified_by": "DL 34/2020"},
      {"version": 3, "date_effective": "2021-09-01", "modified_by": "L. 81/2017"}
    ],
    "current_version": {
      "version": 3,
      "date_effective": "2021-09-01",
      "is_current": true
    }
  }
}
```

**Outcome**: VectorDB provides correct historical version text, KG provides temporal context (later modifications). Combined context allows Expert LLM to answer "what it said then" vs "what it says now".

---

### Example 3: Research Query with High Recall

**Query**: "Quali sono le principali modifiche alla disciplina dello smart working dal 2020 al 2023?"

**Query Understanding Output**:
```json
{
  "normalized_query": "Quali sono le principali modifiche alla disciplina dello smart working dal 2020 al 2023?",
  "intent": {
    "primary": {"type": "research", "confidence": 0.88}
  },
  "complexity": {"level": "very_high", "score": 0.92},
  "entities_extracted": {
    "legal_concepts": ["smart working", "disciplina", "modifiche"],
    "temporal_entities": [
      {"type": "time_period", "start": "2020-01-01", "end": "2023-12-31"}
    ]
  }
}
```

**Router Decision**:
```json
{
  "execution_plan": {
    "agents": [
      {
        "agent_type": "vectordb_agent",
        "priority": "high",
        "rationale": "Research query requires broad recall across multiple sources"
      },
      {
        "agent_type": "kg_agent",
        "priority": "medium",
        "rationale": "KG can provide modification graph, but VectorDB is primary"
      }
    ]
  }
}
```

**VectorDB Agent Task**:
```json
{
  "task_definition": {
    "retrieval_pattern": "P5_multi_query_retrieval",
    "query_normalized": "Quali sono le principali modifiche alla disciplina dello smart working dal 2020 al 2023?",
    "query_variations": 5,
    "filters": {
      "temporal_metadata": {
        "date_effective": {"$gte": "2020-01-01", "$lte": "2023-12-31"}
      },
      "document_type": ["norm", "jurisprudence", "doctrine"]
    },
    "top_k_per_query": 20,
    "final_top_k": 30,
    "rerank": {
      "enabled": true,
      "strategy": "cross_encoder"
    }
  }
}
```

**Query Variations Generated**:
```json
{
  "query_variations": [
    "Quali sono le principali modifiche alla disciplina dello smart working dal 2020 al 2023?",
    "Evoluzione normativa del lavoro agile tra 2020 e 2023",
    "Cambiamenti legislativi smart working periodo 2020-2023",
    "Aggiornamenti disciplina telelavoro dal 2020",
    "Riforme lavoro da remoto in Italia ultimi anni"
  ]
}
```

**Multi-Query Retrieval Flow**:
```
Step 1: Generate 5 Query Variations
   LLM prompt: "Genera variazioni semantiche..."
   Time: 800ms

Step 2: Parallel Retrieval (5 queries)
   Each query → top 20 chunks
   Parallel execution time: max(query_latencies) = 320ms

Step 3: Reciprocal Rank Fusion (RRF)
   Combine 5 × 20 = 100 results
   Deduplicate: 100 → 65 unique chunks
   RRF scoring for each chunk
   Time: 50ms

Step 4: Cross-Encoder Reranking
   Rerank top 50 candidates
   cross_encoder(query_original, chunk.text)
   Time: 1800ms

Step 5: Final Selection
   Select top 30 after reranking
   Total time: 2970ms (~3s)
```

**Reranking Decision Table**:

| Chunk | Initial RRF Score | Cross-Encoder Score | Final Rank | Source |
|-------|------------------|---------------------|------------|--------|
| DL 18/2020 art. 5 | 0.085 | 0.94 | 1 | Norm |
| L. 81/2017 modifiche | 0.072 | 0.91 | 2 | Norm |
| Cass. smart working | 0.068 | 0.88 | 3 | Jurisprudence |
| Dottrina evoluzione | 0.091 | 0.87 | 4 | Doctrine |
| DL 127/2021 | 0.065 | 0.85 | 5 | Norm |

**Results** (Top 10 shown):
```json
{
  "results": [
    {
      "chunk_id": "uuid-dl-18-2020",
      "text": "DL 18/2020 - Misure emergenziali: diritto alla modalità agile senza accordo individuale...",
      "score": 0.94,
      "metadata": {
        "document_type": "norm",
        "date_effective": "2020-03-17"
      }
    },
    {
      "chunk_id": "uuid-l-81-2017-mod",
      "text": "L. 81/2017 - Modifiche alla disciplina permanente del lavoro agile...",
      "score": 0.91,
      "metadata": {
        "document_type": "norm",
        "date_effective": "2021-09-01"
      }
    },
    {
      "chunk_id": "uuid-cass-sw-2022",
      "text": "Cass. 5432/2022 - Orientamento giurisprudenziale sull'applicazione delle norme emergenziali...",
      "score": 0.88,
      "metadata": {
        "document_type": "jurisprudence"
      }
    }
  ],
  "retrieval_stats": {
    "query_variations_used": 5,
    "total_candidates_retrieved": 100,
    "unique_candidates": 65,
    "reranked_candidates": 50,
    "final_returned": 30,
    "total_latency_ms": 2970,
    "coverage": {
      "norms": 15,
      "jurisprudence": 8,
      "doctrine": 7
    }
  }
}
```

**Decision Walkthrough**:

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| Retrieval pattern | P5 (Multi-query) | Research query requires maximum recall |
| Query variations | 5 | Balance between recall and cost |
| Temporal filter | Range (2020-2023) | Explicit time period in query |
| Document types | All (norm, case, doctrine) | Comprehensive research needs all sources |
| Top-k per query | 20 | High recall (5 queries × 20 = 100 candidates) |
| Rerank strategy | Cross-encoder | Precision after high-recall retrieval |
| Final top-k | 30 | Rich context for synthesis |

**Outcome**: Multi-query + reranking achieves comprehensive coverage of smart working evolution (15 norms, 8 cases, 7 doctrinal sources). Expert LLM synthesizes timeline of changes.

---

### Example 4: Hybrid Search for Article Lookup

**Query**: "Quali sono i requisiti del contratto secondo l'art. 1325 c.c.?"

**Query Understanding Output**:
```json
{
  "normalized_query": "Quali sono i requisiti del contratto secondo l'art. 1325 c.c.?",
  "intent": {
    "primary": {"type": "definition", "confidence": 0.90}
  },
  "complexity": {"level": "simple", "score": 0.30},
  "entities_extracted": {
    "norm_references": [
      {"type": "article", "article": "1325", "code": "cc"}
    ],
    "legal_concepts": ["requisiti", "contratto"]
  }
}
```

**Router Decision**:
```json
{
  "execution_plan": {
    "agents": [
      {
        "agent_type": "vectordb_agent",
        "priority": "high",
        "rationale": "Specific article reference benefits from hybrid search (keyword + semantic)"
      }
    ]
  }
}
```

**VectorDB Agent Task**:
```json
{
  "task_definition": {
    "retrieval_pattern": "P2_hybrid_search",
    "query_normalized": "Quali sono i requisiti del contratto secondo l'art. 1325 c.c.?",
    "query_text": "art. 1325 c.c. requisiti contratto",
    "filters": {
      "temporal_metadata.is_current": true,
      "classification.legal_area": "civil"
    },
    "alpha": 0.5,
    "top_k": 10
  }
}
```

**Hybrid Search Flow**:
```
┌────────────────────────────────────────┐
│ Parallel Execution                     │
└────────────────────────────────────────┘

Branch 1: Vector Search               Branch 2: Keyword Search (BM25)
   ↓                                      ↓
Embedding: [0.02, -0.08, ...]         Tokens: ["art", "1325", "c.c.",
Cosine similarity search                      "requisiti", "contratto"]
                                       BM25 scoring with boosts:
Results:                                 - "1325": boost ×2 (article number)
1. Art. 1325 c.c. (score: 0.95)         - "c.c.": boost ×1.5 (code ref)
2. Art. 1321 c.c. (score: 0.88)
3. Art. 1326 c.c. (score: 0.85)       Results:
                                       1. Art. 1325 c.c. (score: 18.3)
                                       2. Art. 1350 c.c. (score: 12.1)
                                       3. Art. 1418 c.c. (score: 10.5)

        ↓                                      ↓
┌────────────────────────────────────────────────┐
│ Score Fusion (alpha=0.5)                      │
│                                                │
│ Art. 1325: 0.5 × 0.95 + 0.5 × 1.0 = 0.975    │
│ Art. 1321: 0.5 × 0.88 + 0.5 × 0.0 = 0.440    │
│ Art. 1350: 0.5 × 0.0  + 0.5 × 0.66 = 0.330   │
│                                                │
│ (BM25 scores normalized to [0,1])             │
└────────────────┬───────────────────────────────┘
                 ↓
┌────────────────────────────────────────┐
│ Ranked Results                         │
│ 1. Art. 1325 (0.975) ← Perfect match   │
│ 2. Art. 1321 (0.440) ← Semantic similar│
│ 3. Art. 1326 (0.425) ← Semantic similar│
└────────────────────────────────────────┘
```

**Results**:
```json
{
  "results": [
    {
      "chunk_id": "uuid-art-1325",
      "text": "Art. 1325 c.c. - Indicazione dei requisiti. I requisiti del contratto sono: 1) l'accordo delle parti; 2) la causa; 3) l'oggetto; 4) la forma, quando risulta che è prescritta dalla legge sotto pena di nullità.",
      "score": 0.975,
      "metadata": {
        "document_type": "norm",
        "vector_score": 0.95,
        "keyword_score": 1.0
      },
      "citation_reference": "[1] Art. 1325 c.c."
    },
    {
      "chunk_id": "uuid-art-1321",
      "text": "Art. 1321 c.c. - Nozione. Il contratto è l'accordo di due o più parti per costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale.",
      "score": 0.440,
      "metadata": {
        "document_type": "norm",
        "vector_score": 0.88,
        "keyword_score": 0.0
      },
      "citation_reference": "[2] Art. 1321 c.c."
    }
  ]
}
```

**Score Breakdown Table**:

| Chunk | Vector Score | Keyword Score (BM25) | Alpha=0.5 Combined | Rank |
|-------|-------------|---------------------|-------------------|------|
| Art. 1325 | 0.95 | 1.0 (exact match) | **0.975** | 1 |
| Art. 1321 | 0.88 | 0.0 (no keyword) | 0.440 | 2 |
| Art. 1326 | 0.85 | 0.0 (no keyword) | 0.425 | 3 |
| Art. 1350 | 0.65 | 0.66 (partial match) | 0.655 | Would be rank 2 if in top 10 |

**Decision Walkthrough**:

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| Retrieval pattern | P2 (Hybrid search) | Specific article number → keyword matching critical |
| Alpha | 0.5 (balanced) | Equal weight for semantic + exact match |
| Filters | is_current=true, legal_area=civil | Current law, civil code context |
| Top-k | 10 | Small result set for specific query |

**Outcome**: Hybrid search ensures Art. 1325 is top result (keyword boost), while semantic search discovers related articles (1321, 1326) for context.

---

## Evolution & RLCF Integration

### Embedding Model Evolution Protocol

**Phase Transition State Machine**:

```
┌─────────────────────────────────────────────────────────────┐
│                  EMBEDDING MODEL LIFECYCLE                   │
└─────────────────────────────────────────────────────────────┘

STATE: Phase 1 (Generic Embeddings)
  Model: text-embedding-3-large
  Metrics: Baseline recall, precision
  Trigger: 10K+ RLCF pairs → TRANSITION to Phase 2

        ↓ (Sufficient data collected)

STATE: Phase 2 (Data Collection)
  Action: Aggregate query-document pairs
  Metrics: Feedback rate, pair quality
  Trigger: 50K+ pairs, quality >0.8 → TRANSITION to Phase 3

        ↓ (Training dataset ready)

STATE: Phase 3 (Fine-Tuned Model)
  Model: Fine-tuned multilingual-e5-large
  Training: Contrastive learning on RLCF pairs
  A/B Test: Phase 1 vs Phase 3
  Metrics: +15-20% recall improvement
  Trigger: 6 months stable, cost optimization needed → TRANSITION to Phase 5

        ↓ (Optimize for deployment)

STATE: Phase 5 (Distilled Model)
  Model: Distilled from Phase 3 (768 dims)
  Training: Knowledge distillation
  Metrics: 90-95% of Phase 3 quality, 3x faster
  Trigger: Continuous RLCF updates

        ↓ (Ongoing evolution)

CONTINUOUS: Weekly RLCF Updates
  Action: Incremental fine-tuning
  Metrics: Drift detection, quality monitoring
  Rollback: If quality degrades >5%
```

### RLCF Feedback Loop Architecture

**Weekly Cycle**:

```
Week N: Production Usage
  ├─ 500 queries processed
  ├─ 200 user feedback (40% feedback rate)
  ├─ 30 corrections (missing concepts)
  └─ 15 new query patterns identified

Week N → N+1: Aggregation & Analysis
  ├─ Build query-document pairs (positive + negative)
  ├─ Identify embedding drift (semantic shift)
  ├─ Calculate quality metrics (recall, precision, F1)
  └─ Decision: Update model? (IF drift > threshold)

Week N+1: Model Update (if triggered)
  ├─ Incremental fine-tuning on new RLCF data
  ├─ A/B test: v2.1 (10%) vs v2.0 (90%)
  ├─ Monitor: Recall, latency, user satisfaction
  └─ Gradual rollout: 10% → 50% → 100%

Week N+2: Validation
  ├─ Compare v2.1 vs v2.0 metrics
  ├─ IF v2.1 better: Complete rollout
  └─ IF v2.1 worse: Rollback to v2.0
```

### RLCF Data Schema

**User Feedback Schema**:
```json
{
  "feedback_id": "uuid",
  "query_id": "uuid",
  "query_text": "È valido un contratto firmato da un minorenne?",
  "retrieved_chunks": [
    {
      "chunk_id": "uuid-1",
      "text": "Art. 2 c.c. - La maggiore età...",
      "score": 0.89,
      "user_feedback": {
        "relevant": true,
        "rating": 5,
        "comment": "Risposta precisa"
      }
    },
    {
      "chunk_id": "uuid-2",
      "text": "Art. 1325 c.c. - I requisiti del contratto...",
      "score": 0.75,
      "user_feedback": {
        "relevant": false,
        "rating": 1,
        "comment": "Non pertinente alla domanda"
      }
    }
  ],
  "missing_chunks": [
    {
      "chunk_id": "uuid-1442",
      "text": "Art. 1442 c.c. - Il contratto è annullabile...",
      "user_suggested": true,
      "comment": "Questo articolo è rilevante ma non è stato trovato"
    }
  ],
  "timestamp": "ISO-8601",
  "user_id": "hashed_user_id"
}
```

**Training Pair Schema** (derived from feedback):
```json
{
  "training_triplet": {
    "anchor": "È valido un contratto firmato da un minorenne?",
    "positive": {
      "chunk_id": "uuid-1",
      "text": "Art. 2 c.c. - La maggiore età...",
      "feedback_score": 5,
      "feedback_count": 12
    },
    "hard_negative": {
      "chunk_id": "uuid-2",
      "text": "Art. 1325 c.c. - I requisiti del contratto...",
      "feedback_score": 1,
      "feedback_count": 8,
      "similarity_to_anchor": 0.75,
      "rationale": "Topically similar (contracts) but legally distinct (requirements vs capacity)"
    }
  },
  "training_weight": 0.85,
  "created_from_feedback_ids": ["feedback-uuid-1", "feedback-uuid-2"]
}
```

### Schema Evolution Strategy

**Version Management**:
```json
{
  "schema_version": "2.1",
  "version_date": "2025-01-15",
  "changes_from_previous": [
    {
      "change_type": "field_addition",
      "field": "retrieval_metadata.user_engagement_score",
      "rationale": "Track which chunks lead to user engagement",
      "backward_compatible": true
    },
    {
      "change_type": "field_modification",
      "field": "authority_metadata.authority_score",
      "old_calculation": "citation_count / max_citations",
      "new_calculation": "weighted_citations + user_feedback",
      "backward_compatible": true
    }
  ],
  "migration_required": false
}
```

**Schema Migration Protocol**:
```
IF schema_version updated:
  1. Backward compatibility check
     IF compatible:
       Deploy new schema, old data still queryable
     ELSE:
       Plan migration

  2. Migration strategy (if needed)
     - Batch re-processing of chunks
     - Update metadata fields
     - Preserve chunk_id (immutable)

  3. Validation
     - A/B test old vs new schema queries
     - Ensure no retrieval quality degradation

  4. Rollout
     - Gradual migration (10% → 50% → 100% of corpus)
```

### Continuous Improvement Metrics

**Quality Metrics Dashboard**:

| Metric | Week 1 | Week 4 | Week 12 | Week 24 | Target |
|--------|--------|--------|---------|---------|--------|
| Recall@20 | 65% | 72% | 78% | 85% | >80% |
| Precision@10 | 70% | 75% | 82% | 88% | >85% |
| User Satisfaction (1-5) | 3.2 | 3.6 | 4.0 | 4.3 | >4.0 |
| Feedback Rate | 25% | 35% | 42% | 48% | >40% |
| Query Latency p95 (ms) | 450 | 380 | 320 | 280 | <500 |
| Embedding Model Version | 1.0 | 1.0 | 2.0 | 2.1 | N/A |
| Corpus Size (chunks) | 500K | 750K | 1.2M | 1.8M | N/A |

**Improvement Triggers**:

| Condition | Action | Priority |
|-----------|--------|----------|
| Recall < 75% for 2 weeks | Investigate embedding quality, consider fine-tuning | High |
| User satisfaction < 3.5 | Review retrieval patterns, analyze negative feedback | High |
| Feedback rate < 30% | Improve UI/UX for feedback collection | Medium |
| Latency p95 > 800ms | Optimize index, consider sharding | High |
| New legal domain detected | Expand legal_area taxonomy, retrain classifiers | Medium |

---

## Summary

The Vector Database is a critical component of MERL-T that enables **semantic retrieval** over Italian legal text. This document has presented a **technology-agnostic blueprint** for the architecture, designed to be adaptive and evolving.

### Key Architectural Principles

1. **Complementary to Knowledge Graph**: VectorDB handles semantic similarity, KG handles structured relationships
2. **Bootstrap Evolution Strategy**: Start with generic embeddings (Phase 1), evolve to fine-tuned Italian legal models (Phase 3+) through RLCF
3. **Retrieval Pattern Catalog**: Six patterns (P1-P6) cover use cases from simple semantic search to complex multi-query retrieval with KG enrichment
4. **Agent-Orchestrated Access**: VectorDB Agent receives tasks from LLM Router, executes in parallel with KG/API Agents
5. **Metadata-Rich Schema**: Unified schema supports heterogeneous sources (norms, jurisprudence, doctrine) with rich temporal, authority, and classification metadata
6. **Performance Optimization**: Six patterns (OP1-OP6) enable sub-second queries at scale through caching, HNSW tuning, quantization, batching, sharding
7. **RLCF-Driven Evolution**: Weekly feedback loops refine embeddings, weekly updates improve retrieval quality over time

### Design Innovations

- **Hybrid Retrieval** (P2): Combines semantic (vector) + keyword (BM25) for balanced recall/precision
- **Temporal Filtering** (P3): Multivigenza support through metadata filtering
- **Multi-Query Expansion** (P5): Generates query variations for +20-30% recall improvement
- **Cross-Modal Enrichment** (P6): VectorDB semantic search + KG structural traversal for comprehensive context
- **Adaptive Embeddings**: Self-improving models through contrastive learning on RLCF query-document pairs
- **Technology Selection Framework**: Abstract interface requirements enable technology swapping without architecture changes

### Integration Points

- **Data Ingestion**: Metadata flows from Akoma Ntoso parsing → Entity extraction → VectorDB schema
- **Query Understanding**: Structured query with intent, entities, complexity → VectorDB task schema
- **LLM Router**: Decides when/how to activate VectorDB Agent based on query characteristics
- **Expert LLMs**: Retrieved chunks provide context for legal reasoning and synthesis
- **RLCF Loop**: User feedback → embedding refinement → quality improvement

### Validation Results

Four comprehensive examples demonstrate the architecture in action:
1. **Simple definition query**: Semantic search retrieves Art. 1414 + doctrinal explanation
2. **Temporal query**: Filtered retrieval finds correct DL 18/2020 version for March 2020
3. **Research query**: Multi-query + reranking achieves comprehensive smart working evolution coverage
4. **Hybrid query**: Keyword + semantic search ensures Art. 1325 is top result

### Evolution Path

The Vector Database architecture is designed to **evolve continuously**:
- **Months 1-3**: Generic embeddings (Phase 1), baseline metrics
- **Months 3-6**: RLCF data collection, training dataset assembly
- **Months 6-12**: Fine-tuned Italian legal embeddings (Phase 3), +15-20% recall
- **Months 12-18**: Domain specialization (Phase 4), precision gains
- **Months 18+**: Distilled models (Phase 5), cost optimization, ongoing RLCF updates

### Technology-Agnostic Commitment

This document intentionally contains **zero implementation code**. All retrieval patterns, optimization strategies, and integration protocols are described as:
- **JSON schemas** for data formats
- **ASCII diagrams** for workflows
- **Decision tables** for logic
- **Conceptual patterns** for algorithms

Implementation details for specific technologies (Weaviate, Qdrant, Pinecone, pgvector) are provided separately in:

**→ `/docs/03-implementation/vector-db-technologies.md`**

### Coherence with Methodology

This document aligns with MERL-T Section 02 methodology principles:
- ✅ Theoretical/agnostic: No technology-specific code
- ✅ Adaptive architecture: Components learn from RLCF data
- ✅ Traceable: All decisions logged with rationale
- ✅ Scalable: Optimization patterns support millions of chunks
- ✅ Robust: Hybrid approaches balance recall and precision

The Vector Database enables MERL-T to handle diverse legal queries—from precise article lookups to open-ended research—with high semantic precision and continuous quality improvement.

---

**Document Version**: 2.0 (Theoretical Architecture)
**Last Updated**: 2025-01-03
**Replaces**: vector-database.md v1.0 (implementation-heavy approach)
**Companion Document**: `/docs/03-implementation/vector-db-technologies.md`
**Cross-References**:
- `/docs/02-methodology/legal-reasoning.md` (Router orchestration, agent coordination)
- `/docs/02-methodology/query-understanding.md` (Query normalization, entity extraction)
- `/docs/02-methodology/knowledge-graph.md` (KG schema, Cypher patterns)
- `/docs/02-methodology/data-ingestion.md` (Metadata generation, chunking strategy)
