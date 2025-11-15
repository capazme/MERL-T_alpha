# 🚀 MERL-T Quick Start

**Versione Sistema**: v0.9.0 (82% completo - Production Ready)

---

## ⚡ Avvio Rapido (3 minuti)

### 1. **Prima Configurazione** (solo la prima volta)

```bash
# 1. Clona il repository (se non l'hai già fatto)
git clone <repo-url> MERL-T_alpha
cd MERL-T_alpha

# 2. Copia il template delle variabili ambiente
cp .env.template .env

# 3. Configura la tua OpenRouter API key
nano .env  # Modifica OPENROUTER_API_KEY
```

**⚠️ IMPORTANTE**: Ottieni la tua API key gratuita da https://openrouter.ai/

### 2. **Avvia il Sistema**

```bash
# Avvia tutto con un solo comando!
./start-dev.sh
```

Lo script ti guiderà attraverso:
- ✅ Verifica prerequisiti (Python 3.11+, Node.js 18+)
- ✅ Setup virtual environment
- ✅ Installazione dipendenze
- ✅ Inizializzazione database
- ✅ Avvio di tutti i servizi

**Tempo stimato**: 2-3 minuti

### 3. **Accedi all'Interfaccia**

Apri il browser su:

- 🌐 **Frontend**: http://localhost:3000
- 📡 **Orchestration API**: http://localhost:8000/docs
- 🤖 **RLCF API**: http://localhost:8001/docs

---

## 🎯 Primi Test

### Test Automatico del Sistema

```bash
# Esegui test completi
./test-system.sh
```

Questo script verifica:
- ✓ Health endpoints
- ✓ API endpoints
- ✓ Query end-to-end
- ✓ Creazione task RLCF
- ✓ Database connectivity
- ✓ Configuration files

### Test Manuale - Query Legale

**Nell'interfaccia web** (http://localhost:3000/query):

1. Inserisci una domanda legale, ad esempio:
   ```
   Quali sono gli obblighi del venditore secondo l'art. 1476 del Codice Civile?
   ```

2. Clicca "Invia Query"

3. Osserva il workflow in tempo reale:
   - 🔍 Preprocessing (NER + KG enrichment)
   - 🧭 Routing (selezione agenti)
   - 📚 Retrieval (documenti rilevanti)
   - 🤔 Reasoning (4 esperti analizzano)
   - ✨ Synthesis (risposta finale)

**Via API** (alternativa):

```bash
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

---

## 🛠️ Comandi Utili

### Gestione Servizi

```bash
./start-dev.sh        # Avvia tutto
./stop-dev.sh         # Ferma tutto
./restart-dev.sh      # Riavvia tutto
./test-system.sh      # Test completi
```

### Log e Debug

```bash
# Vedi log in tempo reale
tail -f logs/orchestration.log   # Backend Orchestration
tail -f logs/rlcf.log             # Backend RLCF
tail -f logs/frontend.log         # Frontend React

# Vedi tutti i log insieme
tail -f logs/*.log
```

### CLI Tools

```bash
# Attiva virtual environment
source venv/bin/activate

# Comandi admin
rlcf-admin --help                           # Help generale
rlcf-admin db migrate                       # Migrazioni DB
rlcf-admin db seed --users 10 --tasks 50    # Popola DB
rlcf-admin config show --type model         # Mostra config

# Comandi utente
rlcf-cli tasks list --status OPEN           # Lista task aperti
rlcf-cli users list --sort-by authority     # Lista esperti
```

---

## 📁 Struttura del Progetto

```
MERL-T_alpha/
├── backend/
│   ├── orchestration/       # API orchestrazione (porta 8000)
│   ├── rlcf_framework/      # API RLCF (porta 8001)
│   └── preprocessing/       # Query understanding + KG
├── frontend/
│   └── rlcf-web/            # React 19 app (porta 3000)
├── docs/
│   ├── 07-guides/
│   │   └── PRIMA_ACCENSIONE.md   # Guida completa (LEGGI QUESTA!)
│   ├── api/
│   │   └── API_EXAMPLES.md       # Esempi API avanzati
│   └── 03-architecture/          # Architettura dettagliata
├── logs/                    # Log di runtime
├── .env                     # Configurazione (DA CREARE!)
├── start-dev.sh             # 🚀 Script di avvio
├── stop-dev.sh              # 🛑 Script di stop
├── restart-dev.sh           # 🔄 Script di riavvio
└── test-system.sh           # 🧪 Script di test
```

---

## 🔧 Modalità di Avvio

### Modalità 1: Rapido (Consigliata per iniziare)

- **Database**: SQLite (file locale `merl_t.db`)
- **Cache**: In-memory (no Redis)
- **Vettori**: In-memory (no Qdrant)
- **Grafo**: Disabilitato (no Neo4j)

**Pro**: Setup velocissimo, zero configurazione
**Contro**: Prestazioni limitate, no persistenza cache

### Modalità 2: Docker Completo

- **Database**: PostgreSQL (container)
- **Cache**: Redis (container)
- **Vettori**: Qdrant (container)
- **Grafo**: Neo4j (container)

**Pro**: Environment completo, prestazioni ottimali
**Contro**: Richiede Docker, setup più lungo

**Avvio**:
```bash
# 1. Avvia database Docker
docker-compose -f docker-compose.dev.yml up -d

# 2. Avvia backend e frontend
./start-dev.sh
```

---

## 📖 Documentazione Completa

Per una guida dettagliata, consulta:

### 📘 **Guida Completa di Prima Accensione**
```bash
cat docs/07-guides/PRIMA_ACCENSIONE.md
```

Questa guida include:
- ✅ Prerequisiti dettagliati
- ✅ Setup passo-passo
- ✅ Spiegazione di cosa succede durante l'esecuzione
- ✅ Test delle funzionalità
- ✅ Troubleshooting completo
- ✅ Comandi avanzati

### 🏗️ **Architettura del Sistema**
```bash
ls docs/03-architecture/
```

- `01-preprocessing-layer.md` - NER, intent classification, KG enrichment
- `02-orchestration-layer.md` - LLM Router, agenti, LangGraph
- `03-reasoning-layer.md` - 4 esperti legali + synthesis
- `04-storage-layer.md` - PostgreSQL, Qdrant, Neo4j, Redis
- `05-learning-layer.md` - RLCF feedback loops

### 🔌 **API Examples**
```bash
cat docs/api/API_EXAMPLES.md
```

Esempi pratici per:
- Invio query
- Feedback utente
- Feedback RLCF
- Correzioni NER
- Statistiche

---

## 🐛 Problemi Comuni

### "Port already in use"

```bash
# Termina processi sulle porte
./stop-dev.sh

# O manualmente
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### "OPENROUTER_API_KEY not configured"

```bash
# Modifica .env
nano .env

# Aggiungi:
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE
```

### "Database connection failed"

```bash
# Se SQLite
rlcf-admin db migrate

# Se PostgreSQL Docker
docker-compose -f docker-compose.dev.yml restart postgres
sleep 10
rlcf-admin db migrate
```

### "Module not found"

```bash
# Reinstalla dipendenze
source venv/bin/activate
pip install -e .

# Frontend
cd frontend/rlcf-web
npm install
```

---

## 🎓 Prossimi Passi

Dopo aver avviato il sistema:

1. **Esplora l'Interfaccia Web**
   - Prova a inviare domande legali diverse
   - Visualizza le execution traces
   - Esplora il pannello Admin

2. **Testa le API**
   - Apri Swagger UI (http://localhost:8000/docs)
   - Prova gli endpoint interattivamente
   - Leggi `docs/api/API_EXAMPLES.md`

3. **Configura RLCF**
   - Vai su http://localhost:3000/admin
   - Modifica authority weights
   - Crea task di valutazione

4. **Leggi la Documentazione**
   - `docs/02-methodology/rlcf/RLCF.md` - Core theory
   - `docs/08-iteration/NEXT_STEPS.md` - Roadmap
   - `docs/IMPLEMENTATION_ROADMAP.md` - Piano completo

---

## 💡 Tips

- **Primo avvio lento?** È normale, Vite deve compilare. Successivi reload sono istantanei.
- **Query lente?** Le prime chiamate LLM richiedono 10-15 secondi. È normale.
- **Errori nei log?** Controlla `logs/*.log` per dettagli.
- **Serve aiuto?** Consulta `docs/07-guides/PRIMA_ACCENSIONE.md` (80+ KB di guida!)

---

## 📞 Supporto

**Problemi o Domande?**

- 📧 Email: support@alis.org
- 📖 Docs: `docs/`
- 🐛 Issues: GitHub Issues

---

**Buona esplorazione! 🚀**

*MERL-T v0.9.0 - Multi-Expert Legal Retrieval Transformer*
*Sponsorizzato da ALIS (Artificial Legal Intelligence Society)*
