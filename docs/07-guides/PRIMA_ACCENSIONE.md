# 🚀 Guida alla Prima Accensione di MERL-T

**Versione**: 1.0
**Data**: 15 Novembre 2025
**Stato Sistema**: v0.9.0 (82% completo - Production Ready)

---

## 📋 Indice

1. [Prerequisiti](#prerequisiti)
2. [Setup Iniziale](#setup-iniziale)
3. [Avvio dei Servizi](#avvio-dei-servizi)
4. [Verifica del Sistema](#verifica-del-sistema)
5. [Prima Esplorazione](#prima-esplorazione)
6. [Test delle Funzionalità](#test-delle-funzionalità)
7. [Troubleshooting](#troubleshooting)
8. [Comandi Utili](#comandi-utili)

---

## 🔧 Prerequisiti

### Software Richiesto

Verifica di avere installato:

```bash
# Python 3.11+
python3 --version  # Deve essere >= 3.11

# Node.js 18+ e npm
node --version     # Deve essere >= 18
npm --version

# Docker e Docker Compose
docker --version
docker-compose --version

# Git
git --version
```

### Porte Necessarie

Il sistema usa le seguenti porte (verifica che siano libere):

| Servizio | Porta | Descrizione |
|----------|-------|-------------|
| **Frontend** | 3000 | React 19 (Vite dev server) |
| **Backend Orchestration** | 8000 | FastAPI orchestration API |
| **Backend RLCF** | 8001 | FastAPI RLCF framework |
| **PostgreSQL** | 5432 | Database relazionale |
| **Redis** | 6379 | Cache e rate limiting |
| **Qdrant** | 6333 | Vector database |
| **Neo4j** | 7474, 7687 | Graph database (web + bolt) |

```bash
# Verifica porte libere (macOS/Linux)
lsof -i :3000
lsof -i :8000
lsof -i :8001
lsof -i :5432
```

---

## ⚙️ Setup Iniziale

### 1. Clone del Repository

```bash
# Se non l'hai già fatto
cd ~/Desktop/CODE
git clone <repository-url> MERL-T_alpha
cd MERL-T_alpha
```

### 2. Configurazione Variabili Ambiente

```bash
# Copia il template
cp .env.template .env

# Modifica con il tuo editor preferito
nano .env  # oppure vim, code, etc.
```

**Variabili Essenziali da Configurare**:

```bash
# === LLM & AI ===
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE
ROUTER_MODEL=anthropic/claude-3.5-sonnet
EXPERT_MODEL=anthropic/claude-3.5-sonnet

# === Database (dev mode - usa SQLite) ===
DATABASE_URL=sqlite+aiosqlite:///./merl_t.db

# === Redis (opzionale in dev) ===
REDIS_URL=redis://localhost:6379

# === Qdrant (opzionale in dev) ===
QDRANT_HOST=localhost
QDRANT_PORT=6333

# === Neo4j (opzionale in dev) ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# === API Keys ===
ADMIN_API_KEY=dev-admin-key-12345
```

**⚠️ IMPORTANTE**: Ottieni la tua OpenRouter API key da https://openrouter.ai/

### 3. Setup Python Backend

```bash
# Crea virtual environment
python3 -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa dipendenze
pip install -e .

# Verifica installazione
rlcf-cli --help
rlcf-admin --help
```

### 4. Setup Frontend

```bash
cd frontend/rlcf-web

# Installa dipendenze
npm install

# Torna alla root
cd ../..
```

### 5. Inizializzazione Database

**Opzione A: Solo SQLite (più semplice per iniziare)**

```bash
# Crea database e tabelle
rlcf-admin db migrate

# Popola con dati di esempio (opzionale)
rlcf-admin db seed --users 5 --tasks 10
```

**Opzione B: Con Docker (PostgreSQL + altri servizi)**

```bash
# Avvia i database
docker-compose -f docker-compose.dev.yml up -d

# Aspetta 10 secondi che i servizi si avviino
sleep 10

# Esegui migrazioni
rlcf-admin db migrate

# Popola dati di esempio
rlcf-admin db seed --users 5 --tasks 10
```

---

## 🚀 Avvio dei Servizi

### Scenario 1: Sviluppo Rapido (Solo SQLite)

**Terminale 1 - Backend Orchestration**:
```bash
source venv/bin/activate
cd backend/orchestration
uvicorn api.main:app --reload --port 8000
```

**Terminale 2 - Backend RLCF**:
```bash
source venv/bin/activate
cd backend/rlcf_framework
uvicorn main:app --reload --port 8001
```

**Terminale 3 - Frontend**:
```bash
cd frontend/rlcf-web
npm run dev
```

### Scenario 2: Sviluppo Completo (Con Docker)

**Terminale 1 - Avvia tutti i database**:
```bash
docker-compose -f docker-compose.dev.yml up
```

**Terminale 2 - Backend Orchestration**:
```bash
source venv/bin/activate
cd backend/orchestration
export DATABASE_URL=postgresql+asyncpg://merl_t:merl_t_password@localhost/merl_t_orchestration
export REDIS_URL=redis://localhost:6379
uvicorn api.main:app --reload --port 8000
```

**Terminale 3 - Backend RLCF**:
```bash
source venv/bin/activate
cd backend/rlcf_framework
export DATABASE_URL=postgresql+asyncpg://merl_t:merl_t_password@localhost/merl_t_rlcf
uvicorn main:app --reload --port 8001
```

**Terminale 4 - Frontend**:
```bash
cd frontend/rlcf-web
npm run dev
```

### Scenario 3: Docker Compose Completo (Più Semplice)

```bash
# Avvia tutto con un solo comando
docker-compose up -d

# Controlla i log
docker-compose logs -f
```

---

## ✅ Verifica del Sistema

### 1. Verifica Backend Orchestration API

```bash
# Controlla health endpoint
curl http://localhost:8000/health

# Output atteso:
# {"status":"healthy","version":"0.9.0"}

# Apri documentazione API interattiva
open http://localhost:8000/docs
```

### 2. Verifica Backend RLCF API

```bash
# Controlla health endpoint
curl http://localhost:8001/health

# Apri documentazione API interattiva
open http://localhost:8001/docs
```

### 3. Verifica Frontend

```bash
# Apri l'applicazione web
open http://localhost:3000

# Dovresti vedere la homepage di MERL-T
```

### 4. Verifica Database (se usi Docker)

```bash
# PostgreSQL
docker exec -it merl-t-postgres psql -U merl_t -d merl_t_orchestration -c "SELECT COUNT(*) FROM queries;"

# Redis
docker exec -it merl-t-redis redis-cli PING
# Output atteso: PONG

# Qdrant
curl http://localhost:6333/collections

# Neo4j
open http://localhost:7474
# Login: neo4j / your-secure-password
```

---

## 🎯 Prima Esplorazione

### A. Interfaccia Web (Frontend)

#### 1. Homepage (`http://localhost:3000`)

Dovresti vedere:
- **Hero Section**: "MERL-T - Multi-Expert Legal Retrieval Transformer"
- **Navigation Bar**: Links a Query, Admin, About
- **Feature Cards**: Descrizione delle 4 caratteristiche principali

#### 2. Query Interface (`/query`)

**Cosa Puoi Fare**:
- Inserire una domanda legale in italiano
- Esempio: "Quali sono gli obblighi del venditore secondo l'art. 1476 Codice Civile?"
- Vedere il workflow di orchestrazione in tempo reale
- Visualizzare le risposte dei 4 esperti:
  - 📖 Literal Interpreter
  - 🏛️ Systemic/Teleological
  - ⚖️ Principles Balancer
  - 📚 Precedent Analyst

**Test Rapido**:
```bash
# Oppure usa l'API direttamente
curl -X POST http://localhost:8000/api/v1/queries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key-12345" \
  -d '{
    "query_text": "Quali sono le conseguenze della risoluzione del contratto per inadempimento?",
    "context": {
      "domain": "civil_law",
      "jurisdiction": "italy"
    }
  }'
```

#### 3. Admin Dashboard (`/admin`)

**Sezioni Disponibili**:

**a) Task Manager**:
- Visualizza tutti i task RLCF
- Filtra per stato: OPEN, IN_PROGRESS, COMPLETED
- Filtra per tipo: classification, validation, comparison, etc.
- Esporta task in JSON

**b) User Management**:
- Visualizza esperti registrati
- Ordina per authority score
- Vedi competenze per dominio
- Statistiche di partecipazione

**c) Configuration Manager**:
- Modifica parametri RLCF:
  - Authority weights (α, β, γ)
  - Uncertainty threshold
  - Min evaluators
- Modifica task type schemas
- Live validation JSON

**d) Data Export**:
- Esporta dati aggregati
- Download CSV/JSON
- Filtra per data range

#### 4. Execution Traces (`/admin/traces`)

Visualizza:
- Workflow completo di ogni query
- Timing di ogni fase (preprocessing → routing → reasoning → synthesis)
- Input/output di ogni agente
- Expert opinions con provenance
- Metriche di performance

### B. API Documentation (Swagger UI)

#### Orchestration API (`http://localhost:8000/docs`)

**Endpoints Principali**:

1. **POST /api/v1/queries** - Invia nuova query
2. **GET /api/v1/queries/{query_id}** - Ottieni risultato
3. **GET /api/v1/queries/{query_id}/trace** - Vedi execution trace
4. **POST /api/v1/feedback/user** - Invia feedback utente
5. **POST /api/v1/feedback/rlcf** - Invia feedback esperto RLCF
6. **POST /api/v1/feedback/ner** - Correggi NER entities
7. **GET /api/v1/stats/queries** - Statistiche query
8. **GET /api/v1/stats/authority** - Classifica esperti

#### RLCF API (`http://localhost:8001/docs`)

**Endpoints Principali**:

1. **POST /tasks** - Crea nuovo task di valutazione
2. **GET /tasks** - Lista tutti i task
3. **GET /tasks/{task_id}** - Dettagli task specifico
4. **POST /tasks/{task_id}/evaluate** - Valuta task (esperto)
5. **GET /tasks/{task_id}/consensus** - Ottieni consenso aggregato
6. **POST /users** - Registra nuovo esperto
7. **GET /users** - Lista esperti
8. **GET /users/{user_id}/authority** - Authority score esperto
9. **GET /config/model** - Ottieni model config
10. **PUT /config/model** - Aggiorna model config

---

## 🧪 Test delle Funzionalità

### Test 1: Query End-to-End

```bash
# 1. Invia query
QUERY_ID=$(curl -X POST http://localhost:8000/api/v1/queries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key-12345" \
  -d '{
    "query_text": "Cosa prevede l'\''art. 2043 del Codice Civile?",
    "context": {"domain": "civil_law", "jurisdiction": "italy"}
  }' | jq -r '.query_id')

echo "Query ID: $QUERY_ID"

# 2. Aspetta 10-15 secondi per l'elaborazione
sleep 15

# 3. Ottieni risultato
curl http://localhost:8000/api/v1/queries/$QUERY_ID | jq '.'

# 4. Ottieni execution trace
curl http://localhost:8000/api/v1/queries/$QUERY_ID/trace | jq '.'
```

### Test 2: Creazione e Valutazione Task RLCF

```bash
# 1. Crea task di classificazione
TASK_ID=$(curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "classification",
    "input_data": {
      "text": "Il venditore deve consegnare la cosa al compratore entro 30 giorni.",
      "domain": "civil_law",
      "options": ["contract_law", "tort_law", "property_law"]
    },
    "ground_truth": {
      "correct_class": "contract_law",
      "confidence": 0.95
    }
  }' | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# 2. Registra esperto
USER_ID=$(curl -X POST http://localhost:8001/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "mario_rossi",
    "competence_domains": ["civil_law", "contract_law"],
    "credentials": {
      "academic_degree": "phd",
      "years_experience": 10,
      "publications": 5
    }
  }' | jq -r '.user_id')

echo "User ID: $USER_ID"

# 3. Esperto valuta task
curl -X POST http://localhost:8001/tasks/$TASK_ID/evaluate \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": $USER_ID,
    \"response_data\": {
      \"selected_class\": \"contract_law\",
      \"confidence\": 0.9,
      \"explanation\": \"Il testo parla di obblighi del venditore, tipico del diritto contrattuale.\"
    }
  }"

# 4. Ottieni authority score aggiornato
curl http://localhost:8001/users/$USER_ID/authority | jq '.'
```

### Test 3: Feedback Loop

```bash
# 1. Invia feedback utente su un risultato
curl -X POST http://localhost:8000/api/v1/feedback/user \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key-12345" \
  -d '{
    "trace_id": "'"$QUERY_ID"'",
    "rating": 5,
    "feedback_text": "Risposta molto completa e accurata!",
    "categories": ["accuracy", "completeness"]
  }'

# 2. Invia correzione NER
curl -X POST http://localhost:8000/api/v1/feedback/ner \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key-12345" \
  -d '{
    "trace_id": "'"$QUERY_ID"'",
    "expert_id": 1,
    "correction_type": "entity_addition",
    "original_entity": {},
    "corrected_entity": {
      "text": "art. 2043",
      "type": "Norma",
      "attributes": {
        "codice": "Codice Civile",
        "numero": "2043"
      }
    }
  }'
```

### Test 4: Verifica Statistiche

```bash
# Statistiche query
curl "http://localhost:8000/api/v1/stats/queries?days=7" | jq '.'

# Classifica authority
curl "http://localhost:8000/api/v1/stats/authority?limit=10" | jq '.'

# Stats RLCF
curl http://localhost:8001/stats | jq '.'
```

---

## 🔍 Cosa Vedrai Durante l'Esecuzione

### 1. Preprocessing Phase (2-3 secondi)

**Nel frontend** vedrai:
- 🔍 "Preprocessing query..."
- Entity extraction in corso
- Knowledge graph enrichment

**Nel terminale backend**:
```
INFO: Preprocessing query: "Cosa prevede l'art. 2043..."
INFO: NER extracted 3 entities: [Norma(2043), Codice(Civile), Concetto(responsabilità)]
INFO: KG enrichment found 5 sources
```

### 2. Routing Phase (1-2 secondi)

**Nel frontend**:
- 🧭 "Routing to retrieval agents..."
- Execution plan generato

**Nel terminale**:
```
INFO: LLM Router selected 2 agents: [VectorDBAgent, KGAgent]
INFO: Generated execution plan with 3 steps
```

### 3. Retrieval Phase (3-5 secondi)

**Nel frontend**:
- 📚 "Retrieving documents..."
- Agent results streaming

**Nel terminale**:
```
INFO: VectorDBAgent retrieved 10 documents (similarity > 0.75)
INFO: KGAgent traversed graph (depth=2), found 15 nodes
```

### 4. Reasoning Phase (10-15 secondi)

**Nel frontend**:
- 🤔 "Experts analyzing..."
- Progress bars per ogni esperto
- Opinioni che appaiono progressivamente

**Nel terminale**:
```
INFO: LiteralInterpreter analyzing... (8.2s)
INFO: SystemicTeleological analyzing... (12.5s)
INFO: PrinciplesBalancer analyzing... (10.1s)
INFO: PrecedentAnalyst analyzing... (11.3s)
```

### 5. Synthesis Phase (5-7 secondi)

**Nel frontend**:
- ✨ "Synthesizing final answer..."
- Synthesis result con provenance

**Nel terminale**:
```
INFO: Synthesizer aggregating 4 expert opinions
INFO: Shannon entropy: 0.32 (low disagreement)
INFO: Synthesis complete (6.8s)
```

---

## 🐛 Troubleshooting

### Problema: "Port already in use"

```bash
# Trova processo sulla porta 8000
lsof -ti:8000 | xargs kill -9

# Oppure cambia porta
uvicorn api.main:app --reload --port 8080
```

### Problema: "OpenRouter API key invalid"

```bash
# Verifica la tua key
echo $OPENROUTER_API_KEY

# Re-exporta se necessario
export OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY
```

### Problema: "Database connection failed"

```bash
# Se usi SQLite, assicurati che esista
ls -la merl_t.db

# Se non esiste, ricrea
rlcf-admin db migrate

# Se usi PostgreSQL via Docker
docker-compose -f docker-compose.dev.yml restart postgres
sleep 10
rlcf-admin db migrate
```

### Problema: "Module not found"

```bash
# Reinstalla dipendenze
source venv/bin/activate
pip install -e .

# Frontend
cd frontend/rlcf-web
npm install
```

### Problema: "Frontend non si connette al backend"

Verifica che:
1. Backend sia avviato su porta 8000
2. Nel browser console non ci siano errori CORS
3. `vite.config.ts` abbia il proxy corretto:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

### Problema: "Neo4j non si avvia"

```bash
# Controlla i log
docker logs merl-t-neo4j

# Ricrea il container
docker-compose -f docker-compose.dev.yml down
docker volume rm merl-t_neo4j-data
docker-compose -f docker-compose.dev.yml up -d neo4j
```

---

## 📝 Comandi Utili

### CLI Commands

```bash
# Task management
rlcf-cli tasks list --status OPEN --limit 20
rlcf-cli tasks create tasks.yaml
rlcf-cli tasks export 123 --format json -o task_123.json

# User management
rlcf-cli users create mario_rossi --authority-score 0.75
rlcf-cli users list --sort-by authority_score

# Admin commands
rlcf-admin config show --type model
rlcf-admin config validate
rlcf-admin db migrate
rlcf-admin db seed --users 10 --tasks 50
rlcf-admin db reset
rlcf-admin server --reload --port 8001
```

### Docker Commands

```bash
# Vedi tutti i container
docker-compose ps

# Vedi log di un servizio specifico
docker-compose logs -f backend

# Riavvia un servizio
docker-compose restart frontend

# Stop tutto
docker-compose down

# Stop e rimuovi volumi (attenzione: cancella i dati!)
docker-compose down -v

# Rebuild dopo modifiche al codice
docker-compose build
docker-compose up -d
```

### Database Commands

```bash
# PostgreSQL
docker exec -it merl-t-postgres psql -U merl_t -d merl_t_orchestration

# Queries utili
\dt                                    # Lista tabelle
SELECT COUNT(*) FROM queries;         # Conta query
SELECT * FROM queries LIMIT 10;       # Ultime 10 query
SELECT * FROM user_feedback;          # Vedi feedback

# Redis
docker exec -it merl-t-redis redis-cli
KEYS *                                # Vedi tutte le chiavi
GET query:status:abc123              # Vedi status query
FLUSHALL                             # Cancella tutto (attenzione!)

# Qdrant
curl http://localhost:6333/collections                        # Lista collezioni
curl http://localhost:6333/collections/legal_documents/points # Vedi punti

# Neo4j Cypher (browser http://localhost:7474)
MATCH (n) RETURN count(n);                    // Conta tutti i nodi
MATCH (n:Norma) RETURN n LIMIT 10;           // Prime 10 norme
MATCH (n:Norma {numero: "2043"}) RETURN n;   // Trova art. 2043
```

---

## 🎓 Prossimi Passi

Dopo aver completato questa guida, puoi:

1. **Esplorare la Documentazione**:
   - `docs/03-architecture/` - Architettura del sistema
   - `docs/api/API_EXAMPLES.md` - Esempi API avanzati
   - `docs/08-iteration/NEXT_STEPS.md` - Roadmap futura

2. **Contribuire al Progetto**:
   - Vedi `docs/07-guides/CONTRIBUTING.md`
   - Esegui test: `pytest tests/ -v`
   - Apri issue su GitHub

3. **Configurare per Production**:
   - Vedi `docs/07-guides/PRODUCTION_DEPLOYMENT.md`
   - Setup Kubernetes: `infrastructure/k8s/`
   - Monitoring: `infrastructure/monitoring/`

4. **Integrare con Altri Sistemi**:
   - API REST documentata in Swagger
   - WebSocket per real-time updates
   - SDK Python disponibile

---

## 📞 Supporto

**Problemi o Domande?**

- GitHub Issues: [Link al repository]
- Email: support@alis.org
- Discord: [Link community]
- Documentazione: `docs/`

**Debug Mode**:
```bash
# Abilita logging verbose
export LOG_LEVEL=DEBUG
uvicorn api.main:app --reload --log-level debug
```

---

**Buona esplorazione! 🚀**

*Questa guida è parte del progetto MERL-T v0.9.0*
*Ultimo aggiornamento: 15 Novembre 2025*
