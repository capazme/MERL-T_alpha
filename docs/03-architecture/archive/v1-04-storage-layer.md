# Storage Layer Architecture

**Implementation Status**: 🚧 **PARZIALMENTE IMPLEMENTATO**
**Current Version**: v0.6.0
**Last Updated**: November 2025

**Implemented Components**:
- ✅ PostgreSQL: Orchestration tables, authentication, API keys, usage tracking
- ✅ Qdrant (VectorDB): Collection management, semantic search, 3 search patterns
- ✅ E5-large Embeddings: 1024-dim multilingual embeddings
- ✅ Data Ingestion Script: Multi-source support (Neo4j, JSON, PostgreSQL)
- ⏳ Neo4j/Memgraph: Schema defined, KG enrichment service ready, not yet deployed in production
- ⏳ Redis: Used for rate limiting, not yet for general caching

**Code Location**: `backend/orchestration/services/qdrant_service.py`, `backend/orchestration/services/embedding_service.py`, `scripts/ingest_legal_corpus.py`
**Tests**: `tests/orchestration/test_vectordb_agent.py`, `test_embedding_service.py`

---

## 1. Introduction

The **Storage Layer** is the foundation of MERL-T's knowledge infrastructure, consisting of three complementary storage systems plus a comprehensive data ingestion pipeline:

1. **Vector Database** (semantic similarity search over legal corpus)
2. **Knowledge Graph** (structured legal knowledge + relationships)
3. **PostgreSQL** (metadata, RLCF feedback, system state)
4. **Data Ingestion Pipeline** (parse, chunk, embed, enrich legal documents)

**Design Principles**:
- **Complementary Storage**: Each system optimized for different query patterns
- **Unified Metadata**: Single metadata schema across VectorDB + KG + PostgreSQL
- **Bootstrap Evolution**: Embeddings evolve from generic → fine-tuned → distilled (5 phases)
- **Continuous Ingestion**: Pipeline supports incremental updates (new laws, judgments)
- **RLCF-Driven**: Storage optimized based on community feedback

**Performance Targets**:
- Vector search: < 200ms (top-20, with filters)
- KG traversal: < 50ms (depth-3)
- Ingestion throughput: 1000 chunks/hour (single worker)

**Reference**: See `docs/02-methodology/vector-database.md`, `docs/02-methodology/knowledge-graph.md`, `docs/02-methodology/data-ingestion.md` for theoretical foundations.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION PIPELINE                   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Parse   │→ │  Chunk   │→ │  Embed   │→ │ Enrich   │   │
│  │ (Akoma   │  │(Semantic)│  │ (text-   │  │(Metadata)│   │
│  │  Ntoso,  │  │          │  │embedding)│  │          │   │
│  │   PDF)   │  │          │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
└─────────────┬────────────────────────────────────────────────┘
              ↓
   ┌──────────┴──────────┐
   │                     │
   ↓                     ↓
┌────────────────┐  ┌────────────────┐
│ VECTOR DATABASE│  │ KNOWLEDGE GRAPH│
│                │  │                │
│ • Chunks       │  │ • Norms        │
│ • Embeddings   │  │ • Concepts     │
│ • Metadata     │  │ • Sentenze     │
│ • HNSW Index   │  │ • Relationships│
│                │  │ • 23 node types│
│ • Weaviate     │  │ • Neo4j        │
└────────────────┘  └────────────────┘
         ↓                   ↓
         └───────────┬───────┘
                     ↓
         ┌───────────────────┐
         │   POSTGRESQL      │
         │                   │
         │ • Chunk metadata  │
         │ • RLCF feedback   │
         │ • User sessions   │
         │ • System state    │
         └───────────────────┘
```

**Data Flow**:
1. **Ingestion**: Legal documents → Pipeline → Chunks + Embeddings + Metadata
2. **Storage**: Chunks → VectorDB, Structured data → KG, Metadata → PostgreSQL
3. **Retrieval**: VectorDB Agent → Vector search, KG Agent → Graph traversal
4. **Feedback**: RLCF → PostgreSQL → Retrain embeddings → Update VectorDB

---

## 3. Vector Database Architecture

**Reference**: `docs/02-methodology/vector-database.md`

The Vector Database stores **semantic embeddings** of legal text chunks for fast similarity search.

### 3.1 HNSW Index

**HNSW** (Hierarchical Navigable Small World) is an approximate nearest neighbor algorithm optimized for high-dimensional vectors.

**Architecture**:

```
Vector Database Structure:

┌─────────────────────────────────────────────────────┐
│                 HNSW Index Layers                    │
│                                                      │
│  Layer 2 (coarse):   [Node A] ←→ [Node B]          │
│                         ↕           ↕               │
│  Layer 1 (medium):   [A1] [A2]  [B1] [B2]          │
│                       ↕    ↕      ↕    ↕            │
│  Layer 0 (fine):   [All 1M chunks, densely connected]│
│                                                      │
└─────────────────────────────────────────────────────┘

Search Strategy:
1. Start at Layer 2 (coarse navigation)
2. Find closest node at Layer 2
3. Descend to Layer 1
4. Find closest node at Layer 1
5. Descend to Layer 0
6. Exhaustive search in local neighborhood
7. Return top-k nearest neighbors

Complexity: O(log N) instead of O(N) for brute force
```

**HNSW Parameters**:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **M** | 16 | Max connections per node per layer (higher = better recall, more memory) |
| **ef_construction** | 128 | Size of dynamic candidate list during construction (higher = better index quality) |
| **ef_search** | 64 | Size of dynamic candidate list during search (higher = better recall, slower search) |
| **max_layers** | Auto (log N) | Number of hierarchical layers |

**Trade-offs**:
- **Recall vs Speed**: Higher `ef_search` → Better recall, slower search
- **Index Quality vs Build Time**: Higher `ef_construction` → Better index, slower build
- **Memory vs Recall**: Higher `M` → Better recall, more memory (~16 bytes per connection)

**Storage Requirements**:
- Vector dimension: 3072 (text-embedding-3-large)
- Vectors stored: 1,000,000 chunks
- Vector size: 3072 × 4 bytes (float32) = 12 KB per vector
- HNSW overhead: ~30% (connections)
- **Total**: 1M × 12KB × 1.3 = **~15.6 GB**

---

### 3.2 Metadata Filter Engine

**Purpose**: Apply metadata constraints to narrow search space before vector similarity.

**Filter Architecture**:

```
┌────────────────────────────────────────────────────┐
│ Query with Filters                                 │
│ {                                                  │
│   "query": "risoluzione contratto",                │
│   "filters": {                                     │
│     "temporal_metadata.is_current": true,          │
│     "classification.legal_area": "civil",          │
│     "authority_metadata.hierarchical_level":       │
│       ["Costituzione", "Legge Ordinaria"]          │
│   }                                                │
│ }                                                  │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ STEP 1: Metadata Filtering (Pre-filtering)        │
│   Apply boolean filters to metadata               │
│   Reduce search space from 1M → 200K chunks       │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ STEP 2: Vector Search (HNSW on filtered set)      │
│   Search only within filtered 200K chunks          │
│   Retrieve top-20 by cosine similarity             │
└──────────────────┬─────────────────────────────────┘
                   ↓
           Top-20 Results
```

**Filter Types**:

| Filter Category | Metadata Fields | Example |
|----------------|----------------|---------|
| **Temporal** | `temporal_metadata.is_current`<br>`temporal_metadata.date_effective`<br>`temporal_metadata.date_end` | Current law only: `is_current = true`<br>Historical: `date_effective <= 2010-01-01` |
| **Hierarchical** | `authority_metadata.hierarchical_level`<br>`authority_metadata.binding_force` | Constitutional level: `["Costituzione", "Legge Costituzionale"]` |
| **Domain** | `classification.legal_area`<br>`classification.legal_domain_tags` | Civil law: `legal_area = "civil"` |
| **Document Type** | `document_type` | Norms only: `document_type = "norm"` |
| **Entity** | `entities_extracted.norm_references`<br>`entities_extracted.case_references` | References Art. 1453: `norm_references contains "art_1453_cc"` |

**Performance**:
- Filter evaluation: ~5ms (indexed metadata fields)
- Reduction ratio: Typically 1M → 100K-500K (depends on filter selectivity)
- Combined (filter + search): ~150ms (vs 200ms without filtering)

---

### 3.3 Hybrid Search Combiner

**Purpose**: Combine semantic similarity (vector) with keyword matching (BM25) for better recall.

**Architecture**:

```
Query: "risoluzione per inadempimento"
            ↓
    ┌───────┴───────┐
    │               │
    ↓               ↓
┌─────────────┐  ┌─────────────┐
│ Vector      │  │ Keyword     │
│ Search      │  │ Search      │
│ (HNSW)      │  │ (BM25)      │
└──────┬──────┘  └──────┬──────┘
       │                │
       ↓                ↓
  vector_scores    keyword_scores
  (cosine sim)     (BM25 score)
       │                │
       └────────┬───────┘
                ↓
      ┌──────────────────┐
      │ Score Fusion     │
      │ combined =       │
      │ α·vector +       │
      │ (1-α)·keyword    │
      └────────┬─────────┘
               ↓
        Hybrid Rankings
```

**Score Fusion Algorithm**:

```
Input:
- query: "risoluzione per inadempimento"
- alpha: 0.7 (weighting parameter)

Step 1: Vector Search
- Embed query → query_vector [3072 dims]
- HNSW search → top-100 candidates with cosine_scores

Step 2: Keyword Search (BM25)
- Tokenize query → ["risoluzione", "inadempimento"]
- BM25 scoring → top-100 candidates with bm25_scores

Step 3: Normalize Scores
- vector_norm = (cosine - min) / (max - min)  → [0, 1]
- keyword_norm = (bm25 - min) / (max - min)   → [0, 1]

Step 4: Fuse Scores
- For each chunk appearing in either result set:
    combined_score = alpha * vector_norm + (1 - alpha) * keyword_norm

Step 5: Rerank
- Sort chunks by combined_score descending
- Return top-k

Output: Top-k chunks with hybrid ranking
```

**Alpha Parameter Tuning**:

| Alpha | Vector Weight | Keyword Weight | Use Case |
|-------|--------------|---------------|----------|
| **1.0** | 100% | 0% | Pure semantic (conceptual similarity) |
| **0.8** | 80% | 20% | Semantic-heavy (default for case law) |
| **0.7** | 70% | 30% | Balanced (default for norms) |
| **0.5** | 50% | 50% | Equal weight |
| **0.3** | 30% | 70% | Keyword-heavy (exact term matching) |
| **0.0** | 0% | 100% | Pure keyword (legacy search) |

**Performance**:
- Vector search: ~100ms
- BM25 search: ~50ms
- Parallel execution: max(100, 50) = ~100ms
- Score fusion: ~10ms
- **Total**: ~110ms (vs 100ms for vector-only)

---

### 3.4 Cross-Encoder Reranker

**Purpose**: Two-stage retrieval for higher precision (HNSW recall stage + BERT reranking stage).

**Architecture**:

```
Stage 1: RECALL (Fast, Lower Precision)
┌────────────────────────────────────┐
│ Semantic Search (HNSW)             │
│ Retrieve top-50 candidates         │
│ Latency: ~100ms                    │
└──────────────┬─────────────────────┘
               ↓
        Top-50 Candidates
               ↓
Stage 2: PRECISION (Slow, Higher Precision)
┌────────────────────────────────────┐
│ Cross-Encoder BERT Reranking       │
│                                    │
│ For each of 50 candidates:         │
│   Input: [CLS] query [SEP] chunk  │
│   BERT inference → relevance score │
│                                    │
│ Latency: ~40ms × 50 = 2000ms      │
└──────────────┬─────────────────────┘
               ↓
         Reranked top-10
```

**Cross-Encoder Model**:

```json
{
  "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "fine_tuned_on": "italian_legal_triplets",
  "training_data": {
    "size": 5000,
    "format": "(query, chunk, relevance_label)",
    "source": "RLCF feedback"
  },
  "input_format": "[CLS] query [SEP] chunk_text [SEP]",
  "output": "relevance_score (0.0-1.0)",
  "max_input_length": 512,
  "latency": "~40ms per pair"
}
```

**Processing Logic**:

```
Input: query = "È valido un contratto firmato da un minorenne?"
       candidates = [chunk_1, chunk_2, ..., chunk_50]

For each candidate_i in candidates:
    # Construct input for BERT
    bert_input = f"[CLS] {query} [SEP] {candidate_i.text[:500]} [SEP]"

    # BERT inference
    relevance_score_i = cross_encoder_model(bert_input)

    # Store score
    candidate_i.rerank_score = relevance_score_i

# Sort by rerank_score
ranked_candidates = sort(candidates, key=rerank_score, descending=True)

# Return top-10
return ranked_candidates[:10]
```

**Performance**:
- **Candidate count**: 50 (recall stage)
- **Final count**: 10 (precision stage)
- **Latency**: ~2s (50 × 40ms)
- **Accuracy improvement**: +15% precision@10 (vs vector-only)

**When to Use**:
- Query complexity > 0.6 (medium/high)
- Intent = `validità_atto` (requires precision)
- User requests "accurate" results

---

### 3.5 Unified Metadata Schema

**Reference**: `docs/02-methodology/vector-database.md` §3, `docs/02-methodology/data-ingestion.md` §4

**Full Metadata Schema** (stored with each chunk):

```json
{
  "chunk_metadata": {
    "chunk_id": "uuid",
    "document_id": "uuid (parent document)",
    "document_type": "norm | jurisprudence | doctrine",

    "temporal_metadata": {
      "date_published": "2023-06-15",
      "date_effective": "2023-07-01",
      "date_end": null,
      "is_current": true,
      "version_id": "art_1453_cc_v3"
    },

    "classification": {
      "legal_area": "civil | criminal | administrative | constitutional",
      "legal_domain_tags": ["contract", "obligation", "termination"],
      "complexity_level": 0.6,
      "hierarchical_level": "Legge Ordinaria"
    },

    "authority_metadata": {
      "hierarchical_level": "Costituzione | Legge Costituzionale | Legge Ordinaria | Regolamento",
      "binding_force": 0.95,
      "authority_score": 0.88,
      "citation_count": 1542
    },

    "kg_links": {
      "primary_article_id": "art_1453_cc",
      "referenced_norm_ids": ["art_1454_cc", "art_1455_cc"],
      "related_concept_ids": ["risoluzione_contratto", "inadempimento"],
      "jurisprudence_cluster_id": "cluster_inadempimento_2023"
    },

    "entities_extracted": {
      "norm_references": ["art_1453_cc", "art_1418_cc"],
      "case_references": ["cass_2023_12567"],
      "legal_concepts": ["risoluzione", "inadempimento", "contratto"],
      "named_entities": {
        "persons": [],
        "organizations": [],
        "courts": ["Cassazione"]
      }
    },

    "ingestion_metadata": {
      "source_url": "https://www.normattiva.it/...",
      "ingestion_date": "2024-01-15T10:30:00Z",
      "parser_version": "v2.1",
      "embedding_model": "text-embedding-3-large",
      "embedding_phase": 2
    }
  }
}
```

**Metadata Inheritance**:
- Document-level metadata → All chunks from same document
- Version-aware: Each version of norm has separate chunks
- Dynamic enrichment: Metadata updated when new relationships discovered in KG

---

## 4. Knowledge Graph Architecture

**Reference**: `docs/02-methodology/knowledge-graph.md`

The Knowledge Graph stores **structured legal knowledge** with rich relationships.

### 4.1 Neo4j Schema

**Node Types** (23 total):

```
LEGAL DOCUMENTS (5 node types):
┌───────────────────────────────────────────────────┐
│ 1. Norma                                          │
│    - Costituzione, Legge, DL, D.Lgs, Regolamento │
│                                                   │
│ 2. Versione                                       │
│    - Temporal version of Norma (multivigenza)    │
│                                                   │
│ 3. Comma / Lettera / Numero                      │
│    - Fine-grained article structure              │
│                                                   │
│ 4. AttoGiudiziario                               │
│    - Sentenze, Ordinanze, Decreti                │
│                                                   │
│ 5. Dottrina                                       │
│    - Legal scholarship, commentaries             │
└───────────────────────────────────────────────────┘

LEGAL ENTITIES (4 node types):
┌───────────────────────────────────────────────────┐
│ 6. SoggettoGiuridico                             │
│    - Legal persons (natural, juridical)          │
│                                                   │
│ 7. OrganoGiurisdizionale                         │
│    - Courts (Cassazione, TAR, Corte Cost.)       │
│                                                   │
│ 8. OrganoAmministrativo                          │
│    - Administrative bodies (Ministero, Agenzia)  │
│                                                   │
│ 9. RuoloGiuridico                                │
│    - Legal roles (creditore, debitore, erede)    │
└───────────────────────────────────────────────────┘

LEGAL CONCEPTS (3 node types):
┌───────────────────────────────────────────────────┐
│ 10. ConcettoGiuridico                            │
│     - Abstract legal concepts (contratto, proprietà)│
│                                                   │
│ 11. DefinizioneLegale                            │
│     - Legal definitions from norms               │
│                                                   │
│ 12. PrincipioGiuridico                           │
│     - Legal principles (buona fede, certezza)    │
└───────────────────────────────────────────────────┘

LEGAL RELATIONS (4 node types):
┌───────────────────────────────────────────────────┐
│ 13. DirittoSoggettivo                            │
│     - Subjective rights (ownership, credit)      │
│                                                   │
│ 14. InteresseLegittimo                           │
│     - Legitimate interests (administrative law)  │
│                                                   │
│ 15. ModalitàGiuridica                            │
│     - Legal modalities (conditions, terms)       │
│                                                   │
│ 16. Responsabilità                               │
│     - Legal liability types                      │
└───────────────────────────────────────────────────┘

PROCEDURES & CONSEQUENCES (4 node types):
┌───────────────────────────────────────────────────┐
│ 17. Procedura                                     │
│     - Legal procedures (trial, appeal)           │
│                                                   │
│ 18. FattoGiuridico                               │
│     - Legal facts (birth, death, contract)       │
│                                                   │
│ 19. Caso                                          │
│     - Legal cases (fact patterns)                │
│                                                   │
│ 20. Sanzione / Termine                           │
│     - Sanctions and deadlines                    │
└───────────────────────────────────────────────────┘

EU INTEGRATION (2 node types):
┌───────────────────────────────────────────────────┐
│ 21. DirettivaUE                                   │
│     - EU directives                              │
│                                                   │
│ 22. RegolamentoUE                                │
│     - EU regulations                             │
└───────────────────────────────────────────────────┘

REASONING (1 node type):
┌───────────────────────────────────────────────────┐
│ 23. Regola / ProposizioneGiuridica               │
│     - Inference rules (if-then patterns)         │
└───────────────────────────────────────────────────┘
```

---

### 4.2 Relationship Types (65 total, 11 categories)

**Relationship Categories**:

```
1. HIERARCHICAL RELATIONSHIPS (7 types)
┌──────────────────────────────────────────────────┐
│ - GERARCHIA_KELSENIANA                           │
│   (Costituzione → Legge → Regolamento)           │
│                                                  │
│ - ABROGA / MODIFICA / SOSTITUISCE                │
│   (Norm evolution)                               │
│                                                  │
│ - ATTUAZIONE / DELEGA                            │
│   (Implementation relationships)                 │
│                                                  │
│ - HA_VERSIONE                                    │
│   (Norm → Version, for multivigenza)             │
└──────────────────────────────────────────────────┘

2. CITATION RELATIONSHIPS (5 types)
┌──────────────────────────────────────────────────┐
│ - CITA / RICHIAMA / RINVIA                       │
│   (Cross-references between norms)               │
│                                                  │
│ - INTERPRETA / APPLICA                           │
│   (Jurisprudence → Norm)                         │
└──────────────────────────────────────────────────┘

3. CONCEPTUAL RELATIONSHIPS (8 types)
┌──────────────────────────────────────────────────┐
│ - DISCIPLINATO_DA                                │
│   (Concept → Norm)                               │
│                                                  │
│ - RELAZIONE_CONCETTUALE                          │
│   (Concept ← → Concept)                          │
│   Subtypes: prerequisito, conseguenza,           │
│             alternativa, eccezione               │
│                                                  │
│ - DEFINISCE / SPECIFICA                          │
│   (Norm → Definition)                            │
│                                                  │
│ - ISTANZIA / GENERALIZZA                         │
│   (Concept hierarchy)                            │
└──────────────────────────────────────────────────┘

4. PROCEDURAL RELATIONSHIPS (6 types)
┌──────────────────────────────────────────────────┐
│ - PRESUPPONE / RICHIEDE                          │
│   (Procedural dependencies)                      │
│                                                  │
│ - PRECEDE / SEGUE                                │
│   (Temporal sequence)                            │
│                                                  │
│ - ALTERNATIVA_A / ESCLUDE                        │
│   (Mutual exclusivity)                           │
└──────────────────────────────────────────────────┘

5. SUBJECT-OBJECT RELATIONSHIPS (7 types)
┌──────────────────────────────────────────────────┐
│ - HA_DIRITTO / HA_OBBLIGO                        │
│   (Subject → Right/Obligation)                   │
│                                                  │
│ - ESERCITA / TUTELA                              │
│   (Subject → Action)                             │
│                                                  │
│ - LESO / PROTETTO                                │
│   (Harm/Protection relationships)                │
│                                                  │
│ - PROPRIETARIO_DI / DETENTORE_DI                 │
│   (Ownership relationships)                      │
└──────────────────────────────────────────────────┘

6. TEMPORAL RELATIONSHIPS (4 types)
┌──────────────────────────────────────────────────┐
│ - VALIDO_DA / VALIDO_FINO_A                      │
│   (Temporal validity)                            │
│                                                  │
│ - CONTEMPORANEO_A / POSTERIORE_A                 │
│   (Temporal ordering)                            │
└──────────────────────────────────────────────────┘

7. CAUSAL RELATIONSHIPS (6 types)
┌──────────────────────────────────────────────────┐
│ - CAUSA / EFFETTO                                │
│   (Causa → Effetto)                              │
│                                                  │
│ - PRODUCE / ESTINGUE                             │
│   (Legal consequence relationships)              │
│                                                  │
│ - INVALIDA / ANNULLA                             │
│   (Invalidation relationships)                   │
│                                                  │
│ - CONDIZIONATO_DA / SUBORDINATO_A                │
│   (Conditional relationships)                    │
└──────────────────────────────────────────────────┘

8. JURISPRUDENCE RELATIONSHIPS (5 types)
┌──────────────────────────────────────────────────┐
│ - INTERPRETA / CONFERMA / RIBALTA                │
│   (Sentenza → Norm/Sentenza)                     │
│                                                  │
│ - PRECEDENTE_DI / SEGUITO_DA                     │
│   (Case law evolution)                           │
└──────────────────────────────────────────────────┘

9. CONFLICT RELATIONSHIPS (4 types)
┌──────────────────────────────────────────────────┐
│ - CONTRASTA_CON / IN_CONFLITTO_CON               │
│   (Norm ←conflict→ Norm)                         │
│                                                  │
│ - DEROGA / INTEGRA                               │
│   (Exception/Integration)                        │
└──────────────────────────────────────────────────┘

10. EU INTEGRATION RELATIONSHIPS (6 types)
┌──────────────────────────────────────────────────┐
│ - RECEPISCE / ATTUA_DIRETTIVA                    │
│   (Italian norm → EU directive)                  │
│                                                  │
│ - CONFORMITA_A / VIOLAZIONE_DI                   │
│   (Norm ←→ EU law)                               │
│                                                  │
│ - RINVIO_PREGIUDIZIALE / DISAPPLICAZIONE         │
│   (CGUE interaction)                             │
└──────────────────────────────────────────────────┘

11. META RELATIONSHIPS (7 types)
┌──────────────────────────────────────────────────┐
│ - COMMENTATO_DA / ANALIZZATO_DA                  │
│   (Norm → Dottrina)                              │
│                                                  │
│ - FONTE / DERIVATO_DA                            │
│   (Source tracking)                              │
│                                                  │
│ - CORRELATO_A / SIMILE_A / ESEMPIO_DI            │
│   (Analogical relationships)                     │
└──────────────────────────────────────────────────┘
```

**Relationship Properties**:

```cypher
// Example relationship with properties
(:Norma {id: "art_1453_cc"})-[
  r:DISCIPLINATO_DA {
    strength: 0.95,
    relationship_type: "prerequisito",
    established_by: "legislator",
    date_established: "1942-03-16"
  }
]->(:ConcettoGiuridico {id: "risoluzione_contratto"})
```

---

### 4.3 Query Patterns

**Common Query Patterns**:

**Pattern 1: Concept-to-Norm Mapping**
```cypher
// Find norms that discipline a concept
MATCH (c:ConcettoGiuridico {id: $concept_id})-[:DISCIPLINATO_DA]->(n:Norma)
OPTIONAL MATCH (n)-[:HA_VERSIONE]->(v:Versione)
WHERE v.is_current = true OR v IS NULL
RETURN n, v
ORDER BY n.hierarchical_level DESC
LIMIT 10
```

**Pattern 2: Hierarchical Traversal**
```cypher
// Find parent norms in Kelsenian hierarchy
MATCH path = (parent:Norma)-[:GERARCHIA_KELSENIANA*1..3]->(child:Norma {id: $norm_id})
RETURN parent, length(path) AS distance
ORDER BY distance ASC
```

**Pattern 3: Related Concepts Discovery**
```cypher
// Find related concepts via multi-hop traversal
MATCH path = (c1:ConcettoGiuridico {id: $concept_id})-[:RELAZIONE_CONCETTUALE*1..2]-(c2:ConcettoGiuridico)
WHERE ALL(r IN relationships(path) WHERE r.relationship_type IN $allowed_types)
WITH c2, path,
     reduce(strength = 1.0, r IN relationships(path) | strength * r.strength) AS path_strength
RETURN c2, path_strength
ORDER BY path_strength DESC
LIMIT 10
```

**Pattern 4: Jurisprudence Lookup**
```cypher
// Find case law interpreting a norm
MATCH (n:Norma {id: $norm_id})<-[:INTERPRETA]-(s:AttoGiudiziario)
WHERE s.document_type = 'sentenza'
  AND s.court IN ['Cassazione', 'Corte Costituzionale']
RETURN s
ORDER BY s.date_published DESC
LIMIT 5
```

---

## 5. PostgreSQL Architecture

### 5.1 Metadata Storage

**Purpose**: Store chunk metadata for faster filtering (alternative to Neo4j for simple queries).

**Schema**:

```sql
-- Chunks table (primary metadata)
CREATE TABLE chunks (
    chunk_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'norm', 'jurisprudence', 'doctrine'
    text TEXT NOT NULL,

    -- Temporal metadata
    date_published DATE,
    date_effective DATE,
    date_end DATE,
    is_current BOOLEAN DEFAULT true,
    version_id VARCHAR(100),

    -- Classification
    legal_area VARCHAR(50),
    legal_domain_tags TEXT[], -- Array of tags
    complexity_level FLOAT,
    hierarchical_level VARCHAR(100),

    -- Authority
    binding_force FLOAT,
    authority_score FLOAT,
    citation_count INTEGER,

    -- KG links
    primary_article_id VARCHAR(100),
    referenced_norm_ids TEXT[],
    related_concept_ids TEXT[],

    -- Ingestion
    ingestion_date TIMESTAMP DEFAULT NOW(),
    embedding_model VARCHAR(100),
    embedding_phase INTEGER,

    -- Indexes
    CONSTRAINT valid_document_type CHECK (document_type IN ('norm', 'jurisprudence', 'doctrine'))
);

-- Indexes for fast filtering
CREATE INDEX idx_chunks_is_current ON chunks(is_current);
CREATE INDEX idx_chunks_legal_area ON chunks(legal_area);
CREATE INDEX idx_chunks_document_type ON chunks(document_type);
CREATE INDEX idx_chunks_hierarchical_level ON chunks(hierarchical_level);
CREATE INDEX idx_chunks_date_effective ON chunks(date_effective);
CREATE INDEX idx_chunks_primary_article ON chunks(primary_article_id);

-- GIN index for array fields (fast containment queries)
CREATE INDEX idx_chunks_domain_tags ON chunks USING GIN(legal_domain_tags);
CREATE INDEX idx_chunks_referenced_norms ON chunks USING GIN(referenced_norm_ids);
```

---

### 5.2 RLCF Feedback Storage

**Purpose**: Store community feedback for RLCF learning loops.

**Schema**:

```sql
-- User feedback on answers
CREATE TABLE answer_feedback (
    feedback_id UUID PRIMARY KEY,
    trace_id VARCHAR(100) NOT NULL, -- Links to query execution
    user_id UUID NOT NULL,
    user_authority_score FLOAT NOT NULL, -- Dynamic authority (0.0-1.0)

    -- Feedback content
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    corrections JSONB, -- Structured corrections

    -- Context
    query_text TEXT NOT NULL,
    final_answer TEXT NOT NULL,
    execution_plan JSONB,
    expert_outputs JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 5)
);

CREATE INDEX idx_feedback_trace_id ON answer_feedback(trace_id);
CREATE INDEX idx_feedback_user_id ON answer_feedback(user_id);
CREATE INDEX idx_feedback_rating ON answer_feedback(rating);
CREATE INDEX idx_feedback_created_at ON answer_feedback(created_at);


-- Training examples derived from feedback
CREATE TABLE training_examples (
    example_id UUID PRIMARY KEY,
    feedback_id UUID REFERENCES answer_feedback(feedback_id),

    example_type VARCHAR(50) NOT NULL, -- 'router_decision', 'embedding_triplet', 'entity_annotation', etc.

    -- Training data
    input_data JSONB NOT NULL,
    expected_output JSONB NOT NULL,

    -- Metadata
    quality_score FLOAT, -- How good is this training example (0.0-1.0)
    used_in_training BOOLEAN DEFAULT false,
    training_run_id UUID,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_training_examples_type ON training_examples(example_type);
CREATE INDEX idx_training_examples_quality ON training_examples(quality_score);
```

---

## 6. Data Ingestion Pipeline

**Reference**: `docs/02-methodology/data-ingestion.md`

The Data Ingestion Pipeline transforms raw legal documents into searchable chunks with embeddings and metadata.

### 6.1 Pipeline Overview

```
┌────────────────────────────────────────────────────────┐
│ Stage 1: PARSING                                       │
│   Akoma Ntoso XML/JSON → Structured Norm              │
│   PDF (Sentenze) → Extracted Text                     │
│   Latency: ~500ms per document                        │
└──────────────────┬─────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────────┐
│ Stage 2: CHUNKING                                      │
│   Semantic chunking with overlap                      │
│   Norms: Article-level (1 article = 1 chunk)          │
│   Sentenze: Section-based (fatto, diritto, dispositivo)│
│   Dottrina: Similarity-based (threshold=0.72)         │
│   Latency: ~200ms per document                        │
└──────────────────┬─────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────────┐
│ Stage 3: EMBEDDING GENERATION                          │
│   text-embedding-3-large (Phase 1-2)                  │
│   Fine-tuned legal embeddings (Phase 3+)              │
│   Latency: ~50ms per chunk (batched)                  │
└──────────────────┬─────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────────┐
│ Stage 4: METADATA ENRICHMENT                           │
│   - Temporal metadata extraction                      │
│   - Entity extraction (NER)                            │
│   - Classification (legal area, complexity)           │
│   - Authority scoring                                  │
│   - KG linking (norm IDs, concept IDs)                │
│   Latency: ~300ms per chunk                           │
└──────────────────┬─────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────────┐
│ Stage 5: STORAGE                                       │
│   - VectorDB: chunk + embedding + metadata            │
│   - PostgreSQL: chunk metadata                        │
│   - Neo4j: structured entities + relationships        │
│   Latency: ~100ms per chunk                           │
└────────────────────────────────────────────────────────┘

Total Pipeline Latency: ~1.15s per chunk
Throughput: 1 worker = ~3,000 chunks/hour
Parallelizable: N workers = N × 3,000 chunks/hour
```

---

### 6.2 Norm Parser (Akoma Ntoso)

**Input**: Akoma Ntoso XML/JSON from Italian Government API

**Processing**:

```
Akoma Ntoso Document (XML)
         ↓
┌──────────────────────────────┐
│ 1. Parse XML Structure       │
│    Extract: meta, body, annex│
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 2. Extract Metadata          │
│    - Title, date, source     │
│    - Hierarchical level      │
│    - Effective dates         │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 3. Parse Article Structure   │
│    - Articles (Art. 1, 2...) │
│    - Commas (comma 1, 2...)  │
│    - Letters (lett. a, b...) │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 4. Extract Full Text         │
│    Concatenate article text  │
└──────────┬───────────────────┘
           ↓
   Structured Norm Object
```

**Output Example**:

```json
{
  "norm": {
    "norm_id": "art_1453_cc",
    "source": "Codice Civile",
    "article": "1453",
    "title": "Risoluzione per inadempimento",
    "hierarchical_level": "Legge Ordinaria",
    "date_published": "1942-03-16",
    "date_effective": "1942-03-16",
    "is_current": true,
    "structure": {
      "commas": [
        {
          "comma_num": 1,
          "text": "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno."
        }
      ]
    },
    "full_text": "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno."
  }
}
```

---

### 6.3 PDF Processor (Sentenze)

**Input**: PDF files of court decisions (sentenze)

**Processing**:

```
PDF File
    ↓
┌──────────────────────────────┐
│ 1. OCR (if scanned)          │
│    Tesseract OCR             │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 2. Layout Analysis           │
│    Detect sections:          │
│    - Intestazione (header)   │
│    - Fatto (facts)           │
│    - Diritto (law)           │
│    - Dispositivo (ruling)    │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 3. Text Extraction           │
│    Extract text per section  │
└──────────┬───────────────────┘
           ↓
┌──────────────────────────────┐
│ 4. Metadata Extraction       │
│    - Court, date, case number│
│    - Parties, judges         │
│    - Norms cited             │
└──────────┬───────────────────┘
           ↓
  Structured Sentenza Object
```

**Output Example**:

```json
{
  "sentenza": {
    "sentenza_id": "cass_2023_12567",
    "court": "Cassazione",
    "section": "Civile, Sezione III",
    "date_published": "2023-06-15",
    "case_number": "12567/2023",
    "sections": {
      "fatto": "Il ricorrente ha stipulato un contratto di compravendita...",
      "diritto": "La Corte rileva che l'Art. 1453 c.c. prevede...",
      "dispositivo": "La Corte rigetta il ricorso."
    },
    "norms_cited": ["art_1453_cc", "art_1454_cc"],
    "binding_force": 0.85
  }
}
```

---

### 6.4 Semantic Chunking Engine

**Purpose**: Split documents into semantically coherent chunks.

**Chunking Strategies** (by document type):

| Document Type | Strategy | Chunk Size | Overlap | Rationale |
|--------------|----------|-----------|---------|-----------|
| **Norms** | Article-level | 1 article | 0 tokens | Legal articles are atomic units |
| **Jurisprudence** | Section-based | 1 section (fatto/diritto/dispositivo) | 50 tokens | Sections are semantically distinct |
| **Doctrine** | Similarity-based | Dynamic (max 1024 tokens) | 100 tokens | Paragraphs may span multiple semantic units |

**Similarity-Based Chunking** (for Doctrine):

```
Input: Document text = [sent_1, sent_2, ..., sent_N]

Step 1: Sentence Embeddings
For each sentence sent_i:
    embed_i = embedding_model(sent_i)

Step 2: Compute Sentence Similarities
For i = 1 to N-1:
    similarity_i = cosine_similarity(embed_i, embed_{i+1})

Step 3: Identify Chunk Boundaries
boundaries = []
For i = 1 to N-1:
    if similarity_i < threshold (0.72):
        boundaries.append(i)  # Break here

Step 4: Create Chunks with Overlap
chunks = []
For each boundary pair (start, end):
    chunk_text = sent_start...sent_end
    if len(chunk_text) > max_tokens (1024):
        split further
    chunks.append(chunk_text)

Output: Array of chunks
```

**Performance**:
- Embedding sentences: ~20ms per sentence (batched)
- Similarity computation: ~5ms per pair
- Total: ~200ms per document (avg 20 sentences)

---

### 6.5 Embedding Generation Service

**Reference**: `docs/02-methodology/vector-database.md` §4

**5-Phase Bootstrap Evolution**:

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Generic Embeddings (Bootstrap)                 │
│   Model: text-embedding-3-large (OpenAI)                │
│   No fine-tuning, zero-shot                             │
│   Quality: Baseline                                     │
│   Timeline: Week 1-4                                    │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Italian Legal Corpus Pre-training              │
│   Model: multilingual-e5-large                          │
│   Pre-training on Italian legal corpus (unsupervised)   │
│   Quality: +10% vs Phase 1                              │
│   Timeline: Week 5-8                                    │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Contrastive Fine-Tuning (RLCF data)            │
│   Model: Fine-tuned from Phase 2                        │
│   Training data: Anchor-Positive-Negative triplets      │
│     from RLCF feedback (query, relevant_chunk, irrelevant_chunk)│
│   Loss: Contrastive loss (triplet margin loss)          │
│   Quality: +20% vs Phase 1                              │
│   Timeline: Week 9-16 (accumulate RLCF data)            │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: Domain-Specific Hard Negative Mining           │
│   Model: Fine-tuned from Phase 3                        │
│   Training data: RLCF + Hard negatives                  │
│     (chunks semantically similar but legally distinct)  │
│   Quality: +25% vs Phase 1                              │
│   Timeline: Week 17-24                                  │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 5: Knowledge Distillation (Deployment Optimization)│
│   Model: Distilled from Phase 4                         │
│   Size: 768 dims (vs 1024 Phase 4) → 3x faster          │
│   Quality: +22% vs Phase 1 (slight drop from Phase 4)   │
│   Timeline: Week 25+                                    │
└─────────────────────────────────────────────────────────┘
```

**Training Data for Phase 3+**:

```json
{
  "triplet_example": {
    "anchor": "È valido un contratto firmato da un minorenne?",
    "positive": "Art. 2 c.c. - La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti...",
    "negative": "Art. 1350 c.c. - Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità: 1) i contratti che trasferiscono la proprietà di beni immobili...",
    "source": "rlcf_feedback",
    "feedback_id": "uuid",
    "user_authority": 0.85
  }
}
```

**Performance Evolution**:

| Phase | Model | Dims | Latency (per chunk) | Quality (MRR@10) |
|-------|-------|------|---------------------|------------------|
| 1 | text-embedding-3-large | 3072 | 50ms | 0.60 (baseline) |
| 2 | multilingual-e5-large | 1024 | 30ms | 0.66 (+10%) |
| 3 | Fine-tuned (contrastive) | 1024 | 30ms | 0.72 (+20%) |
| 4 | Fine-tuned (hard neg) | 1024 | 30ms | 0.75 (+25%) |
| 5 | Distilled | 768 | 15ms | 0.73 (+22%) |

---

### 6.6 Metadata Enrichment Pipeline

**Enrichment Steps**:

```
Chunk Text
    ↓
┌──────────────────────────────────────┐
│ 1. Temporal Metadata Extraction      │
│    - date_published (from source)    │
│    - date_effective (from Akoma Ntoso│
│    - is_current (check date_end)     │
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ 2. Entity Extraction (NER)           │
│    - norm_references                 │
│    - case_references                 │
│    - legal_concepts                  │
│    - named_entities (courts, persons)│
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ 3. Classification                    │
│    - legal_area (civil, criminal...) │
│    - legal_domain_tags (ML model)    │
│    - complexity_level (0.0-1.0)      │
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ 4. Authority Scoring                 │
│    - hierarchical_level              │
│    - binding_force (based on court)  │
│    - authority_score (citation_count)│
└──────────┬───────────────────────────┘
           ↓
┌──────────────────────────────────────┐
│ 5. KG Linking                        │
│    - primary_article_id              │
│    - referenced_norm_ids             │
│    - related_concept_ids (KG lookup) │
└──────────┬───────────────────────────┘
           ↓
   Enriched Chunk Metadata
```

**Performance**: ~300ms per chunk (NER + classification + KG lookup)

---

## 7. Technology Mapping

### 7.1 Vector Database

| Component | Technology Options | Recommended | Rationale |
|-----------|-------------------|------------|-----------|
| **Vector DB** | • Weaviate<br>• Qdrant<br>• Pinecone<br>• pgvector | **Weaviate** | Hybrid search native, open-source, GraphQL API |
| **Embedding Model** | • text-embedding-3-large<br>• multilingual-e5-large<br>• Fine-tuned legal | **text-embedding-3-large** (Phase 1-2)<br>**Fine-tuned** (Phase 3+) | Best quality for Italian legal domain |
| **Cross-Encoder** | • ms-marco-MiniLM<br>• Legal-BERT fine-tuned | **ms-marco fine-tuned on legal data** | Balance speed/accuracy |

**Decision Tree for Vector DB**:

```
Need managed service (no ops)?
  ├─ YES → Pinecone (managed, proprietary)
  └─ NO  → Need hybrid search native?
             ├─ YES → Weaviate (open-source, self-hosted)
             └─ NO  → Qdrant (open-source, simpler)
```

---

### 7.2 Knowledge Graph

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Graph DB** | Neo4j Enterprise | Industry standard, best Cypher support, APOC plugins |
| **Graph Algorithms** | Neo4j GDS (Graph Data Science) | Shortest path, community detection for jurisprudence clustering |

---

### 7.3 Data Ingestion

| Component | Technology Options | Recommended | Rationale |
|-----------|-------------------|------------|-----------|
| **PDF Parser** | • PyPDF2<br>• pdfplumber<br>• Apache Tika | **pdfplumber** | Best for structured Italian legal PDFs |
| **OCR** | • Tesseract<br>• AWS Textract | **Tesseract (Italian trained)** | Open-source, good Italian support |
| **Task Queue** | • Celery + RabbitMQ<br>• Redis Queue | **Celery + RabbitMQ** | Mature, retry logic, monitoring |

---

## 8. Docker Compose Architecture

### 8.1 Service Definitions

```yaml
version: '3.8'

services:
  # Weaviate Vector Database
  weaviate:
    image: semitechnologies/weaviate:1.22.4
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
      - DEFAULT_VECTORIZER_MODULE=none
      - ENABLE_MODULES=text2vec-openai,generative-openai
      - CLUSTER_HOSTNAME=node1
    volumes:
      - weaviate_data:/var/lib/weaviate
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  # Neo4j Knowledge Graph
  neo4j:
    image: neo4j:5.13-enterprise
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_initial__size=4G
      - NEO4J_dbms_memory_heap_max__size=8G
      - NEO4J_dbms_memory_pagecache__size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    deploy:
      resources:
        limits:
          memory: 12G

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=merl_t
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=merl_t
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql
    deploy:
      resources:
        limits:
          memory: 2G

  # Data Ingestion Worker (Celery)
  ingestion-worker:
    build: ./services/ingestion-worker
    environment:
      - CELERY_BROKER_URL=amqp://rabbitmq:5672
      - WEAVIATE_URL=http://weaviate:8080
      - NEO4J_URI=bolt://neo4j:7687
      - POSTGRES_URI=postgresql://merl_t:${POSTGRES_PASSWORD}@postgres:5432/merl_t
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL=text-embedding-3-large
    depends_on:
      - rabbitmq
      - weaviate
      - neo4j
      - postgres
    deploy:
      replicas: 3

  # RabbitMQ (Message Broker)
  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  weaviate_data:
  neo4j_data:
  neo4j_logs:
  postgres_data:
  rabbitmq_data:
```

---

## 9. Error Handling & Resilience

### 9.1 Ingestion Failures

**Failure Types**:
- **Parse error**: Document format invalid → Skip document, log error
- **Chunking error**: Chunking fails → Fall back to fixed-size chunking (1024 tokens)
- **Embedding error**: API timeout → Retry 3 times, then skip chunk
- **Storage error**: VectorDB/Neo4j unavailable → Queue chunk for retry (exponential backoff)

**Retry Strategy**:
- **Transient errors**: Retry 3 times with exponential backoff (1s, 2s, 4s)
- **Permanent errors**: Log error, notify admin, skip item
- **Dead Letter Queue**: Failed items after 3 retries → DLQ for manual inspection

---

## 10. Performance Characteristics

### 10.1 Latency

| Operation | Latency (P95) | Optimization |
|-----------|--------------|--------------|
| **Vector search** (top-20) | 150ms | HNSW ef_search=64 |
| **Vector search + filters** | 200ms | Pre-filtering with metadata index |
| **Hybrid search** (P2) | 180ms | Parallel vector + BM25 |
| **Reranked search** (P4) | 2.2s | Cross-encoder on 50 candidates |
| **KG traversal** (depth-3) | 50ms | Indexed relationships |
| **Ingestion** (per chunk) | 1.15s | Pipeline latency |

---

### 10.2 Throughput

| Operation | Throughput | Conditions |
|-----------|-----------|-----------|
| **Ingestion** | 3,000 chunks/hour | 1 worker |
| **Ingestion** | 9,000 chunks/hour | 3 workers (parallel) |
| **Vector search** | 1,000 queries/sec | Single Weaviate instance |
| **KG queries** | 500 queries/sec | Single Neo4j instance |

---

## 11. Cross-References

### Section 02 Methodology
- **Vector Database**: `docs/02-methodology/vector-database.md`
  - §3: Metadata Schema
  - §4: Embedding Strategy (5-phase bootstrap)
  - §5: Retrieval Patterns P1-P6

- **Knowledge Graph**: `docs/02-methodology/knowledge-graph.md`
  - §2: KG Schema (23 node types, 65 relationships)
  - §3: Query Patterns

- **Data Ingestion**: `docs/02-methodology/data-ingestion.md`
  - §3: Chunking Strategies
  - §4: Metadata Enrichment

### Section 03 Architecture
- **Orchestration Layer**: `docs/03-architecture/02-orchestration-layer.md`
  - VectorDB Agent consumes VectorDB from Storage Layer

---

**Document Version**: 1.0
**Last Updated**: 2024-11-03
**Status**: ✅ Complete
