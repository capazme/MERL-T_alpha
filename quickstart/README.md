# 🚀 MERL-T Quick Start Scripts

**Cartella di utility scripts per sviluppo rapido**

---

## 📁 Contenuto

| File | Descrizione |
|------|-------------|
| **start-dev.sh** | 🚀 Avvia l'intero sistema MERL-T |
| **stop-dev.sh** | 🛑 Ferma tutti i servizi |
| **restart-dev.sh** | 🔄 Riavvia il sistema |
| **test-system.sh** | 🧪 Test completi del sistema |
| **cleanup.sh** | 🧹 Pulizia leggera (cache e file di sessione) |
| **cleanup-hard.sh** | 💀 Pulizia completa (ELIMINA TUTTO: database, venv, node_modules) |
| **QUICK_START.md** | 📖 Guida rapida di avvio |
| **CHEATSHEET.md** | 📋 Comandi utili |

---

## 🚀 Script Principali

### 1. start-dev.sh - Avvio Sistema

**Cosa fa**:
- ✅ Verifica prerequisiti (Python 3.11+, Node 18+)
- ✅ Setup virtual environment
- ✅ Installazione dipendenze
- ✅ Inizializzazione database
- ✅ Avvio backend (porte 8000, 8001)
- ✅ Avvio frontend (porta 3000)
- ✅ Verifica health endpoints
- ✅ Apertura browser

**Uso**:
```bash
./quickstart/start-dev.sh
```

**Modalità di Avvio**:
1. **Rapido** - Solo SQLite (consigliato per iniziare)
2. **Docker** - PostgreSQL + Redis + Qdrant + Neo4j
3. **Manuale** - Configura a mano

**Output**:
- Log salvati in `logs/`
- PID files per ogni servizio
- Runtime info in `logs/runtime.info`

---

### 2. stop-dev.sh - Stop Sistema

**Cosa fa**:
- 🛑 Termina Backend Orchestration (porta 8000)
- 🛑 Termina Backend RLCF (porta 8001)
- 🛑 Termina Frontend (porta 3000)
- 🛑 Cleanup porte (fallback)
- 🛑 Stop Docker containers (opzionale)
- 🛑 Cancellazione log (opzionale)

**Uso**:
```bash
./quickstart/stop-dev.sh
```

**Opzioni Interattive**:
- Fermare anche Docker containers?
- Cancellare file di log?

---

### 3. restart-dev.sh - Riavvio Sistema

**Cosa fa**:
- Chiama `stop-dev.sh`
- Aspetta 3 secondi
- Chiama `start-dev.sh`

**Uso**:
```bash
./quickstart/restart-dev.sh
```

**Quando Usarlo**:
- Dopo modifiche al codice backend
- Dopo cambio configurazione
- Dopo update dipendenze

---

### 4. test-system.sh - Test Sistema

**Cosa fa**:
- ✓ Test health endpoints
- ✓ Test API endpoints
- ✓ Test query end-to-end (15 secondi)
- ✓ Test creazione task RLCF
- ✓ Verifica database connectivity
- ✓ Verifica configuration files
- ✓ Controlla errori nei log

**Uso**:
```bash
./quickstart/test-system.sh
```

**Output Esempio**:
```
[TEST] Verifica Health Endpoints
  ✓ PASS - Backend Orchestration health OK
  ✓ PASS - Backend RLCF health OK
  ✓ PASS - Frontend responding OK

[TEST] Verifica API Endpoints
  ✓ PASS - GET /api/v1/queries OK
  ✓ PASS - GET /api/v1/stats/queries OK

...

✓ TUTTI I TEST PASSATI! 🎉
```

**Exit Code**:
- `0` - Tutti i test passati
- `1` - Uno o più test falliti

---

### 5. cleanup.sh - Pulizia Sistema

**⚠️ ATTENZIONE**: Operazione IRREVERSIBILE!

**Cosa Rimuove**:

| Categoria | File/Directory |
|-----------|----------------|
| **Database** | `merl_t.db`, `*.db-shm`, `*.db-wal` |
| **Log** | `logs/*.log`, `logs/*.pid`, `logs/runtime.info` |
| **Cache Python** | `__pycache__/`, `*.pyc`, `*.pyo` |
| **Cache Vite** | `node_modules/.vite/` |
| **Temp Files** | `.DS_Store`, `*~`, `*.swp` |
| **Coverage** | `htmlcov/`, `.coverage` |
| **Pytest** | `.pytest_cache/` |

**Cosa NON Rimuove (default)**:
- ✅ Codice sorgente
- ✅ File `.env` (configurazione)
- ✅ `venv/` (virtual environment)
- ✅ `node_modules/`
- ✅ Docker volumes

**Uso**:
```bash
./quickstart/cleanup.sh
```

**Opzioni Interattive**:
1. Conferma cleanup (digita `YES`)
2. Fermare container Docker? [y/N]
3. Rimuovere volumi Docker? [y/N]
4. Rimuovere immagini orfane? [y/N]
5. Rimuovere virtual environment? [y/N]
6. Rimuovere node_modules? [y/N]
7. Rimuovere .env? [y/N] ⚠️ **ATTENZIONE!**

**Output**:
- Report salvato in `logs/cleanup_report_TIMESTAMP.txt`
- Backup `.env` in `backups/` (se rimosso)

**Quando Usarlo**:
- Prima di committare (pulizia repo)
- Reset completo per testing
- Riportare allo stato "post-clone"
- Liberare spazio disco

---

## 📖 Documentazione

### QUICK_START.md

Guida rapida con:
- ⚡ Avvio rapido (3 minuti)
- 🎯 Primi test
- 🛠️ Comandi utili
- 📁 Struttura progetto
- 🔧 Modalità di avvio
- 🐛 Problemi comuni
- 🎓 Prossimi passi

**Quando Leggerlo**: Prima di avviare il sistema la prima volta

### CHEATSHEET.md

Riferimento veloce con:
- 🚀 Gestione sistema
- 🌐 URL principali
- 🗄️ Comandi database
- 🔧 CLI admin/utente
- 📡 API calls (curl)
- 🐳 Docker
- 📊 Log e debug
- 🧪 Testing
- 🎯 Quick workflows

**Quando Usarlo**: Tieni aperto durante lo sviluppo!

---

## 🔄 Workflow Tipici

### Prima Volta (Setup Iniziale)

```bash
# 1. Configura .env
cp .env.template .env
nano .env  # Aggiungi OPENROUTER_API_KEY

# 2. Avvia sistema
./quickstart/start-dev.sh

# 3. Test
./quickstart/test-system.sh

# 4. Apri browser
open http://localhost:3000
```

### Sviluppo Quotidiano

```bash
# Mattina - Avvia
./quickstart/start-dev.sh

# Durante la giornata - Monitor log
tail -f logs/*.log

# Dopo modifiche - Riavvia
./quickstart/restart-dev.sh

# Fine giornata - Stop
./quickstart/stop-dev.sh
```

### Debug di un Problema

```bash
# 1. Verifica servizi
./quickstart/test-system.sh

# 2. Controlla log
grep -i "error" logs/*.log

# 3. Riavvia pulito
./quickstart/stop-dev.sh
sleep 3
./quickstart/start-dev.sh

# 4. Test specifico
curl http://localhost:8000/health
```

### Pulizia Prima di Commit

```bash
# 1. Stop tutto
./quickstart/stop-dev.sh

# 2. Cleanup
./quickstart/cleanup.sh
# Scegli: NO a venv, NO a node_modules, NO a .env

# 3. Test che funzioni ancora
./quickstart/start-dev.sh
./quickstart/test-system.sh

# 4. Commit
git add .
git commit -m "feature: ..."
```

### Reset Completo

```bash
# 1. Cleanup totale
./quickstart/cleanup.sh
# Scegli: YES a tutto (tranne .env)

# 2. Reinstalla dipendenze
python3 -m venv venv
source venv/bin/activate
pip install -e .

cd frontend/rlcf-web
npm install
cd ../..

# 3. Riavvia
./quickstart/start-dev.sh
```

---

## 🎨 Personalizzazione

### Modificare Porte

Modifica direttamente negli script:

**start-dev.sh**:
```bash
# Linee 180-200 circa
uvicorn api.main:app --reload --port 8000  # Cambia 8000
uvicorn main:app --reload --port 8001      # Cambia 8001
npm run dev                                 # Porta 3000 in vite.config.ts
```

### Aggiungere Controlli Custom

**test-system.sh**:
```bash
# Dopo Test 7, aggiungi:

# ============================================================================
# Test 8: Custom Test
# ============================================================================

print_test "Il Mio Test Custom"

if [ -f "mio_file.txt" ]; then
    print_pass "File custom trovato"
else
    print_fail "File custom mancante"
fi
```

### Escludere File dal Cleanup

**cleanup.sh**:
```bash
# Nella sezione rimozione log (linea ~200)
if [ -d "logs" ]; then
    # Escludi un file specifico
    find logs -type f ! -name "important.log" -delete
    print_success "Log rimossi (escluso important.log)"
fi
```

---

## 🐛 Troubleshooting Scripts

### "Permission denied"

```bash
# Rendi eseguibili
chmod +x quickstart/*.sh
```

### "Command not found: bc"

Il comando `bc` è usato per comparazioni di versioni. Installalo:

```bash
# macOS
brew install bc

# Linux
sudo apt-get install bc
```

### Script si blocca

Premi `Ctrl+C` per interrompere, poi:

```bash
# Cleanup manuale
killall -9 python3 node
./quickstart/stop-dev.sh
```

### "Docker not found"

Se non usi Docker, scegli sempre modalità "Rapido" (1) in `start-dev.sh`

---

## 📊 Log e Output

### Log Files

Tutti i log sono salvati in `logs/`:

```
logs/
├── orchestration.log    # Backend Orchestration
├── rlcf.log             # Backend RLCF
├── frontend.log         # Frontend React
├── orchestration.pid    # PID del processo
├── rlcf.pid
├── frontend.pid
├── runtime.info         # Info di runtime
├── test_query_result.json         # Risultato test query
└── cleanup_report_TIMESTAMP.txt   # Report cleanup
```

### Visualizzare Log in Tempo Reale

```bash
# Tutti insieme
tail -f logs/*.log

# Singolo servizio
tail -f logs/orchestration.log

# Con colori (se hai bat)
bat --paging=never logs/orchestration.log -f
```

### Cercare Errori

```bash
# Tutti gli errori
grep -i "error" logs/*.log

# Errori oggi
grep -i "error" logs/*.log | grep "$(date +%Y-%m-%d)"

# Conta errori
grep -c "ERROR" logs/orchestration.log
```

---

## 🔗 Link Rapidi

Quando il sistema è avviato:

- 🌐 **Frontend**: http://localhost:3000
- 📡 **Orchestration API**: http://localhost:8000/docs
- 🤖 **RLCF API**: http://localhost:8001/docs
- 💚 **Health Orchestration**: http://localhost:8000/health
- 💚 **Health RLCF**: http://localhost:8001/health

Se usi Docker:
- 🐘 **PostgreSQL**: localhost:5432
- 🔴 **Redis**: localhost:6379
- 🔍 **Qdrant**: http://localhost:6333/dashboard
- 🕸️ **Neo4j**: http://localhost:7474

---

## 💡 Tips & Tricks

### Alias Utili

Aggiungi al tuo `~/.bashrc` o `~/.zshrc`:

```bash
# MERL-T aliases
alias merl-start='cd ~/Desktop/CODE/MERL-T_alpha && ./quickstart/start-dev.sh'
alias merl-stop='cd ~/Desktop/CODE/MERL-T_alpha && ./quickstart/stop-dev.sh'
alias merl-test='cd ~/Desktop/CODE/MERL-T_alpha && ./quickstart/test-system.sh'
alias merl-logs='cd ~/Desktop/CODE/MERL-T_alpha && tail -f logs/*.log'
alias merl='cd ~/Desktop/CODE/MERL-T_alpha'
```

Poi:
```bash
merl-start    # Da ovunque!
```

### Auto-Avvio al Login (macOS)

Crea un file `~/Library/LaunchAgents/com.merl-t.startup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.merl-t.startup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/TUO_USERNAME/Desktop/CODE/MERL-T_alpha/quickstart/start-dev.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

### Integrazione IDE

**VS Code** - Aggiungi tasks (`.vscode/tasks.json`):

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "MERL-T: Start",
      "type": "shell",
      "command": "./quickstart/start-dev.sh"
    },
    {
      "label": "MERL-T: Stop",
      "type": "shell",
      "command": "./quickstart/stop-dev.sh"
    },
    {
      "label": "MERL-T: Test",
      "type": "shell",
      "command": "./quickstart/test-system.sh"
    }
  ]
}
```

Poi: `Cmd+Shift+P` → "Tasks: Run Task" → "MERL-T: Start"

---

## 📞 Supporto

**Problemi con gli script?**

1. Controlla log: `cat logs/*.log`
2. Verifica permessi: `ls -la quickstart/`
3. Reinstalla dipendenze: `pip install -e . && npm install`
4. Consulta `QUICK_START.md` sezione Troubleshooting

**Documentazione Completa**:
- `../docs/07-guides/PRIMA_ACCENSIONE.md` - Guida completa (70+ KB!)
- `../docs/api/API_EXAMPLES.md` - Esempi API
- `../docs/03-architecture/` - Architettura sistema

---

**Happy Coding! 🚀**

*MERL-T v0.9.0 - Quick Start Scripts*
*Ultimo aggiornamento: 15 Novembre 2025*
