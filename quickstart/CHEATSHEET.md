# 📋 MERL-T Command Cheatsheet

**Quick reference** per i comandi più usati

---

## 🚀 Gestione Sistema

```bash
# Avvio
./start-dev.sh              # Avvia tutto (interattivo)
./stop-dev.sh               # Ferma tutto
./restart-dev.sh            # Riavvia tutto
./test-system.sh            # Test completi

# Alternativa manuale
cd backend/orchestration && uvicorn api.main:app --reload --port 8000
cd backend/rlcf_framework && uvicorn main:app --reload --port 8001
cd frontend/rlcf-web && npm run dev
```

## 🌐 URL Principali

```
http://localhost:3000           # Frontend React
http://localhost:8000/docs      # Orchestration API (Swagger)
http://localhost:8001/docs      # RLCF API (Swagger)
http://localhost:8000/health    # Health check orchestration
http://localhost:8001/health    # Health check RLCF
```

## 🗄️ Database

```bash
# SQLite (modalità rapida)
rlcf-admin db migrate                    # Crea tabelle
rlcf-admin db seed --users 5 --tasks 10  # Popola dati esempio
sqlite3 merl_t.db ".tables"              # Lista tabelle
sqlite3 merl_t.db "SELECT COUNT(*) FROM queries;"

# PostgreSQL (Docker)
docker exec -it merl-t-postgres psql -U merl_t -d merl_t_orchestration
\dt                                       # Lista tabelle
SELECT * FROM queries LIMIT 5;           # Prime 5 query

# Redis
docker exec -it merl-t-redis redis-cli
KEYS *                                    # Tutte le chiavi
GET query:status:abc123                  # Vedi status query
FLUSHALL                                 # Cancella tutto

# Qdrant
curl http://localhost:6333/collections   # Lista collezioni

# Neo4j
open http://localhost:7474               # Browser UI
# Login: neo4j / your-password
```

## 🔧 CLI Admin

```bash
source venv/bin/activate    # Attiva venv (necessario!)

# Database
rlcf-admin db migrate
rlcf-admin db seed --users 10 --tasks 50
rlcf-admin db reset         # ⚠️ CANCELLA TUTTO

# Config
rlcf-admin config show --type model
rlcf-admin config show --type tasks
rlcf-admin config validate

# Server
rlcf-admin server                        # Avvia RLCF server
rlcf-admin server --reload --port 8001   # Con hot-reload
```

## 👤 CLI Utente

```bash
# Tasks
rlcf-cli tasks list                       # Lista tutti
rlcf-cli tasks list --status OPEN         # Solo aperti
rlcf-cli tasks list --limit 20            # Primi 20
rlcf-cli tasks create tasks.yaml          # Crea da file
rlcf-cli tasks export 123 -o task.json    # Esporta task

# Users
rlcf-cli users list                       # Lista esperti
rlcf-cli users list --sort-by authority   # Ordina per authority
rlcf-cli users create mario_rossi         # Crea utente
```

## 📡 API Calls (curl)

### Orchestration API (porta 8000)

```bash
API_KEY="dev-admin-key-12345"

# 1. Invia query
curl -X POST http://localhost:8000/api/v1/queries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "query_text": "Cosa prevede l'\''art. 2043 del Codice Civile?",
    "context": {"domain": "civil_law", "jurisdiction": "italy"}
  }'

# 2. Ottieni risultato
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/queries/QUERY_ID

# 3. Ottieni execution trace
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/queries/QUERY_ID/trace

# 4. Invia feedback utente
curl -X POST http://localhost:8000/api/v1/feedback/user \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "trace_id": "QUERY_ID",
    "rating": 5,
    "feedback_text": "Ottima risposta!"
  }'

# 5. Statistiche
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/stats/queries?days=7"

curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/stats/authority?limit=10"
```

### RLCF API (porta 8001)

```bash
# 1. Crea task
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "classification",
    "input_data": {
      "text": "Il venditore deve consegnare la cosa...",
      "domain": "civil_law",
      "options": ["contract_law", "tort_law"]
    },
    "ground_truth": {
      "correct_class": "contract_law",
      "confidence": 0.95
    }
  }'

# 2. Lista task
curl http://localhost:8001/tasks

# 3. Ottieni task specifico
curl http://localhost:8001/tasks/TASK_ID

# 4. Valuta task (come esperto)
curl -X POST http://localhost:8001/tasks/TASK_ID/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": USER_ID,
    "response_data": {
      "selected_class": "contract_law",
      "confidence": 0.9,
      "explanation": "Obblighi del venditore = contract law"
    }
  }'

# 5. Ottieni consenso
curl http://localhost:8001/tasks/TASK_ID/consensus

# 6. Authority score utente
curl http://localhost:8001/users/USER_ID/authority
```

## 🐳 Docker

```bash
# Avvia tutti i servizi
docker-compose -f docker-compose.dev.yml up -d

# Stop tutti
docker-compose -f docker-compose.dev.yml down

# Stop + cancella volumi (⚠️ DATI PERSI)
docker-compose -f docker-compose.dev.yml down -v

# Vedi log
docker-compose logs -f                 # Tutti
docker-compose logs -f postgres        # Solo postgres
docker-compose logs --tail=100 backend # Ultimi 100 righe

# Status
docker-compose ps

# Riavvia servizio
docker-compose restart postgres

# Rebuild
docker-compose build
docker-compose up -d
```

## 📊 Log e Debug

```bash
# Log in tempo reale
tail -f logs/orchestration.log
tail -f logs/rlcf.log
tail -f logs/frontend.log
tail -f logs/*.log              # Tutti insieme

# Log con colori (se hai bat installato)
bat logs/orchestration.log

# Cerca errori
grep -i "error" logs/*.log
grep -i "exception" logs/*.log

# Conta errori
grep -c "ERROR" logs/orchestration.log

# Log debug (abilita prima)
export LOG_LEVEL=DEBUG
uvicorn api.main:app --reload --log-level debug
```

## 🔍 Verifica Sistema

```bash
# Health check
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:3000

# Porte occupate
lsof -i :3000
lsof -i :8000
lsof -i :8001

# Termina processo su porta
lsof -ti:8000 | xargs kill -9

# Processi Python/Node
ps aux | grep uvicorn
ps aux | grep node

# Versioni
python3 --version
node --version
npm --version
docker --version
```

## 🧹 Cleanup

```bash
# Cancella cache Python
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Cancella cache Vite
rm -rf frontend/rlcf-web/node_modules/.vite

# Cancella log
rm -f logs/*.log
rm -f logs/*.pid

# Cancella database SQLite (⚠️)
rm merl_t.db

# Reinstalla dipendenze Python
pip install -e . --force-reinstall

# Reinstalla dipendenze Node
cd frontend/rlcf-web
rm -rf node_modules package-lock.json
npm install
```

## 🧪 Testing

```bash
# Test completi
pytest tests/ -v

# Test specifici
pytest tests/rlcf/ -v
pytest tests/orchestration/ -v
pytest tests/preprocessing/ -v

# Con coverage
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html

# Singolo file
pytest tests/orchestration/test_llm_router.py -v

# Test solo su un pattern
pytest tests/ -k "test_authority" -v
```

## ⚙️ Environment Variables

```bash
# File .env principale
export OPENROUTER_API_KEY=sk-or-v1-...
export DATABASE_URL=sqlite+aiosqlite:///./merl_t.db
export REDIS_URL=redis://localhost:6379

# Per session corrente
export LOG_LEVEL=DEBUG
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Vedi tutte le variabili
cat .env
```

## 📦 Dependency Management

```bash
# Python
pip list                        # Vedi pacchetti installati
pip freeze > requirements.txt   # Esporta dipendenze
pip install -r requirements.txt # Installa da file

# Node.js
npm list                        # Albero dipendenze
npm outdated                    # Vedi pacchetti obsoleti
npm update                      # Aggiorna pacchetti
npm audit                       # Controlla vulnerabilità
npm audit fix                   # Fixa vulnerabilità
```

## 🎯 Quick Workflows

### Nuovo Sviluppatore (First Time Setup)

```bash
git clone <repo> MERL-T_alpha
cd MERL-T_alpha
cp .env.template .env
nano .env  # Configura OPENROUTER_API_KEY
./start-dev.sh
open http://localhost:3000
```

### Sviluppo Quotidiano

```bash
cd MERL-T_alpha
./start-dev.sh                # Avvia
# ... lavora ...
./stop-dev.sh                 # Stop a fine giornata
```

### Debug di un Errore

```bash
tail -f logs/*.log            # Monitor log
grep -i "error" logs/*.log    # Trova errori
curl http://localhost:8000/health  # Verifica servizi
./test-system.sh              # Test completi
```

### Dopo Modifiche al Codice

```bash
./restart-dev.sh              # Riavvia tutto
# Oppure solo il servizio modificato
docker-compose restart backend
```

---

## 🔗 Link Utili

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **RLCF Docs**: http://localhost:8001/docs
- **Neo4j**: http://localhost:7474
- **Qdrant**: http://localhost:6333/dashboard

---

## 📚 Documentazione

```bash
# Guide
cat docs/07-guides/PRIMA_ACCENSIONE.md
cat docs/07-guides/LOCAL_SETUP.md
cat QUICK_START.md

# Architettura
ls docs/03-architecture/

# API
cat docs/api/API_EXAMPLES.md
cat docs/api/AUTHENTICATION.md

# Next Steps
cat docs/08-iteration/NEXT_STEPS.md
```

---

**Stampa questo cheatsheet e tienilo a portata di mano!** 📋

*MERL-T v0.9.0 - Per supporto vedi QUICK_START.md*
