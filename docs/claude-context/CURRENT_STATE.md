# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 13 Dicembre 2025 (pomeriggio) |
| **Fase progetto** | **RLCF Consolidation** - Componenti iusgraph integrati in merlt |
| **Prossimo obiettivo** | Test enrichment con manuale Torrente (ON HOLD) |
| **Blocchi attivi** | Nessuno |

---

## Cosa Abbiamo Fatto (Sessione Corrente - 13 Dic 2025, Pomeriggio)

### Integrazione iusgraph → merlt/rlcf - COMPLETATO ✅

Incorporati organicamente i componenti utili da `iusgraph/` in `merlt/rlcf/`,
poi archiviata la cartella originale.

#### Nuovi File Creati

| File | Contenuto |
|------|-----------|
| `merlt/rlcf/validation/__init__.py` | Export moduli validation |
| `merlt/rlcf/validation/models.py` | ValidationIssue, ValidationReport, IssueSeverity, IssueType, ValidationConfig, FixResult |
| `merlt/rlcf/metrics.py` | MetricsTracker singleton per tracking LLM calls/costi |
| `merlt/rlcf/task_handlers/__init__.py` | Factory `get_handler()`, registry handler |
| `merlt/rlcf/task_handlers/base.py` | TaskHandler base class |
| `merlt/rlcf/task_handlers/qa.py` | QAHandler, StatutoryRuleQAHandler |
| `merlt/rlcf/task_handlers/retrieval.py` | RetrievalValidationHandler |
| `merlt/rlcf/task_handlers/classification.py` | ClassificationHandler |

#### Bug Fix Importante

**`merlt/rlcf/aggregation.py`** importava `from .task_handlers import get_handler`
ma il modulo NON ESISTEVA. Ora il bug è risolto - task_handlers esiste con:
- 11 task types supportati
- Factory pattern per istanziazione
- Handler specializzati per QA, Retrieval, Classification

#### Struttura RLCF Aggiornata

```
merlt/rlcf/
├── __init__.py              # Aggiornato con nuovi export
├── ai_service.py            # OpenRouterService
├── aggregation.py           # AggregationEngine (fix import!)
├── authority.py             # AuthorityModule
├── config.py                # Configurazione RLCF
├── database.py              # SQLAlchemy Base
├── models.py                # SQLAlchemy models (User, Task, Feedback...)
├── metrics.py               # ✨ NUOVO: MetricsTracker singleton
├── validation/              # ✨ NUOVO: Validation system
│   ├── __init__.py
│   └── models.py            # ValidationIssue, ValidationReport, etc.
└── task_handlers/           # ✨ NUOVO: Task type handlers
    ├── __init__.py          # get_handler() factory
    ├── base.py              # TaskHandler base
    ├── qa.py                # QA, STATUTORY_RULE_QA
    ├── retrieval.py         # RETRIEVAL_VALIDATION
    └── classification.py    # CLASSIFICATION
```

#### Design per Frontend React/Vite

Tutti i nuovi modelli sono progettati per integrazione API:
- `to_dict()` per JSON serialization
- `from_dict()` per JSON deserialization
- Nessuna dipendenza CLI (rimossa `interactive.py`)

#### Cleanup

- `iusgraph/` archiviata in `_archive/iusgraph_20251213/`
- `_archive/` aggiunta a `.gitignore`

---

## Cosa Abbiamo Fatto (Sessione Precedente - 13 Dic 2025, Mattina)

### Database Cleanup - COMPLETATO ✅

Pulizia completa dei database per mantenere solo lo scheletro normativo.

#### Operazioni Eseguite

**FalkorDB:**
- ✅ Eliminati 2,609 nodi Dottrina generici da `merl_t_exp_libro_iv_cc`
- ✅ Cancellati 7 grafi di test:
  - `merl_t_legal`, `merl_t_dev`, `merl_t_integration_test`
  - `merl_t_test_multi`, `merl_t_exp_test`, `merl_t_test_ms`, `merl_t_exp_sample`
- ✅ Rinominato `merl_t_exp_libro_iv_cc` → `merl_t_dev` (via Redis RENAME)

**Qdrant:**
- ✅ Eliminate collection di test: `merl_t_integration_test`
- ✅ Rinominata `exp_libro_iv_cc` → `merl_t_dev_chunks` (5,330 vectors copiati)
- ✅ Cancellata collection originale

#### Stato Finale Database

| Storage | Nome | Contenuto |
|---------|------|-----------|
| **FalkorDB** | `merl_t_dev` | 13,377 nodi, 14,772 relazioni |
|  | └─ Norma | 1,004 nodi (scheletro normativo) |
|  | └─ Comma | 2,546 nodi (struttura articoli) |
|  | └─ AttoGiudiziario | 9,827 nodi (massime giurisprudenziali) |
| **Qdrant** | `merl_t_dev_chunks` | 5,330 vectors (embeddings multi-source) |

**Scheletro Normativo Pulito:**
- ✓ Nodi normativi (Norma, Comma) da Normattiva
- ✓ Massime giurisprudenziali (AttoGiudiziario) da Brocardi
- ✓ Embeddings multi-source (norma, spiegazione, ratio, massime)
- ✗ Nodi Dottrina eliminati (saranno ricreati con enrichment strutturato)

---

## Cosa Abbiamo Fatto (Sessione Precedente - 10 Dic 2025)

### Enrichment Pipeline Core - COMPLETATO ✅

Creata pipeline di enrichment come funzionalità core del package `merlt`.
L'enrichment estrae entità strutturate (concetti, principi, definizioni, etc.)
da fonti testuali (Brocardi, manuali PDF) usando LLM.

#### Architettura Implementata

```
merlt/pipeline/enrichment/
├── __init__.py              # EnrichmentPipeline, EnrichmentConfig
├── config.py                # EnrichmentConfig, EnrichmentScope
├── models.py                # EntityType (17), RelationType (35), EnrichmentStats
├── checkpoint.py            # CheckpointManager per resume
├── pipeline.py              # EnrichmentPipeline (orchestratore)
├── config/
│   ├── extractors.yaml      # Prompt LLM per 17 tipi entità
│   ├── linkers.yaml         # Configurazione dedup/linking
│   ├── writers.yaml         # Query Cypher per 17 tipi nodi
│   └── schema.yaml          # Schema LKIF: 23 nodi, 65+ relazioni
├── sources/
│   ├── base.py              # BaseEnrichmentSource
│   ├── brocardi.py          # BrocardiEnrichmentSource
│   └── manual.py            # ManualEnrichmentSource (PDF)
├── extractors/
│   ├── base.py              # BaseEntityExtractor
│   ├── concept.py           # ConceptExtractor
│   ├── principle.py         # PrincipleExtractor
│   ├── definition.py        # DefinitionExtractor
│   └── generic.py           # GenericExtractor + create_extractor()
├── linkers/
│   ├── normalization.py     # normalize_name()
│   └── entity_linker.py     # EntityLinker (dedup)
├── writers/
│   └── graph_writer.py      # EnrichmentGraphWriter
└── prompts/
    ├── concetto.txt
    ├── principio.txt
    └── definizione.txt
```

#### Schema Entità (17 tipi estraibili)

| Priorità | Tipi |
|----------|------|
| 1 (Core) | ConcettoGiuridico, PrincipioGiuridico, DefinizioneLegale |
| 2 (Soggetti) | SoggettoGiuridico, Ruolo, ModalitaGiuridica |
| 3 (Fatti/Atti) | FattoGiuridico, AttoGiuridicoEntita, Procedura, Termine, EffettoGiuridico, Responsabilita, Rimedio |
| 4 (Avanzate) | Sanzione, Caso, Eccezione, Clausola |

#### Relazioni (35 tipi)

- **Strutturali**: CONTIENE, MODIFICA, CITA
- **Semantiche**: DISCIPLINA, ESPRIME_PRINCIPIO, DEFINISCE, PREVEDE, ATTRIBUISCE
- **Gerarchiche**: SPECIES, GENUS, IMPLICA, ESCLUDE
- **Principi**: BILANCIA_CON, DEROGA, SPECIFICA
- **Causali**: CAUSA, PRESUPPONE, GENERA
- **Soggettive**: TITOLARE_DI, CONTROPARTE, ASSUME_RUOLO
- **Procedurali**: FASE_DI, PRECEDE, ATTIVA
- **Dottrinali**: COMMENTA, SPIEGA, INTERPRETA, APPLICA, ILLUSTRA
- **Rimedi**: TUTELA, REAGISCE_A, ECCEZIONE_A

#### API Target

```python
from merlt import LegalKnowledgeGraph
from merlt.pipeline.enrichment import EnrichmentConfig

kg = LegalKnowledgeGraph()
await kg.connect()

# Una riga per enrichment
config = EnrichmentConfig.for_libro_iv()
result = await kg.enrich(config)

print(result.summary())
# ══════════════════════════════════════════════════════════
# ENRICHMENT RESULT
# Contents processati: 1500
# ENTITÀ CORE (priorità 1):
#   Concetti:      150 (+30 merge)
#   Principi:       45 (+10 merge)
#   Definizioni:    80 (+15 merge)
# ...
```

#### File Creati/Modificati

| File | Descrizione |
|------|-------------|
| `merlt/pipeline/enrichment/**` | Nuovo package (15+ file) |
| `merlt/core/legal_knowledge_graph.py` | Aggiunto `enrich()`, `cleanup_dottrina()` |
| `merlt/pipeline/enrichment/config/*.yaml` | 4 file config YAML |

---

## Cosa Abbiamo Fatto (Sessione Precedente - 8 Dic 2025, Notte)

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
