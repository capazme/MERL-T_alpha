# Experiments Index

> **Indice cronologico di tutti gli esperimenti MERL-T**
> Aggiornare questo file quando si crea un nuovo esperimento

---

## Esperimenti per Fase

### Fase 1: Data Ingestion
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| [EXP-001](./EXP-001_ingestion_libro_iv/) | ingestion_libro_iv | **COMPLETED** | 2025-12-03/04 | RQ1-4 | Ingestion completa 887 articoli Libro IV CC con Brocardi enrichment |

> **Nota**: EXP-002 (Brocardi Enrichment) è stato integrato direttamente in EXP-001 durante il re-run del 4 dicembre 2025.

### Fase 2: Retrieval & Search
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| [EXP-002](./EXP-002_rag_pipeline_test/) | rag_pipeline_test | **COMPLETED** | 2025-12-04 | RQ4-5 | Test end-to-end RAG: semantic search + Bridge Table + graph enrichment |

### Fase 3: Expert Reasoning
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| - | - | - | - | - | - |

### Fase 4: RLCF Learning
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| - | - | - | - | - | - |

---

## Statistiche

| Metrica | Valore |
|---------|--------|
| Esperimenti totali | 2 |
| Completati | **2** |
| In corso | 0 |
| Pianificati | 0 |
| Falliti | 0 |

---

## Timeline

```
2025-12-03
├── EXP-001 design document creato
├── Pipeline v2 completata (CommaParser + StructuralChunker + IngestionPipelineV2)
├── EXP-001 Run 1 avviato (23:32)
└── EXP-001 Run 1 completato (00:14) - 890 nodi, 892 relazioni (solo Normattiva)

2025-12-04
├── BrocardiScraper ampliato (Relazioni Guardasigilli)
├── Data loss Docker → fix persistenza locale (./data/)
├── Bug fix pipeline (isinstance checks, massime conversion)
├── EXP-001 Run 2 avviato (02:17) - con Brocardi integrato
├── EXP-001 Run 2 completato (02:24) - 3,346 nodi, 25,574 relazioni
├── treextractor.py esteso con gerarchia completa
├── Integrazione treextractor fallback in pipeline
├── EXP-001 Run 3 avviato (19:05) - aggiornamento gerarchia
├── EXP-001 Run 3 completato (19:07) - 3,462 nodi, 26,577 relazioni
├── EXP-001 Run 4 (embedding) avviato (19:46)
├── EXP-001 Run 4 completato (19:55) - 2,546 embeddings in Qdrant
├── Script test_rag_pipeline.py creato
├── EXP-002 completato - RAG pipeline testing
├── Bug discovery: massime con "unknown_NNN" e dati sporchi
├── Fix BrocardiScraper: _parse_massima() con parsing strutturato
├── EXP-001 Run 5 avviato (21:42) - re-run sole massime
├── EXP-001 Run 5 completato (22:52) - 9,775 AttoGiudiziario (+1,082%)
└── GRAPH_EDA.md generato con analisi esplorativa completa
```

---

## Research Questions Coverage

| RQ | Descrizione | Esperimento | Status |
|----|-------------|-------------|--------|
| RQ1 | Chunking comma-level preserva integrità semantica? | EXP-001 | **Verified** ✅ |
| RQ2 | Struttura gerarchica migliora navigabilità? | EXP-001 | **Verified** ✅ |
| RQ3 | Enrichment Brocardi aggiunge valore misurabile? | EXP-001 | **Verified** ✅ |
| RQ4 | Bridge Table riduce latenza vs join runtime? | EXP-001 | **Data Ready** |
| RQ5 | Expert specialization migliora qualità? | - | Not started |
| RQ6 | RLCF converge a pesi ottimali? | - | Not started |

---

## Risultati Chiave EXP-001

### Run 1 (3 dicembre 2025) - Solo Normattiva
| Metrica | Valore |
|---------|--------|
| Articoli | 887/887 (100%) |
| Nodi Norma | 890 |
| Relazioni | 892 |
| Dottrina | 0 |
| AttoGiudiziario | 0 |

### Run 2 (4 dicembre 2025) - Con Brocardi
| Metrica | Valore | Delta |
|---------|--------|-------|
| Articoli | 887/887 (100%) | - |
| Nodi totali | **3,346** | +274% |
| - Norma | 889 | - |
| - Dottrina | 1,630 | +∞ |
| - AttoGiudiziario | 827 | +∞ |
| Relazioni totali | **25,574** | +2,768% |
| - :interpreta | 23,056 | +∞ |
| - :commenta | 1,630 | +∞ |
| - :contiene | 888 | - |

### Run 3 (4 dicembre 2025, sera) - Gerarchia Completa
| Metrica | Valore | Delta |
|---------|--------|-------|
| **Nodi totali** | **3,462** | +116 |
| - Norma | **1,005** | +116 |
|   - codice | 1 | - |
|   - libro | 1 | - |
|   - titolo | 9 | +9 |
|   - capo | 51 | +51 |
|   - sezione | 56 | +56 |
|   - articolo | 887 | - |
| - Dottrina | 1,630 | - |
| - AttoGiudiziario | 827 | - |
| **Relazioni totali** | **26,577** | +1,003 |
| - :contiene | **1,891** | +1,003 |

### Run 4 (4 dicembre 2025, sera) - Embedding Generation
| Metrica | Valore |
|---------|--------|
| Modello | `intfloat/multilingual-e5-large` |
| Dimensione | 1024 |
| Device | MPS (Apple Silicon) |
| Chunks processati | **2,546** |
| Embeddings generati | **2,546** |
| Errori | **0** |
| Success rate | **100%** |
| Tempo | ~8 minuti |
| Collection Qdrant | `merl_t_chunks` |

### Run 5 (4 dicembre 2025, notte) - Massime Fix & Re-ingestion
| Metrica | Pre-Fix | Post-Fix | Delta |
|---------|---------|----------|-------|
| AttoGiudiziario | 827 | **9,775** | **+1,082%** |
| Con numero valido | 0 | 9,771 | +∞ |
| Con anno | 0 | 9,771 | +∞ |
| 'unknown' residui | 827 | **0** | -100% |
| :interpreta | 23,056 | 11,182 | -51% (dedup) |

**Note**: La riduzione delle relazioni :interpreta è dovuta alla corretta deduplicazione. Prima ogni massima con `unknown_NNN` era un nodo separato; ora le stesse sentenze citate da più articoli condividono un singolo nodo.

**Storage Completo dopo Run 5:**
| Storage | Contenuto |
|---------|-----------|
| FalkorDB | **12,410 nodi**, 14,703 relazioni |
| PostgreSQL | 2,546 bridge mappings |
| Qdrant | 2,546 vectors (1024 dim) |

**Breakdown Nodi:**
| Label | Count | % |
|-------|-------|---|
| Norma | 1,005 | 8.1% |
| Dottrina | 1,630 | 13.1% |
| AttoGiudiziario | 9,775 | 78.8% |

---

*Ultimo aggiornamento: 2025-12-04 23:10*
