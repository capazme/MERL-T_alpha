#!/bin/bash

# ============================================================================
# MERL-T Hard Cleanup Script
# ============================================================================
# ⚠️  ELIMINA TUTTO: database, venv, node_modules, cache, Docker volumes
# Usa questo per un reset COMPLETO al primo clone
# ============================================================================

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${RED}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    💀  MERL-T HARD CLEANUP - ATTENZIONE!                  ║
║                                                           ║
║    ⚠️  QUESTO SCRIPT ELIMINERÀ:                            ║
║                                                           ║
║    🗑️  Database SQLite (TUTTI I DATI!)                     ║
║    🗑️  Virtual Environment Python                         ║
║    🗑️  node_modules                                       ║
║    🗑️  Cache Python/Vite                                  ║
║    🗑️  Log files                                          ║
║    🗑️  Docker volumes (DATI PERMANENTI!)                  ║
║    🗑️  File .env (CONFIGURAZIONE!)                        ║
║                                                           ║
║    ✅  MANTERRÀ SOLO:                                      ║
║    • Codice sorgente                                      ║
║    • .git (repository)                                    ║
║    • Documentazione                                       ║
║                                                           ║
║    Equivalente a: git clone fresco                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

print_step() {
    echo -e "\n${CYAN}==>${NC} ${MAGENTA}$1${NC}\n"
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

# Vai alla root del progetto
cd "$(dirname "$0")/.."

# ============================================================================
# Conferma Tripla (è MOLTO pericoloso!)
# ============================================================================

echo -e "${RED}"
echo "⚠️  ATTENZIONE MASSIMA! ⚠️"
echo "Stai per ELIMINARE PERMANENTEMENTE:"
echo "  • Tutti i database e i loro dati"
echo "  • Tutti gli environment (venv, node_modules)"
echo "  • Tutte le configurazioni (.env)"
echo "  • Tutti i volumi Docker"
echo ""
echo "Questa operazione è IRREVERSIBILE e NON ha UNDO!"
echo -e "${NC}"
echo ""

# Prima conferma
print_warning "Prima conferma - Sei ASSOLUTAMENTE sicuro?"
read -p "Digita 'DELETE-EVERYTHING' per procedere: " confirm1

if [ "$confirm1" != "DELETE-EVERYTHING" ]; then
    echo ""
    print_error "Hard cleanup annullato (prima conferma fallita)"
    exit 1
fi

# Seconda conferma
echo ""
print_warning "Seconda conferma - Hai fatto backup se necessario?"
read -p "Digita 'YES-PROCEED' per confermare: " confirm2

if [ "$confirm2" != "YES-PROCEED" ]; then
    echo ""
    print_error "Hard cleanup annullato (seconda conferma fallita)"
    exit 1
fi

# Terza conferma con countdown
echo ""
print_warning "ULTIMA POSSIBILITÀ DI ANNULLARE!"
echo -e "${RED}Inizio hard cleanup tra 5 secondi...${NC}"
echo "Premi Ctrl+C ORA per annullare!"
for i in 5 4 3 2 1; do
    echo -ne "\r${RED}$i...${NC}"
    sleep 1
done
echo ""
echo ""

print_step "🔥 HARD CLEANUP AVVIATO 🔥"

REMOVED_COUNT=0

# ============================================================================
# 1. Stop TUTTI i Servizi
# ============================================================================

print_step "1. Stop Tutti i Servizi"

# Stop servizi con script
if [ -f "quickstart/stop-dev.sh" ]; then
    bash quickstart/stop-dev.sh 2>/dev/null || true
fi

# Kill brutale di tutti i processi Python/Node
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "npm run dev" 2>/dev/null || true
pkill -9 -f "vite" 2>/dev/null || true

# Cleanup porte
for port in 3000 8000 8001 5432 6379 6333 7474 7687; do
    if lsof -ti:$port > /dev/null 2>&1; then
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    fi
done

print_success "Tutti i servizi terminati"

# ============================================================================
# 2. Rimuovi TUTTI i Database
# ============================================================================

print_step "2. Eliminazione Database (TUTTI I DATI!)"

# SQLite
for dbfile in *.db *.db-shm *.db-wal; do
    if [ -f "$dbfile" ]; then
        rm -f "$dbfile"
        print_success "Rimosso $dbfile"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
    fi
done

# Docker volumes (DATI PERMANENTI!)
if command -v docker-compose &> /dev/null; then
    if [ -f "docker-compose.dev.yml" ]; then
        echo -e "${RED}Rimozione volumi Docker (PostgreSQL, Neo4j, Redis, Qdrant)...${NC}"
        docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true
        print_success "Volumi Docker eliminati (DATI PERSI)"
        REMOVED_COUNT=$((REMOVED_COUNT + 1))
    fi

    # Cleanup completo Docker
    print_warning "Pulizia immagini Docker..."
    docker system prune -af --volumes 2>/dev/null || true
    print_success "Docker cleanup completo"
fi

print_warning "💀 Tutti i database eliminati (dati irrecuperabili)"

# ============================================================================
# 3. Rimuovi Virtual Environment Python
# ============================================================================

print_step "3. Eliminazione Virtual Environment Python"

if [ -d "venv" ]; then
    rm -rf venv
    print_success "venv/ eliminato"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning "venv/ non trovato"
fi

# ============================================================================
# 4. Rimuovi node_modules
# ============================================================================

print_step "4. Eliminazione node_modules"

if [ -d "frontend/rlcf-web/node_modules" ]; then
    print_warning "Eliminazione node_modules (può richiedere tempo)..."
    rm -rf frontend/rlcf-web/node_modules
    print_success "node_modules/ eliminato"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning "node_modules/ non trovato"
fi

# package-lock.json
if [ -f "frontend/rlcf-web/package-lock.json" ]; then
    rm -f frontend/rlcf-web/package-lock.json
    print_success "package-lock.json eliminato"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

# ============================================================================
# 5. Rimuovi TUTTA la Cache
# ============================================================================

print_step "5. Eliminazione Cache Completa"

# Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
print_success "Cache Python eliminata"
REMOVED_COUNT=$((REMOVED_COUNT + 1))

# Vite cache
if [ -d "frontend/rlcf-web/node_modules/.vite" ]; then
    rm -rf frontend/rlcf-web/node_modules/.vite
    print_success "Cache Vite eliminata"
fi

# Vite dist
if [ -d "frontend/rlcf-web/dist" ]; then
    rm -rf frontend/rlcf-web/dist
    print_success "Build Vite eliminato"
fi

# pytest cache
if [ -d ".pytest_cache" ]; then
    rm -rf .pytest_cache
    print_success "Pytest cache eliminata"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

# Coverage
if [ -d "htmlcov" ]; then
    rm -rf htmlcov
    print_success "Coverage reports eliminati"
fi
if [ -f ".coverage" ]; then
    rm -f .coverage
    print_success "Coverage data eliminato"
fi

# mypy cache
if [ -d ".mypy_cache" ]; then
    rm -rf .mypy_cache
    print_success "mypy cache eliminata"
fi

# ============================================================================
# 6. Rimuovi TUTTI i Log
# ============================================================================

print_step "6. Eliminazione Log Files"

if [ -d "logs" ]; then
    rm -rf logs/*
    print_success "Tutti i log eliminati"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

# ============================================================================
# 7. Rimuovi File Temporanei
# ============================================================================

print_step "7. Eliminazione File Temporanei"

# .DS_Store
find . -name ".DS_Store" -delete 2>/dev/null || true
print_success ".DS_Store files eliminati"

# Backup files
find . -name "*~" -delete 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
print_success "File di backup eliminati"

# Temp directories
rm -rf /tmp/merl-t-* 2>/dev/null || true

# ============================================================================
# 8. Rimuovi File .env (CONFIGURAZIONE!)
# ============================================================================

print_step "8. Eliminazione File .env"

if [ -f ".env" ]; then
    # Backup PRIMA di eliminare
    mkdir -p backups
    cp .env "backups/.env.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "Backup .env salvato in backups/"

    rm -f ".env"
    print_success ".env eliminato (CONFIGURAZIONE PERSA!)"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning ".env non trovato"
fi

# Anche altri .env*
for envfile in .env.local .env.development .env.production; do
    if [ -f "$envfile" ]; then
        rm -f "$envfile"
        print_success "$envfile eliminato"
    fi
done

# ============================================================================
# 9. Rimuovi Build Artifacts
# ============================================================================

print_step "9. Eliminazione Build Artifacts"

# Python builds
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
print_success "Python build artifacts eliminati"

# ============================================================================
# 10. Rimuovi File di Lock
# ============================================================================

print_step "10. Eliminazione Lock Files"

# Python
if [ -f "poetry.lock" ]; then
    rm -f poetry.lock
    print_success "poetry.lock eliminato"
fi

if [ -f "Pipfile.lock" ]; then
    rm -f Pipfile.lock
    print_success "Pipfile.lock eliminato"
fi

# ============================================================================
# 11. Ricrea Struttura Minima
# ============================================================================

print_step "11. Ricreazione Struttura Essenziale"

# Directory essenziali
mkdir -p logs
mkdir -p backups
print_success "Directory essenziali ricreate"

# .gitkeep per directory vuote
touch logs/.gitkeep
touch backups/.gitkeep
print_success ".gitkeep files creati"

# ============================================================================
# 12. Verifica Git Repository
# ============================================================================

print_step "12. Verifica Repository Git"

if [ -d ".git" ]; then
    print_success "Repository Git OK (preservato)"

    # Controlla file non tracciati
    UNTRACKED=$(git status --porcelain | grep "^??" | wc -l | tr -d ' ')
    if [ "$UNTRACKED" -gt 0 ]; then
        print_warning "Trovati $UNTRACKED file non tracciati"
        echo "Esegui: git status"
    fi
else
    print_error "Repository Git NON trovato!"
fi

# ============================================================================
# 13. Summary e Istruzioni
# ============================================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ HARD CLEANUP COMPLETATO!${NC}"
echo ""
echo -e "Elementi eliminati: ${RED}$REMOVED_COUNT${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${MAGENTA}Il sistema è stato riportato a uno stato POST-CLONE${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${CYAN}📋 PROSSIMI PASSI OBBLIGATORI:${NC}"
echo ""
echo -e "${YELLOW}1. Ricrea file .env:${NC}"
echo "   cp .env.template .env"
echo "   nano .env  # Configura OPENROUTER_API_KEY"
echo ""
echo -e "${YELLOW}2. Ricrea Virtual Environment Python:${NC}"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -e ."
echo ""
echo -e "${YELLOW}3. Reinstalla Dipendenze Node.js:${NC}"
echo "   cd frontend/rlcf-web"
echo "   npm install"
echo "   cd ../.."
echo ""
echo -e "${YELLOW}4. Inizializza Database:${NC}"
echo "   rlcf-admin db migrate"
echo "   rlcf-admin db seed --users 5 --tasks 10"
echo ""
echo -e "${YELLOW}5. Avvia il Sistema:${NC}"
echo "   ./quickstart/start-dev.sh"
echo ""

echo -e "${CYAN}💡 OPPURE usa lo script di setup completo:${NC}"
echo ""
echo "   ./quickstart/setup-from-scratch.sh  ${YELLOW}# Se esiste${NC}"
echo ""

# Salva report dettagliato
REPORT_FILE="logs/hard_cleanup_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" << EOF
MERL-T Hard Cleanup Report
==========================
Data: $(date)
Elementi eliminati: $REMOVED_COUNT

Operazioni eseguite:
✓ Stop tutti i servizi
✓ Eliminazione database SQLite
✓ Eliminazione Docker volumes
✓ Eliminazione virtual environment Python
✓ Eliminazione node_modules
✓ Eliminazione cache completa
✓ Eliminazione log files
✓ Eliminazione file temporanei
✓ Eliminazione file .env
✓ Eliminazione build artifacts
✓ Eliminazione lock files

Backup salvati:
• .env → backups/.env.backup.$(date +%Y%m%d_%H%M%S)

Stato finale:
✓ Repository Git: OK
✓ Codice sorgente: PRESERVATO
✓ Documentazione: PRESERVATA
✓ Configurazione: ELIMINATA
✓ Dipendenze: ELIMINATE
✓ Dati: ELIMINATI

Prossimi passi:
1. Ricrea .env
2. Reinstalla dipendenze (venv + npm)
3. Inizializza database
4. Avvia sistema
EOF

print_success "Report salvato in $REPORT_FILE"

echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}⚠️  RICORDA: Tutti i dati sono stati ELIMINATI! ${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Hard cleanup completato! Sistema pronto per re-setup.${NC}"
echo ""
