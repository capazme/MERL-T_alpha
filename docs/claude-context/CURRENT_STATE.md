# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 3 Dicembre 2025 |
| **Fase progetto** | Infrastruttura v2 completa - Database operativi |
| **Prossimo obiettivo** | Implementare FalkorDBClient e StorageService reali |
| **Blocchi attivi** | Nessuno - infrastruttura pronta |

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

- [x] Archiviato codice v1 in `backend/archive_v1/`
- [x] Creata struttura cartelle v2:
  - `backend/storage/` (FalkorDB, Bridge, Retriever)
  - `backend/orchestration/gating/` (Expert Gating Network)
  - `backend/orchestration/experts/expert_with_tools.py`
- [x] Implementati placeholder v2:
  - `FalkorDBClient` - client grafo (placeholder)
  - `BridgeTable` - mapping vector-graph (placeholder)
  - `GraphAwareRetriever` - hybrid retrieval (placeholder)
  - `ExpertGatingNetwork` - MoE weights (placeholder)
  - `ExpertWithTools` + 4 expert v2 (placeholder)
- [x] Aggiornati tutti `__init__.py` con export corretti
- [x] Verificato import funzionanti con Python 3.12
- [x] Fixato import rotti dopo archiviazione v1

---

## Prossimi Passi Immediati

### Priorita 1: Storage Layer v2 (Settimana 1-2)
- [ ] Setup FalkorDB container
- [ ] Migrazione schema grafo da Neo4j
- [ ] Creare Bridge Table in PostgreSQL
- [ ] Implementare BridgeTableBuilder per ingestion
- [ ] Test query Cypher su FalkorDB

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
source venv/bin/activate

# Database (v2 - con FalkorDB)
docker-compose up -d  # Aggiornare docker-compose per FalkorDB

# Backend
uvicorn backend.orchestration.api.main:app --reload --port 8000

# Test
pytest tests/ -v
```
