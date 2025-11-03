# MERL-T: Roadmap di Implementazione dalla Documentazione alla Produzione

**Versione**: 1.0
**Data**: 3 Novembre 2025
**Autore**: ALIS - Artificial Legal Intelligence Society
**Stato**: Guida Operativa

---

## Indice

1. [Introduzione](#1-introduzione)
2. [Principi Guida per Progetti Complessi](#2-principi-guida-per-progetti-complessi)
3. [Fase 0: Setup Iniziale e Governance](#fase-0-setup-iniziale-e-governance-settimane-1-2)
4. [Fase 1: MVP Foundation (Core RLCF)](#fase-1-mvp-foundation-core-rlcf-settimane-3-8)
5. [Fase 2: Preprocessing Layer](#fase-2-preprocessing-layer-settimane-9-14)
6. [Fase 3: Orchestration Layer](#fase-3-orchestration-layer-settimane-15-22)
7. [Fase 4: Reasoning Layer](#fase-4-reasoning-layer-settimane-23-30)
8. [Fase 5: Integration & Testing](#fase-5-integration--testing-settimane-31-36)
9. [Fase 6: Production Readiness](#fase-6-production-readiness-settimane-37-42)
10. [Fase 7: Launch & Iteration](#fase-7-launch--iteration-settimane-43)
11. [Gestione dei Rischi](#gestione-dei-rischi)
12. [Team e Competenze Richieste](#team-e-competenze-richieste)
13. [Budget e Risorse](#budget-e-risorse)
14. [Metriche di Successo](#metriche-di-successo)

---

## 1. Introduzione

### 1.1 Situazione Attuale

✅ **Completato**:
- Documentazione tecnica completa e rigorosa
- Design architetturale dei 5 layer
- Framework teorico RLCF con fondamenti matematici
- Specifiche API e schemi database
- Requisiti di compliance AI Act

❌ **Da Realizzare**:
- Implementazione del codice
- Infrastruttura operativa
- Testing sistematico
- Deployment in produzione
- Team operativo

### 1.2 Obiettivo

Trasformare la documentazione in un **sistema in produzione** seguendo un approccio:
- **Incrementale**: Funzionalità rilasciate progressivamente
- **Validato**: Testing continuo con feedback reali
- **Sostenibile**: Architettura scalabile e manutenibile
- **Conforme**: AI Act compliance fin dall'inizio

### 1.3 Timeline Complessiva

**Durata totale**: 10-12 mesi (42-52 settimane)
- Fasi 0-1 (MVP RLCF): 8 settimane
- Fasi 2-4 (Core System): 22 settimane
- Fasi 5-6 (Production): 12 settimane
- Fase 7+ (Iteration): Continua

---

## 2. Principi Guida per Progetti Complessi

### 2.1 Build-Measure-Learn

```
┌─────────────┐
│    BUILD    │  Implementa il minimo necessario
│   (Sprint)  │  per testare un'ipotesi
└──────┬──────┘
       ↓
┌─────────────┐
│   MEASURE   │  Raccogli metriche reali
│  (Metrics)  │  da utenti o test
└──────┬──────┘
       ↓
┌─────────────┐
│    LEARN    │  Analizza risultati,
│  (Iterate)  │  decidi prossimi passi
└──────┬──────┘
       ↓
    (repeat)
```

**Applicazione a MERL-T**:
- Non costruire tutto prima di testare
- Ogni fase termina con un deliverable funzionante
- Validazione con esperti legali fin da subito

### 2.2 Vertical Slice Architecture

Invece di costruire layer per layer (tutti i database, poi tutti i servizi, etc.), costruisci **fette verticali end-to-end**:

```
❌ SBAGLIATO (Horizontal):
Mese 1-2: Tutti i database
Mese 3-4: Tutti i backend services
Mese 5-6: Tutto il frontend
→ Nessuna funzionalità completa fino al mese 6

✅ CORRETTO (Vertical Slice):
Mese 1-2: RLCF task ranking + feedback (end-to-end)
Mese 3-4: Simple query → Neo4j → Response (end-to-end)
Mese 5-6: LLM Router + 1 expert (end-to-end)
→ Deliverable funzionante ogni 2 mesi
```

### 2.3 Strangler Fig Pattern

Per integrare componenti complessi senza paralizzare il progetto:

1. **Nuovo sistema** cresce intorno al vecchio
2. **Redirect graduale** del traffico al nuovo sistema
3. **Vecchio sistema** viene "strangolato" progressivamente

**Esempio per MERL-T**:
- Fase 1: Sistema RLCF standalone (senza LLM Router)
- Fase 2: Aggiungi Router semplice (regole hardcoded)
- Fase 3: Sostituisci con LLM Router (100% LLM-based)

### 2.4 Testing Pyramid

```
              /\
             /  \  E2E Tests (5%)
            /____\
           /      \
          / Integration \ (15%)
         /    Tests      \
        /__________________\
       /                    \
      /   Unit Tests (80%)   \
     /________________________\
```

**Priorità**:
- **80% Unit tests**: Ogni funzione matematica RLCF testata
- **15% Integration**: API endpoints, database queries
- **5% E2E**: User journey completi (costosi, fragili)

### 2.5 Infrastructure as Code (IaC)

Tutto in versioning:
- `docker-compose.yml` per development
- `kubernetes/` manifests per production
- `terraform/` per cloud resources
- `scripts/` per automazione

**Beneficio**: Riproducibilità totale dell'ambiente.

---

## Fase 0: Setup Iniziale e Governance (Settimane 1-2)

### Obiettivi

✅ Repository strutturato e operativo
✅ CI/CD pipeline funzionante
✅ Team allineato su workflow
✅ Infrastruttura di sviluppo locale

### Deliverables

#### 0.1 Repository Setup

**Struttura monorepo**:
```
MERL-T/
├── docs/                    # Documentazione esistente
├── backend/
│   ├── rlcf_framework/     # Core RLCF (Fase 1)
│   ├── preprocessing/      # Query understanding (Fase 2)
│   ├── orchestration/      # Router + Agents (Fase 3)
│   ├── reasoning/          # Experts + Synthesizer (Fase 4)
│   └── shared/             # Utilities comuni
├── frontend/
│   ├── web/                # React app principale
│   └── components/         # Shared components
├── infrastructure/
│   ├── docker/             # Dockerfiles
│   ├── kubernetes/         # K8s manifests
│   └── terraform/          # Cloud infra (opzionale Fase 6)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                # Automation
├── .github/
│   └── workflows/          # GitHub Actions CI/CD
├── docker-compose.yml      # Local development
├── requirements.txt        # Python deps (root)
└── package.json            # Node deps (root)
```

**Tasks**:
1. Crea struttura directory (30 min)
2. Inizializza Git submodules o monorepo tool (Nx, Turborepo) (2h)
3. Setup `.gitignore`, `.dockerignore` (30 min)
4. README.md root con quick start (1h)

#### 0.2 Development Environment

**Docker Compose per sviluppo locale**:
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rlcf_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5.13-community
    environment:
      NEO4J_AUTH: neo4j/devpassword
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  neo4j_data:
  redis_data:
```

**Tasks**:
1. Scrivi `docker-compose.dev.yml` (1h)
2. Testa avvio database locali: `docker-compose up -d` (30 min)
3. Documenta in `docs/guides/LOCAL_SETUP.md` (1h)

#### 0.3 CI/CD Pipeline (GitHub Actions)

**File**: `.github/workflows/ci.yml`
```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run linting
        run: ruff check backend/
      - name: Run type checking
        run: mypy backend/
      - name: Run unit tests
        run: pytest tests/unit/ --cov=backend/
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run linting
        run: cd frontend && npm run lint
      - name: Run tests
        run: cd frontend && npm test
```

**Tasks**:
1. Setup GitHub Actions workflow (2h)
2. Configura Codecov per code coverage (30 min)
3. Badge in README per build status (15 min)

#### 0.4 Development Standards

**File**: `docs/guides/CONTRIBUTING.md`

Documenta:
- **Branching strategy**: GitFlow (main, develop, feature/*, hotfix/*)
- **Commit conventions**: Conventional Commits (`feat:`, `fix:`, `docs:`)
- **Code review process**: PR template, 1 approval richiesta
- **Testing requirements**: Coverage > 80% per PR merge

**Tasks**:
1. Scrivi `CONTRIBUTING.md` (2h)
2. Setup PR template `.github/pull_request_template.md` (30 min)
3. Branch protection rules su GitHub (15 min)

### Checklist Fase 0

- [ ] Repository monorepo strutturato
- [ ] Docker Compose locale funzionante (PostgreSQL, Neo4j, Redis)
- [ ] CI/CD pipeline attiva su GitHub Actions
- [ ] Documentazione `CONTRIBUTING.md` e `LOCAL_SETUP.md`
- [ ] Team training su workflow (1 sessione 2h)

**Durata**: 2 settimane con 1 developer full-time

---

## Fase 1: MVP Foundation (Core RLCF) (Settimane 3-8)

### Obiettivo

Implementare il **cuore del sistema RLCF** in versione funzionante ma semplificata:
- Task submission e feedback collection
- Dynamic authority scoring
- Aggregazione feedback
- API REST + database

**Perché iniziare da qui**:
- RLCF è l'innovazione chiave del progetto
- Permette validazione con esperti legali da subito
- Non dipende da LLM/NLP complessi (può usare task manuali)

### Deliverables

#### 1.1 Database Schema (RLCF Core)

**File**: `backend/rlcf_framework/models.py`

Implementa tabelle:
- `users` (id, username, authority_score, credentials_json)
- `tasks` (id, type, input_data, status, created_at)
- `feedback` (id, task_id, user_id, rating, corrections_json, timestamp)
- `aggregated_results` (task_id, final_result_json, confidence, consensus_score)

**Tech stack**:
- SQLAlchemy 2.0 (async)
- Alembic per migrations
- PostgreSQL

**Tasks**:
1. Define SQLAlchemy models (4h)
2. Setup Alembic migrations (2h)
3. Write database initialization script (2h)
4. Unit tests per models (4h)

#### 1.2 Core RLCF Algorithms

**File**: `backend/rlcf_framework/authority_module.py`

Implementa:
```python
def calculate_authority_score(
    user_id: int,
    baseline_credentials: float,
    track_record: float,
    recent_performance: float,
    weights: AuthorityWeights
) -> float:
    """
    A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)

    Returns authority score in [0, 2]
    """
    return (
        weights.alpha * baseline_credentials +
        weights.beta * track_record +
        weights.gamma * recent_performance
    )
```

**File**: `backend/rlcf_framework/aggregation_engine.py`

Implementa aggregazione weighted voting per task tipo `ranking`, `classification`, etc.

**Tasks**:
1. Implementa `authority_module.py` (6h)
2. Implementa `aggregation_engine.py` (8h)
3. Unit tests matematici (confronto con formulas in docs) (6h)
4. Property-based testing con Hypothesis (4h)

#### 1.3 REST API (FastAPI)

**File**: `backend/rlcf_framework/main.py`

Endpoints:
- `POST /users/` - Crea utente
- `POST /users/{id}/credentials/` - Aggiungi credenziali
- `POST /tasks/` - Crea task
- `GET /tasks/{id}` - Dettagli task
- `POST /tasks/{id}/feedback/` - Invia feedback
- `GET /tasks/{id}/result/` - Risultato aggregato

**Tasks**:
1. Setup FastAPI app con dependency injection (4h)
2. Implementa endpoints CRUD per users, tasks, feedback (8h)
3. Implementa aggregation endpoint (4h)
4. OpenAPI docs validation (2h)
5. Integration tests con TestClient (6h)

#### 1.4 Configuration Management

**File**: `backend/rlcf_framework/config.py`

Carica configurazione da YAML (come specificato in docs):
```python
from pydantic import BaseModel
import yaml

class AuthorityWeights(BaseModel):
    alpha: float = 0.3  # baseline_credentials
    beta: float = 0.5   # track_record
    gamma: float = 0.2  # recent_performance

class ModelConfig(BaseModel):
    authority_weights: AuthorityWeights
    aggregation_params: dict
    # ... altri parametri

def load_config(path: str = "config/model_config.yaml") -> ModelConfig:
    with open(path) as f:
        data = yaml.safe_load(f)
    return ModelConfig(**data)
```

**Tasks**:
1. Implementa config loader con Pydantic (3h)
2. Crea `config/model_config.yaml` di default (2h)
3. Valida contro docs specification (1h)
4. Tests per config validation (2h)

#### 1.5 CLI Admin Tool

**File**: `backend/rlcf_framework/cli.py`

Tool per operazioni admin:
```bash
# Crea utenti bulk
python -m rlcf_framework.cli users create-bulk --file users.json

# Esegui aggregazione manuale
python -m rlcf_framework.cli tasks aggregate --task-id 123

# Export risultati
python -m rlcf_framework.cli export --format csv --output results.csv
```

**Tech**: Click o Typer

**Tasks**:
1. Setup CLI con Typer (2h)
2. Comandi per user management (3h)
3. Comandi per task lifecycle (3h)
4. Tests per CLI (2h)

### Testing & Validation Fase 1

**Unit Tests**:
- [ ] Authority scoring: confronta output con calcoli manuali (formule docs)
- [ ] Aggregation: testa casi edge (tutti d'accordo, tutti in disaccordo, missing votes)
- [ ] Database models: CRUD operations
- [ ] Config loading: validazione YAML

**Integration Tests**:
- [ ] End-to-end: create user → create task → submit feedback → get aggregated result
- [ ] API: tutti gli endpoints con status 200/400/404 appropriati

**Acceptance Criteria**:
- [ ] API risponde a tutte le richieste in < 200ms (senza LLM)
- [ ] Authority scores corretti entro 0.01 rispetto a calcoli manuali
- [ ] Code coverage > 85%
- [ ] Documentazione API completa (OpenAPI)

### Milestone 1: RLCF MVP Demo

**Deliverable**: Demo video 5 minuti che mostra:
1. Creazione 3 utenti con credenziali diverse
2. Creazione task di ranking
3. Submission feedback da 3 utenti
4. Visualizzazione aggregated result con authority scores
5. Curl commands documentati in `examples/rlcf_demo.sh`

**Presentazione**: A esperti legali ALIS per validazione concettuale

**Durata Fase 1**: 6 settimane con 2 developers (1 backend + 1 full-stack)

---

## Fase 2: Preprocessing Layer (Settimane 9-14)

### Obiettivo

Costruire la pipeline di **comprensione della query**:
- Query parsing e cleaning
- Named Entity Recognition (NER) per entità legali
- Intent classification
- Knowledge Graph enrichment (primo accesso a Neo4j)

**Perché ora**:
- Fondamentale per tutte le fasi successive
- Permette di testare Neo4j integration
- Può essere validato manualmente (senza LLM Router ancora)

### Deliverables

#### 2.1 Knowledge Graph Population

**Prima di processare query, serve un KG popolato**:

**Tasks**:
1. **Schema Neo4j** (2 settimane, 1 data engineer):
   - Implementa node types: `Norma`, `ConcettoGiuridico`, `Sentenza`
   - Implementa relationships: `REGOLA`, `GERARCHIA_KELSENIANA`, `RELAZIONE_CONCETTUALE`
   - Indexes su `norm_id`, `concept_id`, `title`
   - Script Cypher in `backend/preprocessing/neo4j/schema.cypher`

2. **Data ingestion pipeline** (2 settimane, 1 developer):
   - Parser per Akoma Ntoso XML (norme italiane)
   - ETL per importare Codice Civile, Costituzione
   - Script: `python -m preprocessing.ingest --source codice_civile.xml`
   - Target: ~10,000 norme nel grafo

3. **Validation**:
   - Query test: "Trova tutti gli articoli del Codice Civile"
   - Traversal test: "Gerarchia normativa da Art. 2 c.c. alla Costituzione"

**Risorse esterne**:
- Dati normativi: [Normattiva.it](https://www.normattiva.it/) (XML Akoma Ntoso)
- Ontologia: Manuale se necessario (o ML-assisted tagging)

#### 2.2 NER Module (Legal Entities)

**File**: `backend/preprocessing/ner_module.py`

Entità da riconoscere:
- `NORM` (es. "art. 2 c.c.", "Costituzione art. 24")
- `LEGAL_CONCEPT` (es. "capacità di agire", "inadempimento")
- `DATE` (es. "2010", "gennaio 2020")
- `PERSON` (es. "minorenne", "creditore")

**Tech stack options**:
1. **spaCy custom NER** (consigliato per iniziare):
   - Base model: `it_core_news_lg`
   - Fine-tune su dataset legale annotato (500-1000 esempi)
   - Tools: Prodigy per annotation

2. **Transformer-based** (se accuracy insufficiente):
   - Model: `dbmdz/bert-base-italian-xxl-cased`
   - Fine-tune con HuggingFace Trainer

**Tasks**:
1. Crea dataset annotato (200 query legali annotate) (1 settimana, 1 ML engineer + 1 legal expert)
2. Fine-tune spaCy NER (1 settimana)
3. Evaluation: precision/recall > 0.85 su test set
4. API endpoint: `POST /preprocess/ner` (2 giorni)

#### 2.3 Intent Classification

**Tipi di intent** (da docs):
- `validità_atto` - "È valido un contratto firmato da minorenne?"
- `interpretazione_norma` - "Cosa significa l'art. 2 c.c.?"
- `conseguenze_giuridiche` - "Cosa succede se non pago un debito?"
- `bilanciamento_diritti` - "Prevale libertà espressione o privacy?"

**Approccio**:
1. **Phase 1 (MVP)**: Rule-based classifier
   - Keywords matching: "è valid*" → `validità_atto`
   - Regex patterns
   - Confidence score basato su match quality

2. **Phase 2 (production)**: Fine-tuned classifier
   - Dataset: 500 query annotate per intent
   - Model: DistilBERT Italian
   - Multi-label (una query può avere 2+ intent)

**Tasks**:
1. Implementa rule-based classifier (1 settimana)
2. Valida con esperti su 100 query reali (3 giorni)
3. Se accuracy < 0.80, prepara per ML approach in Fase 3

#### 2.4 KG Enrichment Service

**File**: `backend/preprocessing/kg_enrichment.py`

Dato NER output (entità `NORM`, `LEGAL_CONCEPT`), arricchisci con KG:

```python
async def enrich_concepts(concepts: List[str]) -> EnrichedContext:
    """
    Input: ["capacità di agire", "validità contratto"]

    Process:
    1. Query Neo4j per ogni concetto
    2. MATCH (c:ConcettoGiuridico {label: "capacità di agire"})
       -[:REGOLA]-> (n:Norma)
    3. Return mapped norms, relationships

    Output: {
      "concepts_enriched": [
        {
          "concept_id": "capacità_agire",
          "mapped_norms": ["art_2_cc", "art_1425_cc"],
          "related_concepts": ["maggiore_età", "incapacità_naturale"]
        }
      ]
    }
    """
```

**Tasks**:
1. Implementa Cypher queries per enrichment (1 settimana)
2. Cache con Redis (TTL 1h) (2 giorni)
3. Endpoint: `POST /preprocess/enrich` (1 giorno)
4. Tests: mock Neo4j con neo4j-python-driver test fixtures

#### 2.5 End-to-End Preprocessing Pipeline

**File**: `backend/preprocessing/pipeline.py`

Orchestrate tutti i moduli:

```python
async def preprocess_query(query: str) -> QueryContext:
    """
    Input: "È valido un contratto firmato da un minorenne nel 2010?"

    Steps:
    1. Query cleaning
    2. NER extraction
    3. Intent classification
    4. KG enrichment

    Output: QueryContext object (schema da docs)
    """
    # 1. Clean
    cleaned = clean_query(query)

    # 2. NER
    entities = await ner_module.extract_entities(cleaned)

    # 3. Intent
    intent = intent_classifier.classify(cleaned, entities)

    # 4. KG enrichment
    enriched = await kg_enrichment.enrich_concepts(
        [e for e in entities if e.type == "LEGAL_CONCEPT"]
    )

    return QueryContext(
        original_query=query,
        entities=entities,
        intent=intent,
        enriched_context=enriched
    )
```

**Tasks**:
1. Implementa pipeline orchestration (1 settimana)
2. FastAPI endpoint: `POST /query/preprocess` (2 giorni)
3. Integration tests: 50 query end-to-end (3 giorni)

### Testing & Validation Fase 2

**Dataset Test**:
Crea dataset di 100 query legali italiane reali con ground truth:
- NER entities annotate
- Intent labels
- Expected enriched concepts

**Metrics**:
- NER: F1 score > 0.85
- Intent: Accuracy > 0.80
- KG enrichment: Coverage > 0.70 (% query con almeno 1 norm mappato)
- Latency: < 500ms end-to-end (senza LLM)

### Milestone 2: Query Understanding Demo

**Deliverable**:
- Notebook Jupyter con 20 query processate
- Visualizzazione entities, intent, enriched concepts
- Grafici Neo4j per relationship traversal
- Presentazione a legal experts per validation

**Durata Fase 2**: 6 settimane con 3 developers (1 ML/NLP + 1 backend + 1 data engineer)

---

## Fase 3: Orchestration Layer (Settimane 15-22)

### Obiettivo

Implementare il **cervello decisionale** del sistema:
- LLM Router (100% LLM-based)
- 3 Retrieval Agents (KG, API, VectorDB)
- Parallel execution framework
- ExecutionPlan generation

**Complessità**: Questa è la fase più critica architetturalmente.

### Deliverables

#### 3.1 VectorDB Setup & Population

**Prima di implementare VectorDB Agent, serve un vector store popolato**:

**Tech choice**: Weaviate (supporto hybrid search nativo)

**Tasks** (2 settimane, 1 data engineer):
1. Setup Weaviate con Docker
2. Define schema per legal corpus:
   ```python
   class LegalChunk:
       chunk_id: str
       text: str  # Chunk di norm/jurisprudence
       vector: List[float]  # Embedding (3072 dims)
       metadata: {
           document_type: str  # "norm" | "jurisprudence" | "doctrine"
           norm_id: str
           source: str
           temporal_metadata: {...}
           classification: {...}
       }
   ```
3. Chunking strategy per norme (500 tokens/chunk con overlap 50 tokens)
4. Embedding con OpenAI `text-embedding-3-large`
5. Ingest 10,000 chunks (Codice Civile + sentenze rilevanti)
6. Validation: test query "inadempimento contratto" → retrieve top-10

**Cost estimate**: ~$50 per 10M tokens embedding (one-time)

#### 3.2 VectorDB Agent

**File**: `backend/orchestration/agents/vectordb_agent.py`

Implementa retrieval patterns P1-P4 (P5-P6 in fase successiva):
- P1: Semantic search (HNSW)
- P2: Hybrid search (vector + BM25)
- P3: Filtered retrieval (metadata filters)
- P4: Reranked retrieval (cross-encoder)

**Tasks** (2 settimane, 1 ML engineer):
1. Implementa pattern P1 (semantic) (2 giorni)
2. Implementa pattern P2 (hybrid con alpha parameter) (3 giorni)
3. Implementa pattern P3 (complex filters) (2 giorni)
4. Implementa pattern P4 (cross-encoder reranking) (4 giorni)
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Fine-tune (opzionale): 500 triplets (query, relevant_chunk, score)
5. API endpoint: `POST /agents/vectordb/execute`
6. Tests: precision@10, recall@10 su test set 100 query

#### 3.3 KG Agent

**File**: `backend/orchestration/agents/kg_agent.py`

Implementa graph queries:
- `expand_related_concepts`: Multi-hop traversal
- `hierarchical_traversal`: Gerarchia normativa
- `jurisprudence_lookup`: Sentenze linkate a norme
- `temporal_version_query`: Multivigenza

**Tasks** (1.5 settimane, 1 backend developer):
1. Implementa 4 task types con Cypher queries (1 settimana)
2. Redis caching (TTL 1h) (2 giorni)
3. API endpoint: `POST /agents/kg/execute`
4. Tests: mock Neo4j responses, validate Cypher syntax

#### 3.4 API Agent

**File**: `backend/orchestration/agents/api_agent.py`

Client per Akoma Ntoso API:
- Fetch full norm text
- Version-aware retrieval (multivigenza)
- Caching (Redis, TTL 24h per current version)

**Tasks** (1 settimana, 1 backend developer):
1. HTTP client con httpx (async, retry logic) (2 giorni)
2. Parse Akoma Ntoso XML/JSON response (2 giorni)
3. Caching layer (1 giorno)
4. API endpoint: `POST /agents/api/execute`
5. Tests: mock HTTP responses (VCR.py per record/replay)

#### 3.5 LLM Router (MVP con GPT-4o)

**File**: `backend/orchestration/router.py`

**Approccio incrementale**:

**Phase 1 - Rule-based Router** (settimane 15-16):
- Hardcoded rules: se intent = `validità_atto` → API Agent + Literal Interpreter
- No LLM, solo pattern matching
- Valida architettura async e agent dispatch

**Phase 2 - LLM Router** (settimane 17-20):
- System prompt engineering (iterativo)
- Structured output con JSON Schema (GPT-4o)
- ExecutionPlan generation
- Logging per RLCF feedback

**Tasks Phase 2**:
1. Design system prompt (vedi docs/03-architecture/02-orchestration-layer.md §3.2) (1 settimana iterativa)
2. Implementa LLM call con OpenAI SDK (2 giorni)
3. JSON Schema validation per ExecutionPlan (1 giorno)
4. Fallback strategy (se LLM fail → default plan) (2 giorni)
5. A/B testing framework (10% traffic a nuovo prompt) (3 giorni)
6. Tests: golden dataset 50 query → validate ExecutionPlan quality

**Prompt Engineering Workflow**:
```
1. Draft prompt versione 1.0
2. Test su 20 query → collect ExecutionPlans
3. Manual review con legal expert: "Queste scelte hanno senso?"
4. Refine prompt (add examples, clarify rules)
5. Repeat fino a quality acceptance
```

#### 3.6 Orchestrator (Parallel Agent Dispatch)

**File**: `backend/orchestration/orchestrator.py`

Esegue ExecutionPlan:
```python
async def execute_plan(plan: ExecutionPlan) -> RetrievalResult:
    """
    1. Parse retrieval_plan
    2. Dispatch agents in parallel (asyncio.gather)
    3. Timeout per agent (5s)
    4. Aggregate results
    5. Handle partial failures
    """
    tasks = []

    if plan.retrieval_plan.kg_agent.enabled:
        tasks.append(kg_agent.execute(plan.retrieval_plan.kg_agent.tasks))
    if plan.retrieval_plan.api_agent.enabled:
        tasks.append(api_agent.execute(plan.retrieval_plan.api_agent.tasks))
    if plan.retrieval_plan.vectordb_agent.enabled:
        tasks.append(vectordb_agent.execute(...))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return aggregate_results(results, plan)
```

**Tasks** (1 settimana):
1. Implementa async dispatch logic (3 giorni)
2. Timeout & retry handling (2 giorni)
3. Circuit breaker per agent (1 giorno)
4. Metrics: agent latency, failure rate (1 giorno)

### Testing & Validation Fase 3

**Integration Tests**:
- [ ] End-to-end: query → Router → 3 agents → aggregated RetrievalResult
- [ ] Agent isolation: ogni agent testabile independently
- [ ] Failure scenarios: 1/3 agent fails, system degrada gracefully

**Performance Tests**:
- [ ] Latency P95 < 2.5s (Router + agents parallel)
- [ ] Throughput: 5 req/s su single instance

**LLM Router Quality**:
- Golden dataset 100 query con human-annotated "best ExecutionPlan"
- Metric: Agreement con expert plan > 70%

### Milestone 3: Full Orchestration Demo

**Deliverable**:
- Live demo: 10 query → visualizza ExecutionPlan → retrieval results
- Dashboard Grafana con metrics (agent latency, cache hit rate)
- Comparison: rule-based router vs LLM router (quality & cost)

**Durata Fase 3**: 8 settimane con 4 developers (1 ML + 2 backend + 1 data engineer)

---

## Fase 4: Reasoning Layer (Settimane 23-30)

### Obiettivo

Implementare i **4 Legal Reasoning Experts** + Synthesizer:
- Literal Interpreter
- Systemic-Teleological
- Principles Balancer
- Precedent Analyst
- Synthesizer (combina expert outputs)

**Approccio**: Tutti experts sono LLM-based (stesso model, prompts diversi).

### Deliverables

#### 4.1 Expert Prompt Engineering (Iterativo)

**Per ogni expert**:

1. **Literal Interpreter** (settimane 23-24):
   - System prompt: analisi testuale letterale delle norme
   - Input: norm texts (da API Agent) + query
   - Output: interpretazione letterale con citazioni precise
   - Validation: 20 query test con legal expert review

2. **Systemic-Teleological** (settimane 25-26):
   - System prompt: interpretazione sistematica (norme collegate) + teleologica (ratio legis)
   - Input: norm texts + KG context (norme correlate)
   - Output: interpretazione considerando contesto normativo
   - Validation: 20 query complesse

3. **Principles Balancer** (settimana 27):
   - System prompt: bilanciamento principi costituzionali
   - Input: principi in conflitto + norme costituzionali
   - Output: bilanciamento ragionato
   - Use case: privacy vs libertà espressione

4. **Precedent Analyst** (settimana 28):
   - System prompt: analisi giurisprudenza
   - Input: sentenze relevant (da VectorDB) + query
   - Output: analisi evoluzione giurisprudenziale
   - Validation: 15 query con precedenti noti

**Tasks per expert** (2 settimane each):
1. Draft prompt v1.0 (2 giorni)
2. Test su 20 query (3 giorni)
3. Legal expert review & feedback (2 giorni)
4. Refine prompt v1.1 (2 giorni)
5. Re-test (2 giorni)
6. Finalize prompt v1.2 (1 giorno)
7. Implementa API endpoint: `POST /experts/{expert_type}/analyze` (2 giorni)

**Output format standardizzato**:
```json
{
  "expert_type": "Literal_Interpreter",
  "analysis": "L'art. 2 c.c. stabilisce che...",
  "sources": [
    {"norm_id": "art_2_cc", "quote": "La maggiore età...", "relevance": 0.95}
  ],
  "confidence": 0.88,
  "limitations": "Analisi limitata al testo normativo, senza considerare..."
}
```

#### 4.2 Synthesizer Implementation

**File**: `backend/reasoning/synthesizer.py`

**Due modalità** (da ExecutionPlan):
1. **Convergent synthesis**: Cerca consensus tra experts
2. **Divergent synthesis**: Presenta prospettive multiple

**Implementazione**:
```python
async def synthesize(
    expert_outputs: List[ExpertOutput],
    mode: Literal["convergent", "divergent"],
    query: str
) -> FinalAnswer:
    """
    System prompt per Synthesizer LLM:

    "You are a legal synthesizer. Given analyses from multiple legal
    reasoning experts, combine them into a unified answer.

    Mode: {mode}
    - convergent: Find common ground, highlight consensus
    - divergent: Present all perspectives, explain disagreements

    Expert outputs:
    {expert_outputs}

    Query: {query}

    Provide:
    1. Synthesized answer
    2. Source attribution (which expert contributed what)
    3. Confidence score
    4. Disagreements (if any)
    "
    """
    # LLM call
    # Return FinalAnswer with full provenance
```

**Tasks** (2 settimane):
1. Prompt engineering per synthesizer (1 settimana)
2. Implementa convergent mode (3 giorni)
3. Implementa divergent mode (3 giorni)
4. Source attribution logic (1 giorno)
5. Tests: 30 query con 2-4 experts → validate synthesis quality

#### 4.3 Iteration Controller

**File**: `backend/reasoning/iteration_controller.py`

Decide se iterare o fermarsi:
```python
def should_iterate(
    provisional_answer: FinalAnswer,
    stop_criteria: StopCriteria,
    current_iteration: int
) -> bool:
    """
    Stop if:
    1. Confidence > min_confidence (es. 0.85)
    2. Expert consensus high
    3. Max iterations reached

    Iterate if:
    1. Confidence low → need more retrieval
    2. Experts disagree strongly → need Precedent Analyst
    """
    if current_iteration >= stop_criteria.max_iterations:
        return False

    if provisional_answer.confidence < stop_criteria.min_confidence:
        return True

    if provisional_answer.expert_consensus < 0.7:
        return True

    return False
```

**Tasks** (1 settimana):
1. Implementa iteration logic (3 giorni)
2. Feedback loop: se iterate → Router con context aggiornato (2 giorni)
3. Max iterations safeguard (hard limit 3) (1 giorno)
4. Tests: 10 query che triggherano iteration

### Testing & Validation Fase 4

**Expert Quality**:
- Legal expert review per ogni expert type (20 query each)
- Metric: "Analisi corretta e utile?" → Yes > 80%

**Synthesizer Quality**:
- Golden dataset: 50 query con multi-expert outputs → human-written ideal synthesis
- Metric: ROUGE score > 0.70 tra synthesis e golden

**End-to-End**:
- 100 query complete: Preprocessing → Orchestration → Reasoning → Final Answer
- Latency P95 < 10s (include LLM calls)
- Answer quality review da legal experts: score 4/5 average

### Milestone 4: Full Pipeline Demo

**Deliverable**:
- Live demo completo: query legale → final answer con provenance
- Side-by-side comparison: different expert combinations
- Iteration examples: query che richiedono 2+ iterations
- Documentazione: API completa, esempi curl
- Video tutorial 10 min per legal professionals

**Durata Fase 4**: 8 settimane con 3 developers (2 prompt engineers/ML + 1 backend)

---

## Fase 5: Integration & Testing (Settimane 31-36)

### Obiettivo

**Stabilizzare, testare, ottimizzare** prima di produzione:
- Integration testing end-to-end
- Performance optimization
- Security hardening
- Observability (logging, metrics, tracing)
- User acceptance testing (UAT) con legal experts

### Deliverables

#### 5.1 Comprehensive Testing Suite

**Unit tests** (continuo da fasi precedenti):
- Coverage > 85% per tutti i moduli
- Property-based testing per RLCF math
- Mocking per external services (OpenAI, Neo4j, Weaviate)

**Integration tests** (2 settimane):
- Database integration (PostgreSQL, Neo4j, Redis, Weaviate)
- Agent communication
- LLM API integration (con rate limiting)
- RLCF feedback loop completo

**E2E tests** (2 settimane):
- 50 query scenarios end-to-end
- Multi-iteration scenarios
- Failure recovery (agent timeout, LLM error)
- Tool: Playwright per UI (se frontend ready) + API tests

**Load testing** (1 settimana):
- Tool: Locust o k6
- Scenarios:
  - 10 concurrent users (steady state)
  - 50 users (peak)
  - Ramp up: 0 → 50 over 5 min
- Metrics: P95 latency, error rate, throughput
- Target: P95 < 15s, error rate < 1%

#### 5.2 Performance Optimization

**Profiling** (1 settimana):
- Python: cProfile, py-spy
- Database: EXPLAIN ANALYZE su query lente
- Identificare bottleneck

**Optimizations**:
1. **LLM caching**: Cache identical queries (Redis, TTL 1h) → 30% speedup
2. **Embedding caching**: Cache embeddings per query (reduce OpenAI calls)
3. **Database indexing**: Review tutti gli index Neo4j/PostgreSQL
4. **Agent parallelism**: Ensure real parallel execution (asyncio)
5. **Connection pooling**: PostgreSQL (max 20 connections), Neo4j (5)

**Tasks** (2 settimane):
- Profiling e identificazione bottleneck (1 settimana)
- Implementa top 5 optimizations (1 settimana)
- Re-test load: validate miglioramenti

#### 5.3 Observability Stack

**Logging**:
- Structured JSON logs (tutti i servizi)
- Trace ID propagation (per seguire request end-to-end)
- Log aggregation: Loki o CloudWatch (se AWS)

**Metrics**:
- Prometheus + Grafana
- Metrics da tracciare:
  - Request latency (per layer)
  - LLM API costs ($ per query)
  - Cache hit rates
  - Error rates per component
  - RLCF feedback submission rate

**Tracing**:
- OpenTelemetry
- Jaeger per distributed tracing
- Visualizza: Query → Preprocessing → Router → Agents → Experts → Synthesizer

**Tasks** (2 settimane):
1. Setup Prometheus + Grafana (3 giorni)
2. Instrument code con metrics (4 giorni)
3. Setup OpenTelemetry + Jaeger (3 giorni)
4. Dashboards: 5 dashboard principali (2 giorni)
   - System health
   - RLCF metrics
   - LLM costs
   - User queries analytics
   - Error tracking

#### 5.4 Security Hardening

**Authentication**:
- JWT tokens per API
- Admin API key per operazioni privilegiate
- Rate limiting: 100 req/min per user

**Data protection**:
- Encryption at rest (database)
- Encryption in transit (TLS)
- PII handling: anonimizzazione in logs

**Vulnerability scanning**:
- Dependabot per dependencies
- OWASP ZAP per penetration testing
- Safety check per Python packages

**Tasks** (1 settimana):
1. Implementa JWT auth (2 giorni)
2. Setup rate limiting (1 giorno)
3. TLS certificates (1 giorno)
4. Security audit & fixes (2 giorni)

#### 5.5 User Acceptance Testing (UAT)

**Participants**: 5-10 legal professionals da ALIS

**Process**:
1. **Training session** (2h): Come usare il sistema
2. **Testing period** (2 settimane):
   - Ogni partecipante: 20 query reali
   - Raccolta feedback via form
   - Bug reporting in GitHub Issues
3. **Feedback analysis** (1 settimana):
   - Prioritize issues
   - Quick fixes vs future iterations
4. **Iteration** (1 settimana):
   - Fix critical bugs
   - Improve prompts basato su feedback

**Metrics UAT**:
- Answer quality: avg score > 4/5
- System usability: SUS score > 70
- Bug severity: no P0/P1 bugs at launch

### Milestone 5: Production-Ready System

**Deliverable**:
- Test suite completo (pass rate 100%)
- Load test report: sistema regge 50 concurrent users
- Observability dashboards operativi
- Security audit completato
- UAT report: ready for beta launch

**Durata Fase 5**: 6 settimane con 4 developers (2 backend + 1 DevOps + 1 QA)

---

## Fase 6: Production Readiness (Settimane 37-42)

### Obiettivo

**Deploy in produzione** con infrastructure production-grade:
- Kubernetes cluster
- CI/CD automation
- Disaster recovery
- Monitoring & alerting
- Documentation for ops

### Deliverables

#### 6.1 Kubernetes Setup

**Infrastructure** (GKE o EKS):
- Cluster: 6 nodes (n1-standard-4 o equivalent)
  - 3 nodes per app services
  - 3 nodes per databases (StatefulSets)
- Auto-scaling: HPA (Horizontal Pod Autoscaler)
- Namespaces: `production`, `staging`

**Deployments**:
```yaml
# backend/orchestration/k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: router
  template:
    metadata:
      labels:
        app: router
    spec:
      containers:
      - name: router
        image: merl-t/router:v1.0.0
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: openai-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
```

**Tasks** (3 settimane):
1. Setup GKE/EKS cluster (3 giorni)
2. Write Kubernetes manifests per tutti i services (1 settimana)
3. Setup Helm charts (opzionale, 1 settimana)
4. StatefulSets per databases (PostgreSQL, Neo4j, Redis) (4 giorni)
5. Ingress + Load Balancer (NGINX Ingress) (2 giorni)
6. SSL certificates (Let's Encrypt + cert-manager) (1 giorno)

#### 6.2 CI/CD Pipeline (Production)

**GitHub Actions workflows**:

**Build & Push**:
```yaml
# .github/workflows/build-push.yml
name: Build and Push Docker Images

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t merl-t/router:${{ github.sha }} backend/orchestration/
      - name: Push to registry
        run: docker push merl-t/router:${{ github.sha }}
```

**Deploy**:
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy (e.g., v1.0.0)'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/router \
            router=merl-t/router:${{ github.event.inputs.version }} \
            -n production
      - name: Wait for rollout
        run: kubectl rollout status deployment/router -n production
```

**Tasks** (1 settimana):
1. Docker multi-stage builds per tutti i services (3 giorni)
2. GitHub Actions per build + push (2 giorni)
3. GitHub Actions per deploy (2 giorni)

#### 6.3 Database Backup & Disaster Recovery

**Backup strategy**:
- **PostgreSQL**: Daily backups → S3/GCS (retention 30 giorni)
- **Neo4j**: Weekly full backup + daily incrementals
- **Weaviate**: Weekly backup (rebuilding da source è possibile)

**Disaster recovery**:
- RPO (Recovery Point Objective): 24h (daily backups)
- RTO (Recovery Time Objective): 4h (restore + validation)

**Tasks** (1 settimana):
1. Setup automated backups (CronJobs in K8s) (3 giorni)
2. Disaster recovery runbook (2 giorni)
3. Test restore procedure (1 giorno)

#### 6.4 Monitoring & Alerting

**Alerts** (PagerDuty o Opsgenie):
- **P0 (Critical)**: API down, database down → page on-call immediately
- **P1 (High)**: Error rate > 5%, latency P95 > 30s → alert in 5 min
- **P2 (Medium)**: Cache hit rate < 30%, LLM costs spike → alert in 1h

**Grafana Dashboards**:
1. **System Health**: Uptime, error rate, latency
2. **Business Metrics**: Queries/day, RLCF feedback rate, user growth
3. **Cost Tracking**: LLM API costs per day/week
4. **Database Performance**: Query latency, connection pool usage

**Tasks** (1 settimana):
1. Setup alerting rules in Prometheus (2 giorni)
2. Integrate PagerDuty (1 giorno)
3. Finalize Grafana dashboards (2 giorni)
4. On-call rotation setup (1 giorno)

#### 6.5 Documentation for Operations

**Runbooks**:
1. **Deployment runbook**: Step-by-step deploy new version
2. **Incident response**: How to handle P0/P1 incidents
3. **Scaling runbook**: When/how to scale (HPA tuning)
4. **Database maintenance**: Vacuum, reindex, backup restore

**API Documentation**:
- OpenAPI spec published at `https://api.merl-t.ai/docs`
- Postman collection per developers
- SDK (opzionale): Python client library

**Tasks** (1 settimana):
1. Write runbooks (4 giorni)
2. Publish API docs (1 giorno)
3. Create video tutorials (2 giorni)

### Milestone 6: Production Launch

**Go/No-Go Checklist**:
- [ ] All tests passing (unit, integration, E2E)
- [ ] Load test: 50 concurrent users, P95 < 15s
- [ ] Security audit: no P0/P1 vulnerabilities
- [ ] UAT: avg score > 4/5
- [ ] Monitoring: dashboards operational, alerts tested
- [ ] Disaster recovery: backup tested, runbook validated
- [ ] Documentation: runbooks complete
- [ ] Team training: 2 engineers can deploy & troubleshoot

**Launch Strategy**:
1. **Soft launch** (week 42): Invite-only, 50 beta users (ALIS members)
2. **Monitor** (weeks 43-44): Daily checks, quick iterations
3. **Public launch** (week 45+): Open to public with rate limits

**Durata Fase 6**: 6 settimane con 3 developers (2 DevOps/SRE + 1 technical writer)

---

## Fase 7: Launch & Iteration (Settimane 43+)

### Obiettivo

**Operare e migliorare** il sistema in produzione:
- Monitor user behavior
- RLCF feedback loops operativi
- Continuous improvement

### Activities (Ongoing)

#### 7.1 Post-Launch Monitoring (Weeks 43-46)

**Daily standups**:
- Review metrics: queries/day, error rate, user feedback
- Triage bugs from users
- Quick fixes (hotfix branches)

**Weekly reviews**:
- LLM prompt quality: Are ExecutionPlans optimal?
- RLCF feedback analysis: Are legal experts engaged?
- Cost review: LLM API spend vs budget

#### 7.2 RLCF Model Training (Monthly)

**Process**:
1. **Month 1**: Accumulate 500+ feedback entries
2. **Month 2**:
   - Analyze feedback patterns
   - Identify low-rated ExecutionPlans
   - Update Router prompt (add examples)
3. **A/B test**: New prompt vs old (10% traffic, 7 giorni)
4. **Rollout**: Se metrics migliorano, deploy al 100%

**Metrics to optimize**:
- Average answer rating (target: 4.5/5)
- Expert consensus (target: > 0.80)
- Retrieval efficiency (% agents activated vs used)

#### 7.3 Feature Roadmap (Months 3-12)

**Q1 (Months 3-6)**:
- [ ] Frontend web app completo (React)
- [ ] User authentication & profiles
- [ ] Query history & favorites
- [ ] Export answers to PDF/DOCX

**Q2 (Months 6-9)**:
- [ ] Retrieval patterns P5-P6 (multi-query, cross-modal)
- [ ] Fine-tuned embeddings (legal domain)
- [ ] Cross-encoder reranking con custom training
- [ ] API rate tiers (free, pro, enterprise)

**Q3 (Months 9-12)**:
- [ ] Multi-language support (English legal queries)
- [ ] Jurisprudence auto-ingestion pipeline
- [ ] Advanced RLCF: model fine-tuning (non solo prompt)
- [ ] Enterprise features: white-label, on-premise deployment

### Success Metrics (Year 1)

**User Metrics**:
- 1,000+ registered users
- 10,000+ queries processed
- 500+ RLCF feedback submissions

**Quality Metrics**:
- Average answer rating: 4.3/5
- Expert consensus: 0.82
- Precision@10 (retrieval): 0.88

**Business Metrics**:
- LLM API costs: < €5,000/month
- Uptime: 99.5%
- Community engagement: 50+ active contributors (RLCF feedback)

---

## Gestione dei Rischi

### Rischi Tecnici

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| **LLM API rate limits** | Media | Alto | • Caching aggressivo<br>• Fallback a modelli open-source<br>• Budget alerts |
| **Neo4j performance su large graph** | Media | Medio | • Indexing ottimizzato<br>• Query profiling<br>• Sharding (se necessario) |
| **VectorDB costi storage** | Bassa | Medio | • Start con subset (10K chunks)<br>• Compression<br>• Tiered storage |
| **Prompt brittleness (LLM Router)** | Alta | Alto | • RLCF feedback loop<br>• A/B testing<br>• Fallback rules |
| **Data quality (KG popolazione)** | Media | Alto | • Manual validation sample<br>• Crowdsourcing ALIS members<br>• Iterative refinement |

### Rischi di Progetto

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| **Scope creep** | Alta | Alto | • Strict phase gating<br>• MVP-first mentality<br>• Feature freeze 4 weeks before launch |
| **Legal expert availability** | Media | Medio | • Engage ALIS early<br>• Compensate experts<br>• Async feedback tools |
| **Team turnover** | Media | Alto | • Documentation culture<br>• Pair programming<br>• Knowledge sharing sessions |
| **Budget overrun (LLM costs)** | Media | Alto | • Cost monitoring dashboards<br>• Budget alerts<br>• Optimize prompts for token efficiency |

### Rischi di Compliance

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| **AI Act non-compliance** | Bassa | Critico | • Legal counsel review<br>• Transparency features built-in<br>• Audit trail per decision |
| **GDPR violations** | Bassa | Alto | • PII anonymization<br>• Data retention policies<br>• User consent flows |

---

## Team e Competenze Richieste

### Team Core (Fasi 1-6)

**Full-time (8-10 persone)**:
1. **Tech Lead / Architect** (1): Decisioni architetturali, code review
2. **Backend Developers** (3): FastAPI, async Python, databases
3. **ML/NLP Engineers** (2): Prompt engineering, NER, embeddings
4. **Data Engineer** (1): Neo4j, ETL, vector database
5. **DevOps/SRE** (1): Kubernetes, CI/CD, monitoring
6. **QA Engineer** (1): Testing strategy, automation
7. **Frontend Developer** (1): React (Fase 7+)

**Part-time / Consulenti**:
- **Legal Experts** (3-5 da ALIS): Validation, RLCF feedback, UAT
- **Technical Writer** (1): Documentation, runbooks
- **Security Consultant** (1): Audit, penetration testing

### Competenze Chiave

**Must-have**:
- Python async/await (FastAPI, SQLAlchemy)
- LLM prompting & API integration (OpenAI, Anthropic)
- Graph databases (Neo4j, Cypher)
- Vector databases (Weaviate, Chroma)
- Kubernetes & Docker
- Git workflow (GitFlow)

**Nice-to-have**:
- Fine-tuning ML models (HuggingFace)
- Italian legal domain knowledge
- React/TypeScript
- Terraform (IaC)

---

## Budget e Risorse

### Costi Stimati (10 mesi, Fasi 0-6)

**Team** (€/mese):
- 8 developers @ €5,000/mese avg = €40,000/mese
- Consulenti (€10,000/mese)
- **Totale team**: €50,000/mese × 10 = **€500,000**

**Infrastruttura** (€/mese):
- GKE/EKS cluster (6 nodes): €800/mese
- Databases (managed): €300/mese
- LLM API (OpenAI): €2,000/mese (stima, varia con usage)
- Monitoring tools: €200/mese
- **Totale infra**: €3,300/mese × 10 = **€33,000**

**Servizi & Licenze**:
- Neo4j Enterprise (opzionale): €15,000/anno
- GitHub Enterprise: €2,000/anno
- Misc tools: €3,000
- **Totale servizi**: **€20,000**

**Contingency** (20%): **€110,000**

### Budget Totale: **€663,000** (10 mesi)

**Finanziamento**:
- Grant ALIS / EU funding
- University partnerships (risorse in-kind)
- Corporate sponsors (legal tech companies)

---

## Metriche di Successo

### Technical Metrics

| Metrica | Target | Measurement |
|---------|--------|-------------|
| **API Uptime** | 99.5% | Prometheus uptime checks |
| **Latency P95** | < 15s | End-to-end query processing |
| **Error Rate** | < 1% | Failed queries / total queries |
| **Test Coverage** | > 85% | pytest --cov |
| **RLCF Feedback Rate** | > 10% | Feedback submissions / queries |

### Quality Metrics

| Metrica | Target | Measurement |
|---------|--------|-------------|
| **Answer Quality** | 4.3/5 avg | User ratings (RLCF) |
| **Expert Consensus** | > 0.80 | Agreement among reasoning experts |
| **NER F1 Score** | > 0.85 | Evaluated on test set |
| **Retrieval Precision@10** | > 0.80 | Relevant docs in top-10 |

### Business Metrics

| Metrica | Target (Year 1) | Measurement |
|---------|-----------------|-------------|
| **Registered Users** | 1,000+ | User database |
| **Queries Processed** | 10,000+ | Query logs |
| **RLCF Contributors** | 50+ | Active feedback submitters |
| **LLM Cost Efficiency** | < €0.50/query | Total LLM spend / queries |

---

## Conclusioni

### Approccio Consigliato

1. **Start Small, Iterate Fast**: Fase 1 (RLCF MVP) valida l'idea core in 6 settimane
2. **Vertical Slices**: Ogni fase rilascia funzionalità end-to-end testabili
3. **Expert Validation**: Coinvolgi legal experts ALIS in ogni fase
4. **Cost-Conscious**: Monitora LLM costs da giorno 1, ottimizza prompts
5. **Production-First**: Infrastruttura seria (K8s, monitoring) non opzionale

### Prossimi Passi Immediati

**Settimana 1**:
1. [ ] Finalizza team: recruita tech lead + 2 backend developers
2. [ ] Setup repository (GitHub org, struttura monorepo)
3. [ ] Kickoff meeting: align su vision, roadmap, workflow
4. [ ] Start Fase 0: Docker Compose + CI/CD

**Settimana 2**:
1. [ ] Complete Fase 0 checklist
2. [ ] Legal experts ALIS: define 20 test queries per Fase 1
3. [ ] Budget approval: presente questo documento a stakeholders ALIS

**Week 3**:
1. [ ] Start Fase 1: Database schema + Authority module
2. [ ] Daily standups (15 min)
3. [ ] Weekly demo Fridays

### Risorse Addizionali

**Template**:
- Project charter template
- Sprint planning template (Jira/Linear)
- Incident response template

**Learning Resources**:
- Neo4j Graph Academy (free)
- FastAPI tutorial (official docs)
- LangChain documentation
- Kubernetes basics (CNCF tutorials)

---

**Buona fortuna con MERL-T! 🚀**

*Documento vivente - aggiorna man mano che procedi. Track progress in GitHub Projects.*
