# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 8 Dicembre 2025 (notte) |
| **Fase progetto** | **Multi-Source Embeddings** - RAG potenziato |
| **Prossimo obiettivo** | Full ingestion Libro IV CC (887 articoli) |
| **Blocchi attivi** | Nessuno |

---

## Cosa Abbiamo Fatto (Sessione Corrente - 8 Dic 2025, Notte)

### Multi-Source Embeddings - COMPLETATO ✅

- [x] **Implementazione** in `merlt/core/legal_knowledge_graph.py`:
  - Nuovo metodo `_upsert_embeddings_multi_source()`
  - Crea embedding per: norma, spiegazione, ratio, massime (top 5)
  - Payload con `source_type` per filtraggio

- [x] **Fix massime**: Campo corretto è `massima` (non `testo`)

- [x] **Test con Art. 52 CP** (legittima difesa):
  - 8 embeddings creati (1 norma + 1 spiegazione + 1 ratio + 5 massime)
  - Funzionalità verificata end-to-end

### Ingestion Libro IV CC - PRONTO ✅

- [x] **Script aggiornato** `scripts/ingest_libro_iv_cc.py`:
  - Naming convention EXPERIMENT_STRATEGY.md
  - Graph: `merl_t_exp_libro_iv_cc`, Collection: `exp_libro_iv_cc`
  - Supporto `--skip-brocardi`, `--skip-embeddings`, `--start-from`

- [x] **Test sample** (5 articoli con Brocardi):
  - 5/5 articoli (100% success)
  - 40 embeddings multi-source
  - 354 nodi, 356 relazioni

### RAG Validation - COMPLETATO ✅

- [x] **Script** `scripts/validate_rag.py`:
  - 12 query test per Costituzione
  - Metriche: Recall@K, MRR, by category

- [x] **Baseline Costituzione** (single-source embeddings):
  | Metrica | Valore |
  |---------|--------|
  | Recall@1 | 75% |
  | Recall@5 | **100%** |
  | Recall@10 | **100%** |
  | MRR | **0.850** |

- [x] **By Category**:
  - `principle`: MRR 1.000 (perfetto)
  - `institution`: MRR 1.000 (perfetto)
  - `conceptual`: MRR 0.700

### Documentazione Aggiornata

- [x] `docs/architecture/EMBEDDING_STRATEGY.md` - Strategia multi-source
- [x] `docs/architecture/EXPERIMENT_STRATEGY.md` - Stima embeddings
- [x] `docs/experiments/rag_validation_costituzione.json` - Risultati baseline

---

## REFACTORING COMPLETATO: backend/ → merlt/

### Struttura Nuova
```
merlt/                           # Package principale
├── __init__.py                  # from merlt import LegalKnowledgeGraph
├── config/                      # TEST_ENV, PROD_ENV
├── core/                        # LegalKnowledgeGraph, MerltConfig
├── models/                      # BridgeMapping, altri dataclass condivisi
├── sources/                     # NormattivaScraper, BrocardiScraper
│   └── utils/                   # norma, urn, tree, text, http
├── storage/                     # graph/, vectors/, bridge/, retriever/
├── pipeline/                    # ingestion, parsing, chunking, multivigenza
├── rlcf/                        # authority, aggregation
└── utils/                       # Shared utilities
```

### Imports Aggiornati
```python
# Tutti gli imports usano ora il package merlt
from merlt import LegalKnowledgeGraph
from merlt.sources import NormattivaScraper, BrocardiScraper
from merlt.storage.graph import FalkorDBClient
from merlt.pipeline import IngestionPipelineV2
from merlt.rlcf import OpenRouterService
```

### File CI/CD Aggiornati
- `.github/workflows/ci.yml` - Aggiornato per `merlt/`
- `pyproject.toml` - Creato per package installabile

### Legacy Code Archiviato
- `_archive/` - Tutto il codice vecchio spostato qui

---

## Cosa Abbiamo Fatto (Sessione Corrente - 8 Dic 2025, Sera)

### Code Maintenance & Cleanup - COMPLETATO ✅

- [x] **Analisi architettura** ✅:
  - Mappate ~120+ dipendenze interne tra 45+ file Python
  - Identificati 5 problemi critici/alti

- [x] **Fix CRITICO: BaseScraper duplicato** ✅:
  - Rimosso `BaseScraper` da `merlt/sources/utils/sys_op.py` (dead code)
  - L'unico `BaseScraper` ora è in `merlt/sources/base.py`

- [x] **Fix CRITICO: FalkorDBConfig duplicato** ✅:
  - Consolidato in `merlt/storage/graph/config.py`
  - Supporto variabili d'ambiente (`FALKORDB_HOST`, `FALKORDB_PORT`, etc.)
  - Rimossa versione duplicata da `client.py`

- [x] **Fix CRITICO: RetrieverConfig duplicato** ✅:
  - Eliminato `merlt/storage/retriever/result_models.py` (100% duplicato)
  - L'unico `RetrieverConfig` ora è in `merlt/storage/retriever/models.py`

- [x] **Fix ALTO: Standardizzazione logging** ✅:
  - Convertiti 12+ file da `import logging` a `import structlog`
  - Pattern uniforme: `log = structlog.get_logger()`
  - File modificati: legal_knowledge_graph.py, multivigenza.py, retriever.py,
    ai_service.py, hybrid.py, visualex.py, bridge_builder.py, embeddings.py,
    parsing.py, chunking.py, bridge_table.py, ingestion.py, eurlex.py

- [x] **Fix MEDIO: Inversione dipendenze** ✅:
  - Creato `merlt/models/` directory per dataclass condivisi
  - Spostato `BridgeMapping` da `pipeline/ingestion.py` a `models/mappings.py`
  - Storage non dipende più da Pipeline (corretto)

### EXP-011: Ingestion Costituzione (Replica) - COMPLETATO ✅

- [x] **Ingestion 139 articoli Costituzione** ✅:
  - 139/139 nodi Norma in FalkorDB
  - 134/134 chunks in Qdrant (collection `constitution_exp011`)
  - Fix manuale: 5 embeddings mancanti (articoli 1-5) aggiunti

- [x] **Verifica allineamento grafo-schema** ✅:
  - Properties `numero_*` correttamente usate
  - Struttura gerarchica (Parte I, Parte II) implementata

---

## Cosa Abbiamo Fatto (Sessione Precedente - 8 Dic 2025, Mattina)

### EXP-007: Full Ingestion con Brocardi + Bridge + Multivigenza - COMPLETATO ✅

- [x] **Ingestion 17 articoli (Art. 1453-1469)** ✅:
  - 17/17 processati (100%)
  - 17/17 con Brocardi dottrina (100%)
  - 467 massime giurisprudenziali
  - 16/17 con jurisprudence (94%)
  - 5 relazioni multivigenza

- [x] **Assessment Documentazione** ✅:
  - Analisi completa docs/claude-context/
  - Analisi completa docs/experiments/
  - Analisi completa docs/architecture/
  - Mappatura Research Questions RQ1-RQ6
  - Piano riallineamento creato

- [x] **Fix RLCF Module** ✅:
  - Ripristinati config.py, model_config.yaml, task_config.yaml
  - Creato database.py con SQLAlchemy Base
  - Fix lazy imports in __init__.py
  - OpenRouterService ora importabile

### Research Questions Status ✅

| RQ | Status | Esperimenti |
|----|--------|-------------|
| RQ1 (Chunking) | ✅ VERIFIED | EXP-001, EXP-006, EXP-011 |
| RQ2 (Gerarchia) | ✅ VERIFIED | EXP-001, EXP-011 |
| RQ3 (Brocardi) | ✅ VERIFIED | EXP-001, EXP-006, EXP-007 |
| RQ4 (Bridge Table) | ⚠️ DATA READY | EXP-002, EXP-003 |
| RQ5 (Expert Tools) | ❌ NOT STARTED | - |
| RQ6 (RLCF) | ❌ NOT STARTED | - |

---

## Cosa Abbiamo Fatto (Sessione Precedente - 7 Dic 2025)

### Test di Integrazione Completi - COMPLETATO ✅

- [x] **15/15 test passano** senza mock:
  - `TestImports` (5/5): Core, sources, storage, pipeline, config
  - `TestFalkorDBIntegration` (2/2): Connect, CRUD nodes
  - `TestBridgeTableIntegration` (2/2): Health, CRUD mappings
  - `TestScraperIntegration` (2/2): Normattiva, Brocardi (siti reali)
  - `TestPipelineIntegration` (2/2): CommaParser, StructuralChunker
  - `TestEmbeddingIntegration` (2/2): Singleton, generation

- [x] **CI/CD Aggiornato**:
  - Job `integration` con Docker services (FalkorDB, PostgreSQL, Qdrant)
  - Health checks per tutti i container
  - Test senza mock in CI

### Refactoring backend/ → merlt/ - COMPLETATO ✅

- [x] **Step 1**: Rinominato `backend/` → `merlt/`
- [x] **Step 2-3**: Creata nuova struttura directories e spostati file
- [x] **Step 4-5**: Aggiornati tutti gli imports e creati `__init__.py`
- [x] **Step 6**: Archiviato codice legacy in `_archive/`
- [x] **Step 7-9**: Aggiornati scripts, tests, docs
- [x] **Verifica**: Tutti gli imports funzionano ✅

### CI/CD Setup
- [x] `pyproject.toml` creato con dependencies e tool config
- [x] `.github/workflows/ci.yml` aggiornato per `merlt/`
- [x] `tests/conftest.py` creato con fixtures base

### Core Library Implementata - COMPLETATO ✅

- [x] **`merlt/core/legal_knowledge_graph.py`** ✅:
  - Classe `LegalKnowledgeGraph` che coordina tutti i componenti
  - Classe `MerltConfig` per configurazione unificata
  - Metodo `ingest_norm()` con integrazione completa
  - Metodo `search()` per ricerca ibrida

### EXP-006: Ingestion Libro Primo CP - COMPLETATO ✅

- [x] **Ingestion 263 articoli** ✅:
  - 263/263 processati (100%)
  - 262/263 con Brocardi (99.6%)
  - 6,195 massime totali

- [x] **RAG Test** ✅:
  - 12 query di test
  - Precision@5: 0.200
  - Recall: 0.528
  - MRR: 0.562
  - Verdict: ACCEPTABLE

---

## Cosa Abbiamo Fatto (Sessione Precedente - 6 Dic 2025)

### EXP-005: Fix Multivigenza e Validazione - COMPLETATO ✅

- [x] **Bug Fix 1: Filtering articolo** ✅:
  - Problema: `startswith()` matchava Art. 14 cercando Art. 1
  - Fix: Confronto numeri base esatti (`nv_base != target_base`)

- [x] **Bug Fix 2: is_abrogato troppo permissivo** ✅:
  - Problema: Articolo marcato "abrogato" anche se solo un comma era abrogato
  - Fix: Nuovo metodo `is_article_level_abrogation(for_article=X)`

- [x] **Bug Fix 3: Parsing destinazione** ✅:
  - Problema: Regex non catturava "del comma 2 dell'art. 2-bis"
  - Fix: Pattern esteso per entrambi i formati (articolo-prima e comma-prima)

- [x] **Validazione Ground Truth Normattiva** ✅:
  | Articolo | Sistema | Normattiva | Status |
  |----------|---------|------------|--------|
  | Art. 1 | Vigente | Vigente | ✅ |
  | Art. 2 | Vigente | Vigente | ✅ |
  | Art. 2-bis | Vigente | Vigente (comma 2 abrogato) | ✅ |
  | Art. 3 | Vigente | Vigente | ✅ |
  | Art. 3-bis | Vigente | Vigente | ✅ |

### File Modificati:
- `merlt/external_sources/visualex/tools/norma.py`: Campo `destinazione`, metodo `is_article_level_abrogation()`
- `merlt/external_sources/visualex/scrapers/normattiva_scraper.py`: Parsing migliorato
- `merlt/preprocessing/multivigenza_pipeline.py`: Logica is_abrogato corretta

---

## Cosa Abbiamo Fatto (Sessione Precedente - 5 Dic 2025, Pomeriggio)

### EXP-004: Ingestion Costituzione Italiana - COMPLETATO ✅

- [x] **Design document** ✅:
  - Creato `docs/experiments/EXP-004_ingestion_costituzione/DESIGN.md`
  - 139 articoli target (Principi Fondamentali + Parte I + Parte II)

- [x] **Script ingestion** ✅:
  - Riutilizzato `BrocardiScraper` esistente (no duplicazione codice)
  - Fix: collection Qdrant `merl_t_chunks` (non `legal_chunks`)
  - Fix: porta FalkorDB 6380 (non 6379)
  - Fix: `Norma(tipo_atto=...)` (non `tipo_atto_str`)

- [x] **Risultati FalkorDB** ✅:
  | Metrica | Valore |
  |---------|--------|
  | Nodi Norma (articoli) | 139 |
  | Nodi Dottrina (spiegazioni) | 133 |
  | Nodi AttoGiudiziario (massime) | 14 |

- [x] **Risultati Qdrant** ✅:
  | Metrica | Valore |
  |---------|--------|
  | Embeddings articoli | 138 |
  | Embeddings massime | 14 |
  | Totale collection | **10,814** |

- [x] **Storage totale aggiornato** ✅:
  | Fonte | Articoli | Massime | Embeddings |
  |-------|----------|---------|------------|
  | Libro IV CC | 887 | 9,775 | 10,662 |
  | Costituzione | 139 | 14 | 152 |
  | **Totale** | **1,026** | **9,789** | **10,814** |

---

## Cosa Abbiamo Fatto (Sessione Precedente - 5 Dic 2025, Mattina)

### Pulizia Duplicati e Re-Embedding Article-Level - COMPLETATO ✅

- [x] **Problema identificato** ✅:
  - Art. 1284 aveva **46 chunks identici** (bug ingestion, non chunking)
  - Bridge Table: 2,546 righe, solo **881 URN unici** (65% duplicati!)
  - Ogni articolo aveva ~3 copie dello stesso embedding troncato

- [x] **Step 1: Pulizia Bridge Table** ✅:
  - Query con ROW_NUMBER() OVER (PARTITION BY graph_node_urn, chunk_text)
  - Righe prima: 2,546 → dopo: **881** (-1,665 duplicati)

- [x] **Step 2: Pulizia Qdrant Norma** ✅:
  - Scroll + group by URN + keep first
  - Punti prima: 2,546 → dopo: **881** (-1,665 duplicati)

- [x] **Step 3: Re-Embedding Article-Level** ✅:
  - Strategia: 1 embedding per articolo (testo completo) invece di comma-level
  - Script: `scripts/reembed_articles.py`
  - Articoli letti da FalkorDB: **887** (source of truth)
  - Nuovi embeddings generati: **887** (vs 881 precedenti, +6 mancanti)
  - Art. 1284: da 500 chars (preview) a **7,523 chars** (testo completo)

- [x] **Step 4: Verifica** ✅:
  - Test ricerca "tasso interesse legale": Art. 1284 = #1 (score 0.8517)
  - Test duplicati: **NESSUN DUPLICATO** nei top-10 risultati ✅
  - Massime invariate: 9,775

- [x] **Stato finale storage** ✅:
  | Storage | Prima | Dopo |
  |---------|-------|------|
  | **Qdrant Norma** | 2,546 | **887** |
  | **Qdrant Massime** | 9,775 | 9,775 |
  | **Qdrant Totale** | 12,321 | **10,662** |
  | **Bridge Table** | 2,546 | **887** |
  | **Art. 1284 text** | 500 chars | **7,523 chars** |

---

## Cosa Abbiamo Fatto (Sessione Precedente - 5 Dic 2025, Notte)

### Massime Embedding Completo - COMPLETATO ✅

- [x] **Pulizia duplicati Qdrant** ✅:
  - Due script embed_massime.py eseguiti in parallelo avevano creato duplicati
  - Duplicati trovati: **4,832** (ogni massima aveva 2 copie)
  - Duplicati rimossi: **4,832**
  - Massime uniche residue: **6,592**

- [x] **Embedding massime mancanti** ✅:
  - Grafo corretto identificato: `merl_t_legal` (non `legal_graph`)
  - Massime in FalkorDB: **9,775**
  - Massime già embeddate: **6,592**
  - Massime mancanti: **3,183**
  - Script: `scripts/embed_massime.py --batch-size 64`
  - Tempo: ~6 minuti

---

## Cosa Abbiamo Fatto (Sessione Precedente - 4 Dic 2025, Pomeriggio/Sera)

### Aggiornamento Grafo con Gerarchia Completa - COMPLETATO ✅

- [x] **Script `scripts/update_graph_hierarchy.py`** ✅:
  - Carica NormTree da Normattiva
  - Crea nodi Titolo, Capo, Sezione mancanti
  - Crea relazioni :contiene dalla gerarchia agli articoli

- [x] **Risultati aggiornamento grafo** ✅:
  | Tipo | Creati |
  |------|--------|
  | Titoli | 9 |
  | Capi | 51 |
  | Sezioni | 56 |
  | Relazioni :contiene | 887 |

- [x] **Stato finale grafo** ✅:
  | Nodi | Quantità |
  |------|----------|
  | Norma totali | **1005** |
  | - articolo | 887 |
  | - sezione | 56 |
  | - capo | 51 |
  | - titolo | 9 |
  | - libro | 1 |
  | - codice | 1 |
  | Dottrina | 1630 |
  | AttoGiudiziario | 827 |
  | **Relazioni** | |
  | - :contiene | 1891 |
  | - :interpreta | 23056 |
  | - :commenta | 1630 |

### Hierarchical Tree Extraction - COMPLETATO ✅

- [x] **treextractor.py esteso** ✅:
  - Dataclasses: `NormLevel`, `NormNode`, `NormTree` per struttura gerarchica
  - `get_hierarchical_tree()`: estrae Libro→Titolo→Capo→Sezione→Articolo
  - `get_article_position()`: restituisce position string stile Brocardi
  - `get_all_articles_with_positions()`: per batch processing
  - Test con Codice Civile: 3,263 articoli, 6 Libri
  - Art. 1453 position: "Libro IV - DELLE OBBLIGAZIONI, Titolo II - DEI CONTRATTI IN GENERALE, Capo XIV - Della risoluzione del contratto, Sezione I - Della risoluzione per inadempimento"

- [x] **ingestion_pipeline_v2.py esteso** ✅:
  - `HierarchyURNs` dataclass con `closest_parent()` method
  - Estrazione Capo e Sezione (prima solo Libro/Titolo)
  - Refactoring: 4 `_extract_*_titolo` duplicate → singola `_extract_hierarchy_title(position, level)`
  - 24/24 test passano

- [x] **Sincronizzazione backend** ✅:
  - Copia su `merlt/external_sources/visualex/tools/treextractor.py`

- [x] **Integrazione treextractor in pipeline** ✅:
  - `ingest_article()` accetta `norm_tree` opzionale
  - Fallback automatico: Brocardi → treextractor per position
  - Re-export `NormTree`, `get_article_position` per comodità
  - 25/25 test passano (nuovo test per fallback)

### Note:
- L'estrazione gerarchica da Normattiva serve come fallback quando Brocardi non è disponibile
- Gli articoli senza gerarchia (es. Art. 1-2 CC, Disposizioni sulla legge) restano senza position

### Embedding Generation - COMPLETATO ✅

- [x] **Script `scripts/generate_embeddings.py`** ✅:
  - Connette a PostgreSQL, FalkorDB, Qdrant
  - Carica modello `intfloat/multilingual-e5-large` su MPS (Apple Silicon)
  - Genera embeddings per tutti i chunks della Bridge Table
  - Salva in Qdrant con payload (URN, node_type, text_preview)

- [x] **Risultati embedding generation** ✅:
  | Metrica | Valore |
  |---------|--------|
  | Chunks processati | **2,546** |
  | Embeddings generati | **2,546** |
  | Errori | **0** |
  | Tempo totale | ~8 minuti |
  | Modello | `intfloat/multilingual-e5-large` |
  | Dimensione | 1024 |
  | Device | MPS (Apple Silicon) |

- [x] **Stato Storage Completo** ✅:
  | Storage | Contenuto |
  |---------|-----------|
  | FalkorDB | 3,462 nodi, 26,577 relazioni |
  | PostgreSQL | 2,546 bridge mappings |
  | Qdrant | 2,546 vectors (1024 dim) |

---

## Cosa Abbiamo Fatto (Sessione Precedente - 4 Dic 2025, Notte Tarda)

### EXP-001 Re-run con Brocardi Enrichment Integrato - COMPLETATO ✅

- [x] **Fix persistenza dati Docker** ✅:
  - Data loss dopo chiusura Docker Desktop (tutti i dati persi)
  - Cambiato da Docker volumes a local bind mounts (`./data/`)
  - FalkorDB: fix mount path `/var/lib/falkordb/data`
  - Persistence: `--save 10 1 --appendonly yes`

- [x] **Bug fix pipeline** ✅:
  - `'str' object has no attribute 'get'` → isinstance checks in ingestion_pipeline_v2.py
  - Massime come stringhe → conversione automatica str → dict
  - Bridge Table non esistente → schema.sql applicato

- [x] **Re-run EXP-001 con Brocardi** ✅ (02:17 - 02:24):
  - Articoli: **887/887** (100% success)
  - Errori: **0**
  - **Nodi totali: 3,346** (+274% vs run precedente)
    - Norma: 889 (codice + libro + articoli)
    - Dottrina: 1,630 (Ratio, Spiegazione, Brocardi)
    - AttoGiudiziario: 827 (Massime)
  - **Relazioni totali: 25,574** (+2768% vs run precedente)
    - :interpreta: 23,056
    - :commenta: 1,630
    - :contiene: 888
  - Bridge mappings: 2,546

### Note Importanti:
- EXP-002 (Brocardi Enrichment) ora integrato in EXP-001
- Knowledge Graph completo con dottrina e giurisprudenza
- Sistema pronto per embedding generation e RAG queries

---

## Cosa Abbiamo Fatto (Sessione Precedente - 3 Dic 2025, Notte)

- [x] **CommaParser** ✅:
  - File: `merlt/preprocessing/comma_parser.py` (350+ lines)
  - Parsa article_text → ArticleStructure(numero_articolo, rubrica, List<Comma>)
  - Regex per bis/ter/quater, rubrica, comma parsing
  - Token counting con tiktoken (cl100k_base)
  - 39/39 test passano
- [x] **StructuralChunker** ✅:
  - File: `merlt/preprocessing/structural_chunker.py` (300+ lines)
  - Crea Chunk con URN interno (con comma) e URL esterno (senza comma)
  - Metadata: libro, titolo, capo, sezione da Brocardi position
  - 17/17 test passano
- [x] **IngestionPipelineV2** ✅:
  - File: `merlt/preprocessing/ingestion_pipeline_v2.py` (500+ lines)
  - USA (non modifica) urngenerator e visualex_client esistenti
  - Integra CommaParser + StructuralChunker
  - Crea nodi grafo con 21 properties per Norma
  - Brocardi enrichment: Dottrina (ratio, spiegazione), AttoGiudiziario (massime)
  - Prepara BridgeMapping objects per Bridge Table
  - 21/21 test passano
- [x] **BridgeBuilder** ✅:
  - File: `merlt/storage/bridge/bridge_builder.py` (175 lines)
  - Converte BridgeMapping → Bridge Table format
  - Mapping types: PRIMARY, HIERARCHIC, CONCEPT, DOCTRINE, JURISPRUDENCE
  - Batch insertion support
  - 14/14 test di integrazione con PostgreSQL reale (no mock)

## Cosa Abbiamo Fatto (Sessione Precedente - 3 Dic 2025, Sera)

- [x] **Schema definitivo API → Grafo** ✅:
  - File: `docs/08-iteration/SCHEMA_DEFINITIVO_API_GRAFO.md` (695 lines)
  - Complete node properties per 6 tipi (Norma con 21 properties, ConcettoGiuridico, Dottrina, AttoGiudiziario)
  - URN/URL separation: URN interno con comma (`;262:2~art1453~comma1`), URL esterno senza comma (`;262:2~art1453`)
  - Documentazione allegati: `:1` (Preleggi), `:2` (Codice Civile) del R.D. 262/1942
  - Mapping table completa API fields → Graph properties
  - Chunking strategy: comma-level universale (tutti articoli, no threshold)
  - Comma parser specification con regex rules
  - Esempio concreto Art. 1453: 9 nodes + 11 relations + 2 chunks + 10 bridge mappings
  - Schema **LOCKED** per evitare future migrations
- [x] **Piano ingestion 887 articoli** ✅:
  - File: `docs/08-iteration/INGESTION_PLAN_LIBRO_IV.md` (300+ lines)
  - Target: Libro IV Obbligazioni (art. 1321-2969)
  - Metriche: 887 articoli → ~2500 chunks → ~11k bridge mappings
  - Roadmap: 8 componenti, 30 ore effort estimate
  - Embedding separato post-ingestion (E5-large HuggingFace)
- [x] **Metodologia scientifica** ✅:
  - File: `docs/08-iteration/INGESTION_METHODOLOGY.md` (500+ lines)
  - Paper-ready con research questions, dataset specs, validation strategy
  - Zero-LLM pipeline per reproducibilità
  - Ethical considerations (GDPR, bias mitigation)

## Cosa Abbiamo Fatto (Sessione Precedente - 3 Dic 2025, Pomeriggio)

- [x] **Archiviato codice v1** in `merlt/archive_v1/`
- [x] **Struttura modulare v2**:
  - `merlt/interfaces/` - IStorageService, IExpert, IRLCFService
  - `merlt/services/` - ServiceRegistry (monolith/distributed)
  - `merlt/storage/` - FalkorDB, Bridge, Retriever
  - `merlt/orchestration/gating/` - ExpertGatingNetwork
  - `merlt/external_sources/visualex/` - Scrapers + tools integrati
- [x] **FalkorDBClient reale**:
  - Implementato con falkordb-py
  - Async wrapper con executor (library è sync)
  - Metodi: query(), shortest_path(), traverse(), health_check()
  - ✓ Testato: CREATE, MATCH funzionanti su database reale
- [x] **VisualexAPI integrato**:
  - Copiati scrapers (normattiva, brocardi, eurlex)
  - Copiati tools (urngenerator, text_op, http_client, etc.)
  - ✓ URN generator operativo con URN Normattiva reali
  - Fix import circolari (lazy import)
- [x] **Ingestion pipeline conforme a schema KG**:
  - Node types: Norma, ConcettoGiuridico, Dottrina, AttoGiudiziario
  - Relations: contiene, disciplina, commenta, interpreta
  - URN Normattiva (non ELI teorico)
  - Zero LLM per costruzione grafo base
- [x] **Docker setup completo**:
  - FalkorDB (6380), PostgreSQL (5432), Qdrant (6333), Redis (6379)
  - docker-compose.dev.yml per sviluppo
  - docker-compose.distributed.yml per produzione multi-container
- [x] **Primo batch ingestion** ✅:
  - 4 articoli ingested: Art. 1453-1456 c.c. (Risoluzione del contratto)
  - 6 nodi Norma (1 Codice + 4 Articoli)
  - 4 nodi ConcettoGiuridico
  - 4 relazioni 'contiene', 4 relazioni 'disciplina'
  - Test suite completo (4/4 passed)
  - Script standalone: `scripts/ingest_art_1453_1456.py`
  - Performance: query in 0.3-0.8ms
- [x] **Bridge Table implementata** ✅:
  - PostgreSQL schema con 11 colonne, 6 indici
  - SQLAlchemy ORM models (BridgeTableEntry)
  - Service class async (BridgeTable) con CRUD operations
  - Metodi: add_mapping(), add_mappings_batch(), get_nodes_for_chunk(), get_chunks_for_node()
  - ✓ 5/5 test passano (health_check, single/batch insert, bidirectional queries)
- [x] **Fix PostgreSQL port conflict**:
  - Identificato conflitto con PostgreSQL 14 nativo (Homebrew) su porta 5432
  - Container spostato su porta 5433
  - Analisi approfondita: lsof, docker logs, pg_hba.conf
  - Entrambe le istanze PostgreSQL coesistono senza problemi
- [x] **GraphAwareRetriever implementato** ✅:
  - Hybrid scoring: `final_score = α * similarity + (1-α) * graph_score`
  - Alpha learnable da RLCF feedback (bounds [0.3, 0.9])
  - Shortest path calculation con expert-specific traversal weights
  - Parametri esternalizzati in `merlt/config/retriever_weights.yaml`
  - 4 expert types: LiteralExpert, SystemicExpert, PrinciplesExpert, PrecedentExpert
  - ✓ 11/12 test passano (1 skipped per mancanza dati)
  - 510 LOC totali (models.py + retriever.py)

---

## Prossimi Passi Immediati

### COMPLETATI ✅

#### Ingestion Pipeline - COMPLETATA ✅
- [x] FalkorDB, Qdrant, PostgreSQL operativi
- [x] IngestionPipelineV2 con Brocardi enrichment
- [x] CommaParser + StructuralChunker
- [x] BridgeBuilder con mappings
- [x] Embedding generation con E5-large

#### Batch Ingestion - COMPLETATA ✅
- [x] CC Libro IV: 887 articoli
- [x] Costituzione: 139 articoli
- [x] CP Libro I: 263 articoli
- [x] EXP-007: 17 articoli con pipeline completa

#### GraphAwareRetriever - COMPLETATO ✅
- [x] Hybrid scoring (vector + graph)
- [x] Integrazione Bridge Table
- [x] Alpha parameter configurabile

---

### DA IMPLEMENTARE

#### Priorità 1: RQ4 Benchmark (EXP-008)
- [ ] Script benchmark latenza Bridge vs join
- [ ] Misurazioni formali con metriche
- [ ] Documentazione risultati

#### Priorità 2: RQ5 Expert con Tools (EXP-009)
- [ ] Interfaccia base `ExpertWithTools`
- [ ] `LiteralExpert` con tools (get_exact_text, get_definitions)
- [ ] `SystemicExpert` con tools (get_legislative_history)
- [ ] `PrinciplesExpert` con tools (get_constitutional_basis)
- [ ] `PrecedentExpert` con tools (search_cases, get_citation_chain)
- [ ] `ExpertGatingNetwork` (MoE-style)
- [ ] Esperimento comparativo

#### Priorità 3: RQ6 RLCF Multilivello (EXP-010)
- [ ] Schema DB per authority multilivello
- [ ] `MultilevelAuthority` class
- [ ] `LearnableSystemParameters` (theta_traverse, theta_gating, theta_rerank)
- [ ] Policy gradient training (REINFORCE)
- [ ] Feedback collection endpoint
- [ ] Esperimento convergenza

---

## Decisioni Prese

| Data | Decisione | Motivazione |
|------|-----------|-------------|
| 2025-12-02 | FalkorDB invece di Neo4j | 496x piu veloce, Cypher compatibile, open source |
| 2025-12-02 | Expert autonomi con tools | Ogni expert cerca fonti specifiche per la sua prospettiva |
| 2025-12-02 | Bridge Table per integrazione | Unifica vector search e graph traversal |
| 2025-12-02 | RLCF multilivello | Authority diversa per retrieval/reasoning/synthesis e per dominio |
| 2025-12-02 | Pesi apprendibili | theta_traverse, theta_gating, theta_rerank migliorano con feedback |
| 2025-12-02 | Schema grafo hardcoded | Basato su discussione accademica, non generato da LLM |
| 2025-12-03 | URN Normattiva (non ELI) | Formato reale per Normattiva.it, non teorico europeo |
| 2025-12-03 | VisualexAPI integrato | Scrapers embedded per deploy monolith durante tesi |
| 2025-12-03 | URN/URL separation | URN interno con comma per granularità, URL esterno senza comma per linking |
| 2025-12-03 | Allegato :2 per CC | Codice Civile è Allegato 2 del R.D. 262/1942, Preleggi è Allegato 1 |
| 2025-12-03 | Chunking comma-level universale | No threshold, tutti articoli splittati a livello comma |
| 2025-12-03 | Schema LOCKED | 21 properties per Norma, no future changes senza migration |

---

## Domande Aperte

1. **FalkorDB production**: Limiti di memoria per il nostro dataset?
2. **Expert tools**: Quante chiamate LLM per expert? Budget?
3. **RLCF validation**: Come simulare esperti per test iniziali?

---

## Contesto per Claude

### Cosa devi sapere per riprendere:
- L'utente e uno studente di giurisprudenza (non programmatore)
- Sta facendo una tesi sulla "sociologia computazionale del diritto"
- Ha 6 mesi a tempo pieno, estendibili a 1 anno
- Il codice e stato scritto con LLM (vibe coding)
- Budget limitato (~200-500 euro per API)
- Preferisce comunicare in italiano
- **IMPORTANTE**: Siamo in fase di riprogettazione architettura v2

### File chiave da leggere:
1. `CLAUDE.md` - Istruzioni generali progetto
2. `docs/claude-context/LIBRARY_VISION.md` - Principi guida libreria
3. `docs/claude-context/LIBRARY_ARCHITECTURE.md` - Architettura componenti
4. `docs/experiments/INDEX.md` - Stato esperimenti (7 completati)
5. `docs/architecture/overview.md` - Mappa tecnica v2
6. `docs/archive/08-iteration/INGESTION_METHODOLOGY.md` - Research Questions RQ1-RQ6

### Pattern da seguire:
- Documentare prima di implementare
- Reality-check frequenti
- Test incrementali
- Comunicare in italiano, codice in inglese

---

## Quick Reference

```bash
# Avviare ambiente
cd /Users/gpuzio/Desktop/CODE/MERL-T_alpha
source .venv/bin/activate  # Python 3.12

# Database (v2 - FalkorDB + Qdrant + PostgreSQL + Redis)
docker-compose -f docker-compose.dev.yml up -d

# Verifica database
docker-compose -f docker-compose.dev.yml ps
redis-cli -p 6380 ping  # FalkorDB
curl http://localhost:6333/  # Qdrant

# Test
pytest tests/ -v

# Test imports
python -c "from merlt import LegalKnowledgeGraph; print('OK')"

# Test FalkorDB
python -c "from merlt.storage.graph import FalkorDBClient; import asyncio; asyncio.run(FalkorDBClient().health_check())"
```
