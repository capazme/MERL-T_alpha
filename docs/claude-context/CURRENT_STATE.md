# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 20 Dicembre 2025 |
| **Fase progetto** | **Expert/Tools Implementation** - Preparazione architettura |
| **Prossimo obiettivo** | Weight System Foundation + Tool Framework |
| **Blocchi attivi** | Nessuno |

---

## Cosa Abbiamo Fatto (Sessione Corrente - 20 Dic 2025)

### Riallineamento Documentazione - COMPLETATO ✅

- Aggiornato INDEX.md esperimenti con EXP-013, 014, 015, 016
- Convertito EXP-008/009 in cartelle standard
- Spostati planning docs in claude-context/PLANNING/
- Corrette statistiche (18 esperimenti, 15 completati)
- Rinumerati esperimenti pianificati (EXP-017, EXP-018)

### Weight System - COMPLETATO ✅

Implementato modulo `merlt/weights/`:
- **WeightStore**: Persistenza pesi con fallback YAML, caching, versioning
- **WeightLearner**: Aggiornamento pesi via RLCF feedback loop
- **ExperimentTracker**: A/B testing con assegnazione deterministica

**File creati:**
| File | Descrizione |
|------|-------------|
| `merlt/weights/config.py` | Pydantic models (WeightConfig, LearnableWeight, etc.) |
| `merlt/weights/store.py` | WeightStore con fallback YAML |
| `merlt/weights/learner.py` | WeightLearner per RLCF feedback |
| `merlt/weights/experiment.py` | ExperimentTracker per A/B testing |
| `merlt/weights/config/weights.yaml` | Config unificata (4 Expert + RLCF + Gating) |
| `tests/weights/*.py` | 50 test per il modulo |

### Piano Expert/Tools In Corso

Prossimi step:
- STEP 3: Tool Framework Base (BaseTool, ToolRegistry)
- STEP 4: SemanticSearchTool
- STEP 5: LiteralExpert completo

---

## Cosa Abbiamo Fatto (Sessioni Precedenti - 15 Dic 2025)

### EXP-014: Full Ingestion Libro IV - COMPLETATO ✅

Ingestion completa del Libro IV del Codice Civile (887 articoli) con ottimizzazioni.

#### Risultati Chiave

| Metrica | Valore | Note |
|---------|--------|------|
| Articoli processati | 887/887 | 100% copertura |
| Nodi grafo totali | 27,740 | +103% vs baseline |
| Relazioni totali | 43,935 | +1137% vs baseline |
| Embeddings multi-source | 5,926 | norma+spiegazione+ratio+massime |
| Entità estratte | 3,049 | +2,233 merge |
| Durata totale | 2h 43m | 7.2s/articolo backbone |

#### Distribuzione Nodi

```
AttoGiudiziario:    9,917   (giurisprudenza)
Dottrina:           2,609   (chunk enrichment)
ConcettoGiuridico:  2,571   (entità estratte)
Comma:              1,798   (struttura normativa)
ModalitaGiuridica:  1,610   (entità estratte)
Norma:              1,538   (articoli + gerarchie)
+ altri 16 tipi di entità...
─────────────────────────────
TOTALE:            27,740
```

#### Nuova Feature: BatchIngestionPipeline

Implementata ottimizzazione per parallelizzazione:

| Aspetto | Prima | Dopo | Speedup |
|---------|-------|------|---------|
| HTTP Fetches | Sequenziali | 8 paralleli | ~5x |
| Embeddings | 1 per volta | Batch 32 | ~10x |
| Singolo articolo | ~15-20s | 7.2s | **2-3x** |

#### File Creati

| File | Descrizione |
|------|-------------|
| `merlt/pipeline/batch_ingestion.py` | BatchIngestionPipeline |
| `tests/pipeline/test_batch_ingestion.py` | 16 test validazione |

#### File Modificati

| File | Modifica |
|------|----------|
| `merlt/core/legal_knowledge_graph.py` | Aggiunto `ingest_batch()` |
| `merlt/pipeline/ingestion.py` | Fix chunk_text in BridgeMapping |
| `scripts/exp014_full_ingestion.py` | Supporto `--batch-size`, `--max-concurrent` |

---

## Stato Database Corrente

| Storage | Nome | Contenuto |
|---------|------|-----------|
| **FalkorDB** | `merl_t_dev` | 27,740 nodi, 43,935 relazioni |
| **Qdrant** | `merl_t_dev_chunks` | 5,926 vectors (multi-source) |
| **Bridge Table** | `bridge_table` | 27,114 mappings (100% chunk_text) |

### Copertura Libro IV

- 887/887 articoli (100%)
- 1,798 commi
- 17,227 relazioni DISCIPLINA
- 5,926 embeddings (norma + spiegazione + ratio + massime)

---

## Cosa Abbiamo Fatto (Sessioni Precedenti)

### 14 Dicembre 2025

- Fix bug rubrica tra parentesi (`parsing.py`)
- Implementazione validation framework EXP-014
- Backup baseline pre-ingestion

### 13 Dicembre 2025

- Integrazione iusgraph → merlt/rlcf
- Database cleanup (eliminati Dottrina generici)
- Task handlers per RLCF

### 10 Dicembre 2025

- Enrichment Pipeline Core implementata
- 17 tipi entità estraibili
- 35 tipi relazioni

---

## API Disponibili

```python
from merlt import LegalKnowledgeGraph, MerltConfig

kg = LegalKnowledgeGraph()
await kg.connect()

# Ingestion singolo articolo
result = await kg.ingest_norm("codice civile", "1453")

# Ingestion batch (NUOVO - ottimizzato)
result = await kg.ingest_batch(
    tipo_atto="codice civile",
    article_range=(1173, 2059),
    batch_size=15,
    max_concurrent_fetches=8,
)

# Enrichment LLM
config = EnrichmentConfig(...)
result = await kg.enrich(config)

# Search
results = await kg.search("responsabilità contrattuale")
```

---

## Prossimi Passi

### Priorità 1: RAG Validation
- [ ] Benchmark semantic search su Libro IV
- [ ] Test multi-source embeddings (spiegazione vs norma)
- [ ] Metriche Recall@K, MRR

### Priorità 2: RQ4 Benchmark (Bridge Table)
- [ ] Script benchmark latenza Bridge vs join
- [ ] Misurazioni formali

### Priorità 3: RQ5 Expert con Tools
- [ ] Interfaccia ExpertWithTools
- [ ] Expert specializzati (Literal, Systemic, Principles, Precedent)

---

## Quick Reference

```bash
# Avviare ambiente
cd /Users/gpuzio/Desktop/CODE/MERL-T_alpha
source .venv/bin/activate

# Database
docker-compose -f docker-compose.dev.yml up -d

# Test
pytest tests/ -v  # 397+ test

# Status grafo
python3 -c "
from falkordb import FalkorDB
db = FalkorDB(host='localhost', port=6380)
g = db.select_graph('merl_t_dev')
print('Nodi:', g.query('MATCH (n) RETURN count(n)').result_set[0][0])
print('Relazioni:', g.query('MATCH ()-[r]->() RETURN count(r)').result_set[0][0])
"

# Ingestion batch
python scripts/exp014_full_ingestion.py --full --batch-size 15 --max-concurrent 8
```

---

## Decisioni Prese (Nuove)

| Data | Decisione | Motivazione |
|------|-----------|-------------|
| 2025-12-15 | BatchIngestionPipeline | Parallelizzazione per M4 16GB, 2-3x speedup |
| 2025-12-15 | Multi-source embeddings | Semantic search via spiegazione/ratio, non solo testo |
| 2025-12-15 | chunk_text in Bridge | 100% per RAG debugging |

---

## Contesto per Claude

### Cosa devi sapere per riprendere:
- L'utente è uno studente di giurisprudenza (non programmatore)
- Sta facendo una tesi sulla "sociologia computazionale del diritto"
- **EXP-014 COMPLETATO**: Knowledge Graph Libro IV pronto
- 27,740 nodi, 43,935 relazioni, 5,926 embeddings
- Preferisce comunicare in italiano

### File chiave da leggere:
1. `CLAUDE.md` - Istruzioni generali progetto
2. `docs/claude-context/LIBRARY_VISION.md` - Principi guida
3. `docs/experiments/EXP-014_full_ingestion/README.md` - Ultimo esperimento
4. `docs/experiments/INDEX.md` - Stato esperimenti

### Pattern da seguire:
- Documentare prima di implementare
- Reality-check frequenti
- Test incrementali
- Comunicare in italiano, codice in inglese
