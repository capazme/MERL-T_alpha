#!/bin/bash

# ============================================================================
# MERL-T Development Environment Startup Script
# ============================================================================
# Versione: 1.0
# Data: 15 Novembre 2025
# Descrizione: Avvia l'intero sistema MERL-T in modalità sviluppo
# ============================================================================

set -e  # Exit on error

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    🚀  MERL-T Development Environment Startup Script      ║
║                                                           ║
║    Multi-Expert Legal Retrieval Transformer               ║
║    Version: 0.9.0 (82% Complete - Production Ready)      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================================
# Funzioni di Utility
# ============================================================================

print_step() {
    echo -e "\n${BLUE}==>${NC} ${MAGENTA}$1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 non trovato. Installalo e riprova."
        exit 1
    fi
    print_success "$1 trovato"
}

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "Porta $1 già in uso. Vuoi terminare il processo? [y/N]"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            lsof -ti:$1 | xargs kill -9
            print_success "Processo sulla porta $1 terminato"
        else
            print_error "Impossibile procedere con porta $1 occupata"
            exit 1
        fi
    fi
}

# ============================================================================
# 1. Verifica Prerequisiti
# ============================================================================

print_step "1. Verifica Prerequisiti"

# Verifica Node.js
check_command node
check_command npm

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if (( NODE_VERSION < 18 )); then
    print_error "Node.js 18+ richiesto. Versione attuale: v$NODE_VERSION"
    exit 1
fi
print_success "Node.js v$NODE_VERSION OK"

# Trova la versione corretta di Python (3.11-3.13)
PYTHON_CMD=""
PYTHON_VERSION=""

# Prova in ordine: 3.13, 3.12, 3.11
for version in 3.13 3.12 3.11; do
    if command -v python$version &> /dev/null; then
        PYTHON_CMD="python$version"
        PYTHON_VERSION=$version
        break
    fi
done

# Fallback a python3 generico se nessuna versione specifica è trovata
if [ -z "$PYTHON_CMD" ] && command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)

    # Verifica che sia 3.11-3.13
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" -lt 11 ] || [ "$PYTHON_MINOR" -gt 13 ]; then
        print_error "Python 3.11-3.13 richiesto. Versione trovata: $PYTHON_VERSION"
        print_warning "Installa Python 3.13: brew install python@3.13"
        exit 1
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python 3.11-3.13 non trovato"
    print_warning "Installa Python 3.13: brew install python@3.13"
    exit 1
fi

print_success "Python $PYTHON_VERSION OK (comando: $PYTHON_CMD)"

# ============================================================================
# 2. Modalità di Avvio
# ============================================================================

print_step "2. Selezione Modalità"

echo "Seleziona la modalità di avvio:"
echo "  1) 🚀 Rapido - Solo SQLite (consigliato per iniziare)"
echo "  2) 🐳 Docker - PostgreSQL + Redis + Qdrant + Neo4j"
echo "  3) 💻 Manuale - Configura tutto a mano"
echo ""
read -p "Scegli modalità [1-3]: " mode

# ============================================================================
# 3. Verifica File di Configurazione
# ============================================================================

print_step "3. Verifica Configurazione"

if [ ! -f ".env" ]; then
    print_warning "File .env non trovato. Vuoi crearlo dal template? [Y/n]"
    read -r response
    if [[ "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        print_error "File .env richiesto. Crealo manualmente da .env.template"
        exit 1
    fi
    cp .env.template .env
    print_success ".env creato"
    print_warning "⚠️  IMPORTANTE: Configura OPENROUTER_API_KEY in .env prima di continuare!"
    echo "Premi INVIO dopo aver configurato .env..."
    read
fi

# Verifica OPENROUTER_API_KEY
source .env
if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "sk-or-YOUR-KEY-HERE" ]; then
    print_error "OPENROUTER_API_KEY non configurata in .env"
    print_warning "Ottienila da https://openrouter.ai/"
    exit 1
fi
print_success "OPENROUTER_API_KEY configurata"

# ============================================================================
# 4. Setup Virtual Environment
# ============================================================================

print_step "4. Setup Python Virtual Environment"

if [ ! -d "venv" ]; then
    print_warning "Virtual environment non trovato. Creazione in corso con $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment creato"
elif [ -f "venv/bin/python" ]; then
    # Verifica che il venv usi una versione compatibile
    VENV_VERSION=$(venv/bin/python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    VENV_MINOR=$(echo $VENV_VERSION | cut -d'.' -f2)
    if [ "$VENV_MINOR" -gt 13 ]; then
        print_warning "Virtual environment usa Python $VENV_VERSION (non supportato). Ricreazione..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment ricreato con $PYTHON_CMD"
    fi
fi

source venv/bin/activate
print_success "Virtual environment attivato (Python $PYTHON_VERSION)"

# Installa/Aggiorna dipendenze
print_warning "Installazione dipendenze Python (può richiedere qualche minuto)..."
pip install -q --upgrade pip setuptools wheel
pip install -q -e .
print_success "Dipendenze Python installate"

# ============================================================================
# 5. Setup Frontend
# ============================================================================

print_step "5. Setup Frontend"

cd frontend/rlcf-web

if [ ! -d "node_modules" ]; then
    print_warning "node_modules non trovato. Installazione in corso..."
    npm install
    print_success "Dipendenze Node.js installate"
else
    print_success "node_modules già presente"
fi

cd ../..

# ============================================================================
# 6. Inizializzazione Database
# ============================================================================

print_step "6. Inizializzazione Database"

if [ "$mode" = "1" ]; then
    # Modalità SQLite
    export DATABASE_URL="sqlite+aiosqlite:///./merl_t.db"

    if [ ! -f "merl_t.db" ]; then
        print_warning "Database SQLite non trovato. Creazione in corso..."
        rlcf-admin db migrate
        print_success "Database creato"

        print_warning "Vuoi popolare il database con dati di esempio? [Y/n]"
        read -r response
        if [[ ! "$response" =~ ^([nN][oO]|[nN])$ ]]; then
            rlcf-admin db seed --users 5 --tasks 10
            print_success "Database popolato"
        fi
    else
        print_success "Database SQLite già presente"
    fi

elif [ "$mode" = "2" ]; then
    # Modalità Docker
    check_command docker
    check_command docker-compose

    print_warning "Avvio database con Docker Compose..."
    docker-compose -f docker-compose.dev.yml up -d
    print_success "Database Docker avviati"

    print_warning "Attesa 15 secondi per l'inizializzazione dei database..."
    sleep 15

    export DATABASE_URL="postgresql+asyncpg://merl_t:merl_t_password@localhost/merl_t_orchestration"
    export REDIS_URL="redis://localhost:6379"
    export QDRANT_HOST="localhost"
    export QDRANT_PORT="6333"
    export NEO4J_URI="bolt://localhost:7687"

    # Migrazioni
    rlcf-admin db migrate || print_warning "Migrazioni già eseguite"

    print_warning "Vuoi popolare il database con dati di esempio? [Y/n]"
    read -r response
    if [[ ! "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        rlcf-admin db seed --users 5 --tasks 10
        print_success "Database popolato"
    fi
fi

# ============================================================================
# 7. Verifica Porte
# ============================================================================

print_step "7. Verifica Porte Disponibili"

check_port 3000  # Frontend
check_port 5000  # visualex
check_port 8000  # Backend Orchestration
check_port 8001  # Backend RLCF
check_port 8002  # Ingestion API

print_success "Tutte le porte sono disponibili"

# ============================================================================
# 8. Avvio Servizi
# ============================================================================

print_step "8. Avvio Servizi"

# Directory per i log
mkdir -p logs

# Avvia visualex (richiesto per KG ingestion) in background
print_warning "Avvio visualex API (porta 5000)..."
cd visualex
nohup python app.py > ../logs/visualex.log 2>&1 &
VISUALEX_PID=$!
echo $VISUALEX_PID > ../logs/visualex.pid
cd ..
print_success "visualex API avviato (PID: $VISUALEX_PID)"

# Aspetta che si avvii
sleep 3

# Avvia Backend Orchestration in background
print_warning "Avvio Backend Orchestration API (porta 8000)..."
cd backend/orchestration
nohup uvicorn api.main:app --reload --port 8000 > ../../logs/orchestration.log 2>&1 &
ORCHESTRATION_PID=$!
echo $ORCHESTRATION_PID > ../../logs/orchestration.pid
cd ../..
print_success "Backend Orchestration avviato (PID: $ORCHESTRATION_PID)"

# Aspetta che si avvii
sleep 3

# Avvia Backend RLCF in background
print_warning "Avvio Backend RLCF API (porta 8001)..."
cd backend/rlcf_framework
nohup uvicorn main:app --reload --port 8001 > ../../logs/rlcf.log 2>&1 &
RLCF_PID=$!
echo $RLCF_PID > ../../logs/rlcf.pid
cd ../..
print_success "Backend RLCF avviato (PID: $RLCF_PID)"

# Aspetta che si avvii
sleep 3

# Avvia Ingestion API in background
print_warning "Avvio KG Ingestion API (porta 8002)..."
cd backend/preprocessing/api
nohup python main.py > ../../../logs/ingestion.log 2>&1 &
INGESTION_PID=$!
echo $INGESTION_PID > ../../../logs/ingestion.pid
cd ../../..
print_success "KG Ingestion API avviato (PID: $INGESTION_PID)"

# Aspetta che si avvii
sleep 3

# Avvia Frontend in background
print_warning "Avvio Frontend React (porta 3000)..."
cd frontend/rlcf-web
nohup npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../../logs/frontend.pid
cd ../..
print_success "Frontend avviato (PID: $FRONTEND_PID)"

# Aspetta che tutti i servizi si avviino
print_warning "Attesa 10 secondi per l'avvio completo..."
sleep 10

# ============================================================================
# 9. Verifica Health Endpoints
# ============================================================================

print_step "9. Verifica Servizi"

# Controlla visualex
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    print_success "visualex API: OK"
else
    print_warning "visualex API: Non risponde (potrebbe essere normale)"
    echo "Controlla i log: logs/visualex.log"
fi

# Controlla Backend Orchestration
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend Orchestration: OK"
else
    print_error "Backend Orchestration: NON RISPONDE"
    echo "Controlla i log: logs/orchestration.log"
fi

# Controlla Backend RLCF
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    print_success "Backend RLCF: OK"
else
    print_error "Backend RLCF: NON RISPONDE"
    echo "Controlla i log: logs/rlcf.log"
fi

# Controlla Ingestion API
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    print_success "KG Ingestion API: OK"
else
    print_error "KG Ingestion API: NON RISPONDE"
    echo "Controlla i log: logs/ingestion.log"
fi

# Controlla Frontend (può richiedere più tempo)
sleep 5
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Frontend: OK"
else
    print_warning "Frontend: In avvio..."
    echo "Controlla i log: logs/frontend.log"
fi

# ============================================================================
# 10. Informazioni Finali
# ============================================================================

print_step "10. Sistema Avviato! 🎉"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  ✓ MERL-T è pronto! Ecco i link:                             ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  🌐 Frontend:           http://localhost:3000               ║${NC}"
echo -e "${GREEN}║  📊 visualex API:       http://localhost:5000               ║${NC}"
echo -e "${GREEN}║  📡 Orchestration API:  http://localhost:8000/docs          ║${NC}"
echo -e "${GREEN}║  🤖 RLCF API:           http://localhost:8001/docs          ║${NC}"
echo -e "${GREEN}║  🔄 KG Ingestion API:   http://localhost:8002/docs          ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}📋 Comandi Utili:${NC}"
echo ""
echo "  • Vedi log visualex:       tail -f logs/visualex.log"
echo "  • Vedi log orchestration:  tail -f logs/orchestration.log"
echo "  • Vedi log RLCF:           tail -f logs/rlcf.log"
echo "  • Vedi log ingestion:      tail -f logs/ingestion.log"
echo "  • Vedi log frontend:       tail -f logs/frontend.log"
echo "  • Stop tutti i servizi:    ./quickstart/stop-dev.sh"
echo "  • Riavvia:                 ./quickstart/restart-dev.sh"
echo ""

echo -e "${CYAN}🧪 Test Rapido:${NC}"
echo ""
echo '  curl -X POST http://localhost:8000/api/v1/queries \'
echo '    -H "Content-Type: application/json" \'
echo '    -H "X-API-Key: dev-admin-key-12345" \'
echo '    -d '"'"'{"query_text": "Cosa prevede l'"'"'art. 2043 del Codice Civile?", "context": {"domain": "civil_law"}}'"'"
echo ""

echo -e "${CYAN}📖 Documentazione:${NC}"
echo ""
echo "  • Guida completa:  docs/07-guides/PRIMA_ACCENSIONE.md"
echo "  • API Examples:    docs/api/API_EXAMPLES.md"
echo "  • Architettura:    docs/03-architecture/"
echo ""

# Salva informazioni di runtime
cat > logs/runtime.info << EOF
MERL-T Development Environment
Started: $(date)
Mode: $mode
visualex PID: $VISUALEX_PID
Orchestration PID: $ORCHESTRATION_PID
RLCF PID: $RLCF_PID
Ingestion PID: $INGESTION_PID
Frontend PID: $FRONTEND_PID
Database: ${DATABASE_URL:-SQLite}
EOF

print_success "Runtime info salvate in logs/runtime.info"

# Apri browser automaticamente (opzionale)
print_warning "Vuoi aprire il browser automaticamente? [Y/n]"
read -r response
if [[ ! "$response" =~ ^([nN][oO]|[nN])$ ]]; then
    sleep 2
    if command -v open &> /dev/null; then
        open http://localhost:3000
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    else
        print_warning "Browser non aperto automaticamente. Vai a http://localhost:3000"
    fi
fi

echo ""
echo -e "${MAGENTA}Buona esplorazione! 🚀${NC}"
echo ""
echo -e "${YELLOW}Premi Ctrl+C per terminare lo script (i servizi continueranno a girare)${NC}"
echo -e "${YELLOW}Usa ./stop-dev.sh per fermare tutto${NC}"
echo ""

# Mantieni lo script attivo e mostra log in tempo reale
tail -f logs/*.log
