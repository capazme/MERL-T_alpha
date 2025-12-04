# Experiments Index

> **Indice cronologico di tutti gli esperimenti MERL-T**
> Aggiornare questo file quando si crea un nuovo esperimento

---

## Esperimenti per Fase

### Fase 1: Data Ingestion
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| [EXP-001](./EXP-001_ingestion_libro_iv/) | ingestion_libro_iv | **COMPLETED** | 2025-12-04 | RQ1,RQ2 | Prima ingestion completa: 887 articoli Libro IV CC |
| [EXP-002](./EXP-002_brocardi_enrichment/) | brocardi_enrichment | **RUNNING** | 2025-12-04 | RQ3 | Enrichment Brocardi: Relazioni Guardasigilli, link articoli citati |

### Fase 2: Retrieval & Search
| ID | Nome | Status | Data | RQ | Descrizione |
|----|------|--------|------|-----|-------------|
| - | - | - | - | - | - |

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
| Completati | **1** |
| In corso | **1** |
| Pianificati | 0 |
| Falliti | 0 |

---

## Timeline

```
2025-12
├── 03: EXP-001 creato (PLANNED)
├── 03: EXP-001 avviato (RUNNING)
├── 04: EXP-001 completato (COMPLETED) - 100% success, 887 articoli
├── 04: BrocardiScraper ampliato (Relazioni Guardasigilli)
├── 04: EXP-002 creato (PLANNED)
├── 04: MAPPING.md + batch_enrich_brocardi.py creati
├── 04: Test subset (Art. 1285-1287) - PASSED
└── 04: EXP-002 avviato (RUNNING)

2025-01
└── ...
```

---

## Research Questions Coverage

| RQ | Esperimenti | Status |
|----|-------------|--------|
| RQ1: Chunking comma-level | EXP-001 | **Completed** |
| RQ2: Struttura gerarchica | EXP-001 | **Completed** |
| RQ3: Enrichment Brocardi | EXP-002 | Planned |
| RQ4: Bridge Table performance | - | Not started |
| RQ5: Expert specialization | - | Not started |
| RQ6: RLCF convergence | - | Not started |

---

*Ultimo aggiornamento: 2025-12-04*
