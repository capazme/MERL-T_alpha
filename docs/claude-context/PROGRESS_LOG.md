# MERL-T Progress Log

> **Log cronologico di tutte le sessioni di lavoro**
> Aggiungere entry alla fine di ogni sessione significativa

---

## Formato Entry

```markdown
## [DATA] - Titolo Sessione

**Durata**: X ore
**Obiettivo**: Cosa volevamo fare
**Risultato**: Cosa abbiamo fatto

### Completato
- Item 1
- Item 2

### Problemi Incontrati
- Problema 1 -> Soluzione

### Prossimi Passi
- Step 1
- Step 2

### Note per Future Sessioni
- Cosa ricordare

---
```

---

## Log Sessioni

### 2025-12-03 (Sessione 3) - Ristrutturazione Codice v2

**Durata**: ~2 ore
**Obiettivo**: Rimuovere codice v1, creare struttura cartelle v2
**Risultato**: Completato - Struttura v2 pronta con placeholder

#### Completato
- Archiviato codice v1 in `backend/archive_v1/`:
  - `orchestration/agents/` (KGAgent, APIAgent, VectorDBAgent)
  - `preprocessing/neo4j_*` (neo4j_connection, neo4j_writer, etc.)
  - `orchestration/experts/` singoli file (literal_interpreter.py, etc.)
- Creata nuova struttura cartelle v2:
  - `backend/storage/` (nuovo layer)
  - `backend/storage/falkordb/` - FalkorDBClient placeholder
  - `backend/storage/bridge/` - BridgeTable placeholder
  - `backend/storage/retriever/` - GraphAwareRetriever placeholder
  - `backend/orchestration/gating/` - ExpertGatingNetwork placeholder
  - `backend/orchestration/experts/expert_with_tools.py` - ExpertWithTools + 4 expert v2
- Fixato tutti gli import rotti dopo archiviazione:
  - `langgraph_workflow.py` - commentato import v1
  - `preprocessing/*.py` - commentato import neo4j
  - `rlcf_framework/pipeline_integration.py` - commentato import neo4j
- Aggiornati tutti `__init__.py` con export corretti
- Verificato import con Python 3.12

#### Struttura v2 Finale
```
backend/
├── storage/                     # NEW
│   ├── falkordb/               # FalkorDBClient
│   ├── bridge/                 # BridgeTable
│   └── retriever/              # GraphAwareRetriever
├── orchestration/
│   ├── gating/                 # NEW - ExpertGatingNetwork
│   └── experts/
│       ├── base.py             # Kept
│       ├── synthesizer.py      # Kept
│       └── expert_with_tools.py # NEW v2
└── archive_v1/                 # Old code
```

#### Problemi Incontrati
- Import rotti dopo archiviazione -> risolto commentando con note "v2: ..."
- venv con path sbagliato -> utente ha ricreato con Python 3.12

#### Prossimi Passi
1. Avviare FalkorDB container (Docker)
2. Implementare FalkorDBClient reale (con falkordb-py)
3. Implementare BridgeTable reale (con SQLAlchemy)
4. Implementare GraphAwareRetriever reale
5. Collegare ExpertWithTools a retriever

---

### 2025-12-02 (Sessione 2) - Riprogettazione Architettura v2

**Durata**: ~3 ore
**Obiettivo**: Documentare e cristallizzare l'architettura v2 prima di implementare
**Risultato**: Completato - 5 documenti architetturali v2 creati/aggiornati

#### Completato
- Archiviati documenti v1 in `docs/03-architecture/archive/`
- Creato/aggiornato `02-orchestration-layer.md` (v2):
  - Router semplificato (decide solo quali expert attivare)
  - ExpertGatingNetwork (MoE-style, pesi apprendibili)
  - ExpertWithTools (expert autonomi con retrieval)
  - ExpertTraversalWeights (theta_traverse per expert)
- Creato/aggiornato `03-reasoning-layer.md` (v2):
  - Expert autonomi con tools specifici
  - Prompt per i 4 expert (Literal, Systemic, Principles, Precedent)
  - Gating Network per pesare expert
  - Synthesizer convergent/divergent
- Creato/aggiornato `04-storage-layer.md` (v2):
  - FalkorDB invece di Neo4j (496x piu veloce)
  - Bridge Table (chunk_id <-> graph_node_id mapping)
  - GraphAwareRetriever (hybrid vector + graph)
  - Score = alpha * similarity + (1-alpha) * graph_score
- Creato/aggiornato `05-learning-layer.md` (v2):
  - MultilevelAuthority (per livello + per dominio)
  - LearnableSystemParameters (theta_traverse, theta_gating, theta_rerank)
  - Policy Gradient (REINFORCE con baseline)
  - Resilienza (temporal decay, graph events, recency weighting)
- Aggiornato `docs/SYSTEM_ARCHITECTURE.md` a v2
- Aggiornato `docs/claude-context/CURRENT_STATE.md`

#### Decisioni Architetturali v2
| Componente | v1 | v2 | Motivazione |
|------------|----|----|-------------|
| Expert | Passivi | Autonomi con tools | Retrieval specializzato per prospettiva |
| Graph DB | Neo4j | FalkorDB | 496x piu veloce, Cypher compatibile |
| Vector-Graph | Separati | Bridge Table | Retrieval ibrido |
| RLCF | Scalare | Multilivello | Authority per competenza specifica |
| Pesi | Statici | Apprendibili | Migliorano con feedback |

#### Problemi Incontrati
- Nessun problema tecnico, sessione di sola documentazione

#### Prossimi Passi
1. Setup FalkorDB container
2. Creare Bridge Table in PostgreSQL
3. Implementare ExpertWithTools class
4. Implementare GraphAwareRetriever
5. Schema RLCF multilivello

#### Note per Future Sessioni
- Prima di implementare, rileggere i 4 documenti v2
- Lo schema del grafo e HARDCODED (non generato da LLM)
- Testare FalkorDB prima di migrare dati
- Budget API: considerare quante chiamate LLM per expert

---

### 2025-12-02 (Sessione 1) - Analisi Iniziale e Setup

**Durata**: ~2 ore
**Obiettivo**: Capire lo stato del progetto e stabilire metodologia di lavoro
**Risultato**: Completato

#### Completato
- Analisi completa della documentazione esistente
- Reality-check tecnico del codice (Working Prototype al 70%)
- Identificazione blocchi critici:
  - Neo4j e Qdrant vuoti (retrieval non funziona)
  - API key LLM mancante
  - Mai testato end-to-end
- Creazione mappa sistema: `docs/SYSTEM_ARCHITECTURE.md`
- Definizione KPI e metriche per la tesi
- Setup struttura documentazione per lavoro continuativo:
  - `docs/claude-context/CURRENT_STATE.md`
  - `docs/claude-context/PROGRESS_LOG.md`
- Piano 6 mesi con 5 fasi

#### Scoperte Chiave
1. Il codice e ben strutturato (non e scheletro)
2. La formula RLCF e implementata correttamente
3. Il workflow LangGraph funziona ma in "degraded mode" senza dati
4. ~42k LOC backend reale, non solo documentazione

#### Metriche Identificate per la Tesi
- **Accuracy**: vs gold standard 100 domande
- **Retrieval Quality**: Precision@K, MRR
- **RLCF-specific**: Authority correlation, disagreement preservation
- **Comparison**: vs ChatGPT, vs Lexis/Westlaw

#### Prossimi Passi
1. Setup ambiente (venv, dipendenze)
2. Configurare `.env` con API key
3. Prima query end-to-end (anche in degraded mode)
4. Iniziare seed data per Neo4j

#### Note
- L'utente preferisce italiano per comunicazioni
- Budget limitato -> usare Gemini Flash per test
- Documentare tutto per la tesi

#### Pulizia e Riorganizzazione (fine sessione)
- Riscritto CLAUDE.md v3.0 (da 866 LOC a ~200 LOC, senza ridondanze)
- Creata struttura `docs/claude-context/` per file di sessione
- Eliminato `SYSTEM_MAP.md` (56KB) - duplicato
- Spostato `ARCHITECTURE.md` in archive - info gia in docs/03-architecture/
- Stabilita metodologia di lavoro per prossimi 6 mesi

---

## Milestone Raggiunte

| Data | Milestone | Note |
|------|-----------|------|
| 2025-12-02 | Analisi iniziale completata | Mappa sistema creata |
| 2025-12-02 | Architettura v2 documentata | 5 documenti aggiornati |
| 2025-12-03 | Struttura codice v2 completata | Placeholder pronti |
| - | - | - |

---

## Statistiche Cumulative

| Metrica | Valore |
|---------|--------|
| Sessioni totali | 3 |
| Ore totali | ~7 |
| LOC scritte | ~800 (placeholder v2) |
| LOC documentazione | ~2000 (4 docs architettura v2) |
| Test aggiunti | 0 |
| Bug risolti | 0 |
