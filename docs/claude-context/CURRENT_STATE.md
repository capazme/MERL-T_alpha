# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 3 Dicembre 2025 |
| **Fase progetto** | Primo batch ingestion completato - Graph operativo con dati reali |
| **Prossimo obiettivo** | Bridge Table + GraphAwareRetriever |
| **Blocchi attivi** | Nessuno |

---

## Architettura v2 - Cambiamenti Principali

### Da v1 a v2:
| Aspetto | v1 | v2 |
|---------|----|----|
| Expert | Passivi | Autonomi con tools |
| Graph DB | Neo4j | FalkorDB (496x piu veloce) |
| Vector-Graph | Separati | Bridge Table integrata |
| RLCF | Scalare | Multilivello |
| Pesi | Statici | Apprendibili (theta_*) |

### Documenti v2 Creati:
- `docs/03-architecture/02-orchestration-layer.md` (v2)
- `docs/03-architecture/03-reasoning-layer.md` (v2)
- `docs/03-architecture/04-storage-layer.md` (v2)
- `docs/03-architecture/05-learning-layer.md` (v2)
- `docs/SYSTEM_ARCHITECTURE.md` (v2)

### Archivio v1:
- `docs/03-architecture/archive/v1-*.md`

---

## Cosa Abbiamo Fatto (Ultima Sessione - 3 Dic 2025)

- [x] **Archiviato codice v1** in `backend/archive_v1/`
- [x] **Struttura modulare v2**:
  - `backend/interfaces/` - IStorageService, IExpert, IRLCFService
  - `backend/services/` - ServiceRegistry (monolith/distributed)
  - `backend/storage/` - FalkorDB, Bridge, Retriever
  - `backend/orchestration/gating/` - ExpertGatingNetwork
  - `backend/external_sources/visualex/` - Scrapers + tools integrati
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
  - Node types: Norma, ConceptoGiuridico, Dottrina, AttoGiudiziario
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
  - 4 nodi ConceptoGiuridico
  - 4 relazioni 'contiene', 4 relazioni 'disciplina'
  - Test suite completo (4/4 passed)
  - Script standalone: `scripts/ingest_art_1453_1456.py`
  - Performance: query in 0.3-0.8ms

---

## Prossimi Passi Immediati

### Priorita 1: Storage Layer v2 (Settimana 1-2)
- [x] Setup FalkorDB container (porta 6380)
- [x] Test query Cypher su FalkorDB
- [x] VisualexAPI ingestion pipeline (conforme allo schema)
- [x] Implementare FalkorDBClient reale con falkordb-py
- [x] Integrare VisualexAPI scrapers e tools
- [x] **Primo batch ingestion** - Art. 1453-1456 Codice Civile ✅
- [ ] Creare Bridge Table in PostgreSQL
- [ ] Implementare BridgeTableBuilder per ingestion

### Priorita 2: Expert con Tools (Settimana 3-4)
- [ ] Implementare classe `ExpertWithTools`
- [ ] Definire tools per Literal (get_exact_text, get_definitions)
- [ ] Definire tools per Systemic (get_legislative_history)
- [ ] Definire tools per Principles (get_constitutional_basis)
- [ ] Definire tools per Precedent (search_cases, get_citation_chain)

### Priorita 3: Graph-Aware Retriever (Settimana 5-6)
- [ ] Implementare `GraphAwareRetriever`
- [ ] Integrazione con Bridge Table
- [ ] Alpha parameter learning

### Priorita 4: RLCF Multilivello (Settimana 7-8)
- [ ] Schema DB per authority multilivello
- [ ] `MultilevelAuthority` class
- [ ] `MultilevelFeedback` schema
- [ ] Policy gradient training loop

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
2. `docs/SYSTEM_ARCHITECTURE.md` - Mappa tecnica v2
3. `docs/03-architecture/02-orchestration-layer.md` - Expert autonomi, gating
4. `docs/03-architecture/03-reasoning-layer.md` - Expert con tools
5. `docs/03-architecture/04-storage-layer.md` - FalkorDB, Bridge Table
6. `docs/03-architecture/05-learning-layer.md` - RLCF multilivello

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

# Backend
uvicorn backend.orchestration.api.main:app --reload --port 8000

# Test
pytest tests/ -v

# Test FalkorDB
.venv/bin/python -c "from backend.storage.falkordb import FalkorDBClient; import asyncio; asyncio.run(FalkorDBClient().health_check())"
```
