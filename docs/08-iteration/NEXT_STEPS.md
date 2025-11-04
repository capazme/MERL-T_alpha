# Prossimi Passi - Roadmap di Sviluppo

**Data Ultimo Aggiornamento:** 2025-01-05
**Commit:** `e2c5f44` - Task types alignment and dynamic configuration system
**Branch:** `rlcf-integration`

---

## 📊 Stato Attuale del Progetto

### ✅ Completato (Phase 1)

**Core RLCF Framework:**
- ✅ Authority scoring dinamico implementato
- ✅ Aggregazione uncertainty-preserving
- ✅ Sistema di task handlers polimorfico
- ✅ 11 task types ufficiali allineati
- ✅ RETRIEVAL_VALIDATION (nuovo task type per validare retrieval)
- ✅ Backend FastAPI con 50+ endpoints
- ✅ Frontend React 19 completo
- ✅ CLI tools (rlcf-cli, rlcf-admin)
- ✅ Test suite con 85%+ coverage
- ✅ **Sistema di configurazione dinamica con hot-reload** ⭐ NUOVO

**Lines of Code:** ~6,000 (backend) + ~3,000 (frontend) + ~2,750 (tests)

---

## 🎯 Prossimi Passi Immediati

### 1. Testing & Validazione (1-2 giorni)

**Priorità: ALTA** 🔴

#### A. Test del Sistema di Configurazione Dinamica

```bash
# 1. Avvia il server
cd backend
uvicorn rlcf_framework.main:app --reload

# 2. Esegui test automatico
./scripts/test_dynamic_config.sh

# 3. Test manuale hot-reload
# Terminal 1: Monitora i log
tail -f rlcf_detailed.log | grep ConfigManager

# Terminal 2: Modifica task_config.yaml
# Aggiungi/modifica un task type e salva
# Verifica il messaggio di hot-reload nel Terminal 1
```

**Output Atteso:**
- ✅ Tutti i test passano
- ✅ Hot-reload funziona
- ✅ Backup creati correttamente
- ✅ Validazione blocca configurazioni errate

#### B. Test del RETRIEVAL_VALIDATION Handler

```bash
# Crea una task di tipo RETRIEVAL_VALIDATION
curl -X POST http://localhost:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RETRIEVAL_VALIDATION",
    "input_data": {
      "query": "Quali sono i requisiti GDPR per il consenso?",
      "retrieved_items": [
        {"id": "norm_123", "title": "GDPR Art. 6"},
        {"id": "norm_456", "title": "GDPR Art. 7"}
      ],
      "retrieval_strategy": "semantic_search",
      "agent_type": "vector_db"
    }
  }'

# Genera response e raccogli feedback
# Verifica che aggregation funzioni
```

#### C. Regression Testing

```bash
# Esegui tutti i test esistenti
pytest tests/rlcf/ -v --cov=backend/rlcf_framework

# Verifica che non ci siano regressioni
# Coverage deve rimanere >= 85%
```

---

### 2. Documentazione Utente (1 giorno)

**Priorità: MEDIA** 🟡

#### A. Video/Tutorial

Creare un video screencast che mostra:
1. Come aggiungere un task type custom via API
2. Hot-reload in azione
3. Backup e restore
4. Creare una task del nuovo tipo

#### B. FAQ & Troubleshooting

Aggiungere a `docs/04-implementation/DYNAMIC_CONFIGURATION.md`:
- Esempi di task types per casi d'uso comuni (GDPR, contratti, etc.)
- Troubleshooting comune
- Best practices per produzione

---

### 3. Deployment & Configurazione Produzione (2-3 giorni)

**Priorità: MEDIA** 🟡

#### A. Docker Optimization

```dockerfile
# Aggiungere watchdog a Dockerfile
RUN pip install --no-cache-dir -r requirements.txt

# Verificare che hot-reload funzioni in container
```

#### B. Environment Variables

```bash
# .env.production
ADMIN_API_KEY=secure-random-key-here
DATABASE_URL=postgresql://...
OPENROUTER_API_KEY=sk-...

# Configurazione ConfigManager
CONFIG_BACKUP_RETENTION_DAYS=30
CONFIG_WATCH_ENABLED=true
```

#### C. Monitoring & Logging

- Setup Sentry/NewRelic per error tracking
- Log structured per ConfigManager events
- Alerting su config validation failures

---

## 🚀 Prossime Feature (Phase 2-3)

### Phase 2: Preprocessing Layer (4-6 settimane)

**Obiettivo:** Query Understanding + Knowledge Graph

#### Componenti da Implementare:

1. **Query Understanding Module**
   - NER con spaCy + italian-legal-bert
   - Intent classification
   - Entity linking to KG

2. **Knowledge Graph Setup**
   - Memgraph deployment
   - Schema design (Norme, Articoli, Concetti)
   - Data ingestion pipeline

3. **KG Enrichment Service**
   - Query → Concetti → Norme
   - Cypher query generator
   - Result ranking

**Deliverables:**
- [ ] `backend/preprocessing/query_understanding.py`
- [ ] `backend/preprocessing/kg_service.py`
- [ ] Memgraph schema in `infrastructure/memgraph/`
- [ ] Test suite per preprocessing

**Stima:** 4-6 settimane (1 developer)

---

### Phase 3: Orchestration Layer (6-8 settimane)

**Obiettivo:** LLM Router + Retrieval Agents

#### Componenti da Implementare:

1. **LLM Router**
   - 100% LLM-based decision engine
   - Decides: which experts, which retrieval agents, how many iterations
   - LangGraph state machine

2. **Retrieval Agents**
   - **KG Agent:** Queries Memgraph
   - **API Agent:** EUR-Lex, Normattiva APIs
   - **VectorDB Agent:** Qdrant for semantic search

3. **RLCF Integration for Agents**
   - Use RETRIEVAL_VALIDATION tasks
   - Feedback loops to improve retrieval strategies
   - A/B testing for different strategies

**Deliverables:**
- [ ] `backend/orchestration/llm_router.py`
- [ ] `backend/orchestration/agents/` (kg, api, vector)
- [ ] LangGraph state machine definition
- [ ] Retrieval strategy configs

**Stima:** 6-8 settimane (2 developers)

---

### Phase 4: Reasoning Layer (8-10 settimane)

**Obiettivo:** 4 Expert Types + Synthesizer

#### Componenti da Implementare:

1. **4 Expert Types**
   - Literal Interpreter (positivism)
   - Systemic-Teleological (finalism)
   - Principles Balancer (constitutionalism)
   - Precedent Analyst (empiricism)

2. **Synthesizer**
   - Convergent mode (consensus)
   - Divergent mode (preserve disagreement)
   - Uncertainty quantification

3. **RLCF Integration for Experts**
   - Use QA, STATUTORY_RULE_QA, DOCTRINE_APPLICATION tasks
   - Expert-specific metadata in feedback
   - Authority scoring per expert type

**Deliverables:**
- [ ] `backend/reasoning/experts/` (4 expert modules)
- [ ] `backend/reasoning/synthesizer.py`
- [ ] Prompt templates per expert
- [ ] RLCF feedback integration

**Stima:** 8-10 settimane (2-3 developers)

---

## 🔧 Miglioramenti Tecnici Consigliati

### Immediate (1-2 settimane)

1. **ConfigManager Enhancements**
   - [ ] Add webhook support for config changes (notify external systems)
   - [ ] Add diff viewer for comparing configs
   - [ ] Add validation dry-run endpoint

2. **RETRIEVAL_VALIDATION Improvements**
   - [ ] Add relevance scoring (0.0-1.0)
   - [ ] Add explanation field (why relevant/irrelevant)
   - [ ] Add missing_items ranking

3. **Monitoring Dashboard**
   - [ ] Grafana dashboard for config changes
   - [ ] Backup retention visualization
   - [ ] Hot-reload success/failure metrics

### Short-Term (1 mese)

1. **UI Admin Panel**
   - Visual task type editor
   - Schema builder (drag & drop)
   - Backup browser with diff
   - Config validation preview

2. **Multi-Environment Support**
   - Development/staging/production configs
   - Environment promotion workflow
   - Config sync between environments

3. **Schema Migration System**
   - Automatic migration of existing tasks to new schemas
   - Backward compatibility layer
   - Rollback support

---

## 📈 Metriche di Successo

### Phase 1 (Current)
- ✅ 11 task types implementati
- ✅ 85%+ test coverage
- ✅ Hot-reload funzionante
- ✅ Zero downtime config changes

### Phase 2 (Target)
- [ ] Query Understanding accuracy > 90%
- [ ] KG with 10,000+ legal norms
- [ ] Entity linking precision > 85%

### Phase 3 (Target)
- [ ] LLM Router decision latency < 500ms
- [ ] Retrieval agent response time < 2s
- [ ] RETRIEVAL_VALIDATION feedback rate > 60%

### Phase 4 (Target)
- [ ] Expert reasoning quality > 80% (RLCF scored)
- [ ] Synthesis latency < 3s
- [ ] User satisfaction > 4/5

---

## 💡 Raccomandazioni Architetturali

### 1. Event-Driven Architecture

Considera di usare **events** per comunicazione tra layer:

```python
# Event bus per layer communication
from dataclasses import dataclass

@dataclass
class QueryProcessedEvent:
    query_id: str
    entities: List[Entity]
    intent: str

@dataclass
class RetrievalCompletedEvent:
    query_id: str
    results: List[RetrievalResult]
    agent_type: str

# Pub/sub per RLCF feedback loops
```

### 2. Caching Strategy

Implementare caching multi-livello:

```python
# L1: In-memory (ConfigManager già lo fa)
# L2: Redis per query/retrieval results
# L3: CDN per static assets

# TTL strategy per diverse cache keys
```

### 3. Observability

Setup completo di observability:

```python
# Logs: Structured logging (JSON)
# Metrics: Prometheus + Grafana
# Traces: OpenTelemetry
# Profiles: py-spy per profiling
```

---

## 🎓 Formazione Team

### Per Phase 2 Setup

**Skills needed:**
- Graph databases (Cypher, Memgraph)
- NLP in italiano (spaCy, transformers)
- Knowledge representation

**Resources:**
- Memgraph docs: https://memgraph.com/docs
- spaCy Italian: https://spacy.io/models/it
- italian-legal-bert: Hugging Face

### Per Phase 3 Setup

**Skills needed:**
- LangGraph / LangChain
- Async programming
- API integration

**Resources:**
- LangGraph tutorial: https://langchain-ai.github.io/langgraph/
- FastAPI advanced: https://fastapi.tiangolo.com/advanced/

---

## 📋 Checklist Immediata

### Prima di Procedere a Phase 2

- [ ] Testare sistema configurazione dinamica completamente
- [ ] Verificare hot-reload in ambiente Docker
- [ ] Documentare tutti gli endpoint API (Swagger)
- [ ] Creare video tutorial per ConfigManager
- [ ] Setup monitoring/alerting base
- [ ] Backup strategy per configurazioni in produzione
- [ ] Code review del sistema RETRIEVAL_VALIDATION
- [ ] Performance testing (load test con 100+ concurrent requests)
- [ ] Security audit (API key management, validation)

### Decisioni da Prendere

1. **Database per produzione:**
   - [ ] PostgreSQL on-premise vs managed (RDS, Supabase)
   - [ ] Memgraph self-hosted vs managed

2. **Deployment strategy:**
   - [ ] Docker Compose vs Kubernetes
   - [ ] CI/CD pipeline (GitHub Actions, GitLab CI)

3. **Team structure:**
   - [ ] Quanti developer full-time?
   - [ ] Legal expert involvement frequency?
   - [ ] Budget per infrastruttura cloud?

---

## 🔗 Link Utili

**Documentazione Tecnica:**
- [DYNAMIC_CONFIGURATION.md](../04-implementation/DYNAMIC_CONFIGURATION.md)
- [IMPLEMENTATION_ROADMAP.md](../../IMPLEMENTATION_ROADMAP.md)
- [TECHNOLOGY_RECOMMENDATIONS.md](../../TECHNOLOGY_RECOMMENDATIONS.md)

**Codice:**
- ConfigManager: `backend/rlcf_framework/config_manager.py`
- Config Router: `backend/rlcf_framework/routers/config_router.py`
- RETRIEVAL_VALIDATION: `backend/rlcf_framework/task_handlers/retrieval_validation_handler.py`

**Testing:**
- Test script: `scripts/test_dynamic_config.sh`
- Quick start: [DYNAMIC_CONFIG_QUICKSTART.md](DYNAMIC_CONFIG_QUICKSTART.md)

---

## 📞 Support & Contributi

Per domande o contributi:
1. Apri un issue su GitHub
2. Consulta la documentazione in `docs/`
3. Esegui i test prima di ogni PR
4. Segui le convenzioni di commit (feat:, fix:, docs:)

---

**Prossima Milestone:** Phase 2 - Preprocessing Layer
**Target Date:** Marzo 2025 (stimato)
**Status:** ✅ Phase 1 Complete, Ready to Start Phase 2

---

*Documento creato automaticamente durante la sessione di sviluppo*
*Ultimo aggiornamento: 2025-01-05*
