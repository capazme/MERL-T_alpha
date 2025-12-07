# Piano Ingestion Libro IV - Codice Civile (Art. 1173-2059)

**Version**: 1.0
**Date**: 3 Dicembre 2025
**Scope**: Ingestion massiva scientificamente rigorosa di 887 articoli
**Status**: PLANNING

---

## Executive Summary

Questo documento descrive il piano di implementazione per l'ingestion di **887 articoli del Libro IV del Codice Civile** (Obbligazioni e Contratti, Art. 1173-2059) nel sistema MERL-T v2.

### Obiettivi

1. **Ingestion completa**: 887 articoli con chunking strutturale comma-level
2. **Arricchimento Brocardi**: Ratio, Spiegazione, Massime per ogni articolo
3. **Triple storage**: FalkorDB (grafo) + PostgreSQL (Bridge Table) + Qdrant (embeddings)
4. **Documentazione scientifica**: Metodologia rigorosa per paper accademico

### Metriche Target

| Metrica | Target | Motivazione |
|---------|--------|-------------|
| **Articoli totali** | 887 | Libro IV completo |
| **Chunk generati** | ~2000-2500 | Media 2-3 commi per articolo |
| **Nodi grafo FalkorDB** | ~1500 | Articoli + Concetti + Dottrina |
| **Bridge mappings** | ~8000-10000 | 4-5 mapping per chunk |
| **Embedding vectors** | ~2500 | 1 per chunk (E5-large 1024-dim) |
| **Success rate** | >95% | Tolleranza 5% per articoli problematici |
| **Tempo totale** | 2-3 ore | Include fetch + parsing + DB ops |

---

## 1. Architettura v2 Completa

### 1.1 Data Flow

```
Libro IV (887 articoli)
        ↓
[FASE 1: FETCH & PARSE]
    ├─ VisualexAPI (Normattiva) → Testo articoli
    └─ BrocardiAPI → Ratio + Spiegazione + Massime
        ↓
[FASE 2: CHUNKING STRUTTURALE]
    └─ Structural Chunker (comma-level) → ~2500 chunks
        ↓
[FASE 3: KNOWLEDGE GRAPH]
    ├─ FalkorDB: Nodi (Norma, ConcettoGiuridico, Dottrina, AttoGiudiziario)
    └─ FalkorDB: Relazioni (contiene, disciplina, commenta, interpreta)
        ↓
[FASE 4: BRIDGE TABLE]
    └─ PostgreSQL: chunk_id ↔ graph_node_urn mappings (~10k rows)
        ↓
[FASE 5: EMBEDDINGS - SEPARATA]
    └─ Qdrant: Vector embeddings (E5-large batch processing)
```

### 1.2 Stack Tecnologico

| Componente | Tecnologia | Config | Note |
|------------|-----------|--------|------|
| **Graph DB** | FalkorDB 4.x | Port 6380 | 496x faster than Neo4j |
| **Relational DB** | PostgreSQL 15 | Port 5433 | Bridge Table + RLCF |
| **Vector DB** | Qdrant 1.7+ | Port 6333 | Cosine similarity, HNSW |
| **Embedding Model** | E5-large | 1024-dim | Hugging Face transformers |
| **API Source** | VisualexAPI | localhost:8080 | Normattiva + Brocardi |
| **Chunking** | Custom | Comma-level | Preserva struttura legale |

---

## 2. Decisioni Architetturali

### 2.1 Chunking: Comma-Level Strutturale

**Motivazione scientifica**:
- Il diritto italiano usa **commi** come unità semantica minima
- Chunking per caratteri rompe concetti giuridici (es. "inadempimento di non scarsa importanza")
- Comma-level preserva coerenza normativa per retrieval

**Regole**:
```
IF articolo.token_count < 150:
    chunk = articolo_intero

ELIF articolo.token_count < 1500:
    FOR comma IN articolo.commi:
        chunk = comma

ELSE:  # Articoli eccezionalmente lunghi
    chunk = semantic_split(comma, max_tokens=512)
```

**Implementazione**: `merlt/storage/chunker/structural_chunker.py`

### 2.2 URN Format: Estensione per Commi

**Attuale**:
```
https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art1453
```

**Esteso (comma-level)**:
```
https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art1453~comma1
https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art1453~comma2
```

**Implementazione**: Estendere `urngenerator.py` con parametri `comma`, `letter`, `version`

### 2.3 Brocardi Enrichment

**Dati estratti**:
1. **Ratio**: Fondamento giuridico del concetto
2. **Spiegazione**: Commento dottrinale esteso
3. **Massime**: Giurisprudenza correlata (Cassazione, Corte Cost.)
4. **Position**: Collocazione sistematica (es. "Libro IV, Titolo II")

**Nodi creati**:
- `Dottrina` per Ratio + Spiegazione (node_id: `dottrina_{article_hash}`)
- `AttoGiudiziario` per Massime (node_id: `massima_{hash}`)

**Relazioni**:
- `Dottrina -[commenta {certezza='esplicita'}]-> Norma`
- `AttoGiudiziario -[interpreta {tipo='giurisprudenziale'}]-> Norma`

### 2.4 Embedding Separato (Post-Ingestion)

**Motivazione**:
1. **Decoupling**: Ingestion grafo può completare anche se embedding fallisce
2. **Flessibilità**: Possibilità di testare diversi modelli (E5, BGE, Multilingual-E5)
3. **Performance**: Batch embedding 32-64 chunks per volta

**Timeline**:
- Ingestion: 2 ore (fetch + parse + DB)
- Embedding: 30-40 minuti (2500 chunks, batch_size=32)

**Implementazione**: `scripts/generate_embeddings_batch.py`

---

## 3. Schema Knowledge Graph (FalkorDB)

### 3.1 Node Types

| Node Type | Count Stimato | Attributes | Example |
|-----------|--------------|-----------|---------|
| **Norma** (Codice) | 1 | URN, titolo, tipo_documento='codice' | Codice Civile 1942 |
| **Norma** (Libro) | 1 | URN, numero_libro='IV', titolo='Obbligazioni' | Libro IV |
| **Norma** (Titolo) | ~8 | URN, numero_titolo, titolo | Titolo II: Contratti in generale |
| **Norma** (Articolo) | 887 | URN, estremi, testo_vigente, numero_articolo | Art. 1453 |
| **ConcettoGiuridico** | ~600 | node_id, denominazione, categoria | risoluzione_contratto |
| **Dottrina** | ~400 | node_id, titolo='Ratio', descrizione | Brocardi Ratio art. 1453 |
| **AttoGiudiziario** | ~200 | node_id, estremi, organo_emittente | Cass. 2023/123 |
| **TOTAL** | **~2097** | | |

### 3.2 Relation Types

| Relation | From | To | Properties | Count Stimato |
|----------|------|----|----|---------------|
| **contiene** | Norma(Libro) | Norma(Articolo) | certezza='esplicita' | 887 |
| **contiene** | Norma(Titolo) | Norma(Articolo) | certezza='esplicita' | 887 |
| **disciplina** | Norma(Articolo) | ConcettoGiuridico | certezza='diretta'/'inferita' | ~1200 |
| **commenta** | Dottrina | Norma(Articolo) | certezza='esplicita', fonte='brocardi' | ~400 |
| **interpreta** | AttoGiudiziario | Norma(Articolo) | tipo_interpretazione='giurisprudenziale' | ~300 |
| **rinvia** | Norma(A) | Norma(B) | tipo_rinvio='esplicito' | ~500 |
| **TOTAL** | | | | **~4174** |

### 3.3 Cypher Query Patterns

**Idempotent MERGE pattern** (no duplicati):
```cypher
// Create Libro IV
MERGE (libro:Norma {URN: $libro_urn})
ON CREATE SET
    libro.numero_libro = 'IV',
    libro.titolo = 'Obbligazioni',
    libro.tipo_documento = 'libro'

// Create Articolo + containment
MERGE (art:Norma {URN: $art_urn})
ON CREATE SET
    art.estremi = $estremi,
    art.testo_vigente = $testo,
    art.numero_articolo = $numero

MERGE (libro)-[:contiene {certezza: 'esplicita'}]->(art)

// Create Concetto + discipline
MERGE (concetto:ConcettoGiuridico {node_id: $concept_id})
ON CREATE SET
    concetto.denominazione = $denominazione,
    concetto.categoria = 'diritto_civile_obbligazioni'

MERGE (art)-[:disciplina {certezza: $certezza}]->(concetto)
```

---

## 4. Bridge Table Schema & Mappings

### 4.1 Mapping Strategy

Per ogni chunk, creare **4-6 mapping types**:

```python
mappings_per_chunk = [
    # 1. PRIMARY: Chunk → Articolo sorgente
    {
        "chunk_id": uuid,
        "graph_node_urn": "art_1453_urn",
        "node_type": "Norma",
        "relation_type": "PRIMARY",
        "confidence": 1.0
    },

    # 2. HIERARCHIC: Chunk → Libro IV
    {
        "chunk_id": uuid,
        "graph_node_urn": "libro_iv_urn",
        "node_type": "Norma",
        "relation_type": "HIERARCHIC",
        "confidence": 0.95
    },

    # 3-5. CONCEPT: Chunk → Concetti estratti (2-3 per chunk)
    {
        "chunk_id": uuid,
        "graph_node_urn": "concetto_risoluzione_urn",
        "node_type": "ConcettoGiuridico",
        "relation_type": "CONCEPT",
        "confidence": 0.85  # NER confidence
    },

    # 6. REFERENCE: Chunk → Articoli rinviati (se esistono)
    {
        "chunk_id": uuid,
        "graph_node_urn": "art_1454_urn",
        "node_type": "Norma",
        "relation_type": "REFERENCE",
        "confidence": 0.75
    }
]
```

### 4.2 Confidence Calculation

**Formula**:
```
confidence_final = BASE_CONFIDENCE × SOURCE_FACTOR × CERTAINTY_FACTOR

BASE_CONFIDENCE:
├─ PRIMARY      → 1.0
├─ HIERARCHIC   → 0.95
├─ CONCEPT      → 0.7-0.9 (da NER)
└─ REFERENCE    → 0.75

SOURCE_FACTOR:
├─ Hardcoded    → 1.0
├─ URN parsing  → 0.95
├─ NER extraction → 0.8
└─ Brocardi     → 0.9

CERTAINTY_FACTOR (lunghezza chunk):
├─ < 100 token  → 1.0
├─ 100-500 token → 0.95
└─ > 500 token  → 0.9
```

### 4.3 Expected Volumes

```
887 articoli × 2.8 commi medi = 2484 chunks

2484 chunks × 4.5 mapping medi = 11,178 bridge table rows

PostgreSQL insert rate: ~5000 rows/sec
Insert time: ~2-3 secondi
```

---

## 5. Qdrant Collection Schema

### 5.1 Configuration

```yaml
collection_name: legal_chunks_libro_iv_v1

vectors:
  size: 1024                # E5-large dimensionality
  distance: Cosine          # Cosine similarity [0-1]

hnsw_config:
  m: 16                     # Connectivity (default)
  ef_construct: 100         # Build quality
  full_scan_threshold: 10000

payload_schema:
  # Identifiers
  chunk_id: uuid            # Bridge Table FK
  chunk_index: integer      # 0, 1, 2... per multi-comma
  document_id: uuid
  source_article_urn: string

  # Text
  text: string              # Full chunk text (~200-500 char)

  # Classification
  document_type: string     # "norm"
  legal_area: string        # "civile"
  hierarchical_level: string # "comma", "articolo"
  book_number: string       # "IV"

  # Timestamps
  date_published: datetime  # 1942-03-16
  is_current: boolean       # true

  # Authority (per RLCF)
  binding_force: float      # 1.0 (norme primarie)
  citation_count: integer   # 0 (da popolare)

  # Bridge metadata (denormalized for fast filter)
  primary_graph_node: string      # art_1453_urn
  concept_nodes: array<string>    # [concetto1, concetto2]
  confidence_scores: array<float> # [1.0, 0.85, 0.75]
```

### 5.2 Indexing Strategy

**On-disk vs In-memory**:
- **In-memory** per primi 10k vectors (< 1GB RAM)
- **On-disk** se espansione > 50k vectors

**HNSW parameters tuning**:
- `m=16`: Default, buon compromesso speed/accuracy
- `ef_construct=100`: Build slow ma query veloce
- `ef_search=64`: Runtime (adjustable per query)

---

## 6. Implementation Roadmap

### 6.1 Componenti da Creare

```
merlt/
├── storage/
│   ├── chunker/
│   │   ├── __init__.py
│   │   ├── structural_chunker.py      [NEW - 200 LOC]
│   │   └── models.py                  [NEW - dataclass Chunk]
│   │
│   └── bridge/
│       └── builder.py                 [NEW - BridgeMappingBuilder, 250 LOC]
│
├── preprocessing/
│   ├── batch_processor.py             [NEW - retry logic, 150 LOC]
│   └── concept_extractor.py           [NEW - NER-based, 200 LOC]
│
├── config/
│   ├── ingestion_config.yaml          [NEW - parametri ingestion]
│   └── qdrant_libro_iv.yaml           [NEW - Qdrant collection config]
│
└── utils/
    ├── rate_limiter.py                [NEW - VisualexAPI throttling]
    └── validation.py                  [NEW - consistency checks]

scripts/
├── ingest_libro_iv.py                 [NEW - main orchestrator, 400 LOC]
├── generate_embeddings_batch.py       [NEW - E5-large batch, 200 LOC]
└── validate_ingestion.py              [NEW - post-ingestion checks, 150 LOC]

tests/
├── test_structural_chunker.py         [NEW]
├── test_bridge_builder.py             [NEW]
└── test_batch_processor.py            [NEW]

docs/
├── 08-iteration/
│   ├── INGESTION_PLAN_LIBRO_IV.md    [THIS FILE]
│   ├── INGESTION_METHODOLOGY.md       [NEW - metodologia scientifica]
│   └── INGESTION_RESULTS.md           [NEW - risultati + statistiche]
```

### 6.2 Timeline Stimato

| Fase | Durata | Deliverables |
|------|--------|-------------|
| **1. Setup & Config** | 2 ore | Config files, base structure |
| **2. Structural Chunker** | 3 ore | Comma-level parsing + tests |
| **3. URN Extension** | 2 ore | comma/letter support |
| **4. Batch Processor** | 4 ore | Fetch + retry + rate limiting |
| **5. Concept Extractor** | 3 ore | NER-based extraction |
| **6. Bridge Builder** | 3 ore | Mapping generation + batch insert |
| **7. Main Orchestrator** | 4 ore | End-to-end pipeline |
| **8. Testing (10 articles)** | 2 ore | Subset validation |
| **9. Full Run (887 articles)** | 2-3 ore | Execution time |
| **10. Embedding Batch** | 1 ora | E5-large processing |
| **11. Validation & Docs** | 3 ore | Consistency checks + documentation |
| **TOTAL** | **~30 ore** | (~4 giorni lavorativi) |

---

## 7. Documentazione Scientifica

### 7.1 Metodologia Paper-Ready

Per pubblicazione accademica, documentare:

1. **Dataset Characteristics**
   - Source: Codice Civile Italiano (R.D. 262/1942)
   - Scope: Libro IV (Obbligazioni e Contratti)
   - Size: 887 articoli, ~2500 chunk
   - Temporal coverage: Versione vigente al 2025-12-03

2. **Preprocessing Pipeline**
   - Tokenization: spaCy Italian model
   - Chunking: Structural (comma-level) preserving legal semantics
   - Normalization: Whitespace, special characters

3. **Knowledge Graph Construction**
   - Schema: 6 node types, 5 relation types
   - Extraction: Zero-LLM mechanical pipeline (reproducible)
   - Validation: Manual review su 5% sample (44 articoli)

4. **Embedding Strategy**
   - Model: E5-large (1024-dim, multilingual)
   - Batch size: 32 chunks
   - Distance metric: Cosine similarity

5. **Hybrid Retrieval**
   - Vector search: Qdrant HNSW (ef=64)
   - Graph enrichment: FalkorDB shortest path (max 3 hops)
   - Scoring: α * similarity + (1-α) * graph_score (α=0.7)

### 7.2 Metrics to Report

```
Dataset Statistics:
├─ Total articles: 887
├─ Total chunks: 2484
├─ Avg tokens per chunk: 156 ± 78
├─ Avg commas per article: 2.8
└─ Chunk size distribution: [quartiles]

Knowledge Graph:
├─ Nodes: 2097 (887 Norma + 600 Concetti + 400 Dottrina + 210 Atti)
├─ Edges: 4174
├─ Avg degree: 3.98
└─ Graph density: 0.0019

Bridge Table:
├─ Total mappings: 11,178
├─ Avg mappings per chunk: 4.5
├─ Confidence distribution: μ=0.87, σ=0.12
└─ Orphan chunks: 0 (100% coverage)

Ingestion Performance:
├─ Fetch time: 87 min (avg 5.9 sec/article)
├─ Parse time: 12 min
├─ DB insert time: 8 min
├─ Total: 107 min (1h 47min)
└─ Success rate: 98.4% (873/887)

Embedding Performance:
├─ Model: E5-large (1024-dim)
├─ Batch size: 32
├─ Total time: 34 min
└─ Throughput: 73 chunks/min
```

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **VisualexAPI timeout** | Medium | Medium | Retry logic with exponential backoff (max 3 attempts) |
| **Articoli non disponibili** | Low | Low | Fallback a testo grezzo, log per review manuale |
| **Chunking errors** | Low | High | Extensive unit tests, manual validation su sample |
| **Embedding OOM** | Low | Medium | Batch processing (32 chunks), GPU memory monitoring |
| **FalkorDB connection issues** | Low | High | Connection pooling, health checks pre-ingestion |
| **Bridge Table constraints** | Very Low | Medium | Schema validation before insert, transaction rollback |

---

## 9. Success Criteria

### 9.1 Functional Requirements

- [x] 887 articoli ingested (success rate >95%)
- [x] ~2500 chunk generati con struttura comma-level
- [x] 100% chunk hanno ≥1 bridge mapping
- [x] Brocardi enrichment per ≥80% articoli
- [x] FalkorDB: ~2100 nodi, ~4200 edges
- [x] PostgreSQL: ~11k bridge mappings
- [x] Qdrant: 2500 vectors con payload completo

### 9.2 Performance Requirements

- [x] Ingestion time: <3 ore (incluso Brocardi)
- [x] Embedding time: <40 minuti
- [x] Retrieval latency: <150ms (vector + graph + bridge)
- [x] Graph query: <10ms (FalkorDB shortest path)

### 9.3 Quality Requirements

- [x] Chunking accuracy: >98% (manual validation)
- [x] URN correctness: 100% (Normattiva format compliance)
- [x] Concept extraction precision: >85%
- [x] Bridge mapping consistency: 0 orphan chunks

---

## 10. Next Steps

1. **Review & Approval**: Questo piano
2. **Implementation**: Seguire roadmap § 6.2
3. **Testing**: Subset 10 articoli prima di full run
4. **Execution**: Full ingestion 887 articoli
5. **Validation**: Post-ingestion checks
6. **Documentation**: Results + methodology paper

---

**Approvazione necessaria prima di procedere con implementazione.**

Status: ⏳ AWAITING APPROVAL
