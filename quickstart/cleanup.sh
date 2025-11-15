#!/bin/bash

# ============================================================================
# MERL-T Light Cleanup Script
# ============================================================================
# Pulisce solo cache e file di sessione
# MANTIENE: database, venv, node_modules, .env
# ============================================================================

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    🧹  MERL-T Light Cleanup Script                        ║
║                                                           ║
║    Pulisce cache e file di sessione                       ║
║                                                           ║
║    ✓ Rimuove:                                             ║
║    • Log files                                            ║
║    • Cache Python (__pycache__, *.pyc)                    ║
║    • Cache Vite (.vite)                                   ║
║    • File temporanei (.DS_Store, *~, *.swp)               ║
║    • PID files                                            ║
║    • Coverage reports                                     ║
║    • Pytest cache                                         ║
║                                                           ║
║    ✓ Mantiene:                                            ║
║    • Database (SQLite/PostgreSQL)                         ║
║    • Virtual environment (venv/)                          ║
║    • Node modules (node_modules/)                         ║
║    • Configurazione (.env)                                ║
║    • Docker volumes                                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

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

# Vai alla root del progetto
cd "$(dirname "$0")/.."

# ============================================================================
# Conferma Utente
# ============================================================================

echo ""
print_warning "Questo script pulirà cache e file di sessione."
print_warning "Database, venv e node_modules saranno PRESERVATI."
echo ""
read -p "Procedere? [Y/n] " confirm

if [[ "$confirm" =~ ^([nN][oO]|[nN])$ ]]; then
    echo ""
    print_error "Cleanup annullato"
    exit 1
fi

echo ""
print_step "Inizio Light Cleanup..."

# Conta elementi eliminati
REMOVED_COUNT=0
FREED_SPACE=0

# ============================================================================
# 1. Stop Servizi
# ============================================================================

print_step "1. Stop Servizi in Esecuzione"

# Usa lo script stop se esiste
if [ -f "quickstart/stop-dev.sh" ]; then
    print_warning "Esecuzione stop-dev.sh..."
    bash quickstart/stop-dev.sh || true
else
    # Stop manuale
    print_warning "Stop manuale dei servizi..."

    # PID files
    for pidfile in logs/orchestration.pid logs/rlcf.pid logs/frontend.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            if ps -p $PID > /dev/null 2>&1; then
                kill $PID 2>/dev/null || true
                print_success "Processo PID $PID terminato"
            fi
            rm "$pidfile"
            REMOVED_COUNT=$((REMOVED_COUNT + 1))
        fi
    done

    # Cleanup porte
    for port in 3000 8000 8001; do
        if lsof -ti:$port > /dev/null 2>&1; then
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
            print_success "Processo sulla porta $port terminato"
        fi
    done
fi

print_success "Servizi fermati"

# ============================================================================
# 2. Rimuovi Log Files
# ============================================================================

print_step "2. Rimozione Log Files"

if [ -d "logs" ]; then
    # Conta dimensione prima
    if command -v du &> /dev/null; then
        LOGS_SIZE=$(du -sk logs 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + LOGS_SIZE))
    fi

    # Conta file
    LOG_COUNT=$(find logs -type f -name "*.log" -o -name "*.pid" -o -name "*.info" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$LOG_COUNT" -gt 0 ]; then
        # Rimuovi solo log, pid, info (NON .gitkeep)
        find logs -type f \( -name "*.log" -o -name "*.pid" -o -name "*.info" -o -name "*.json" \) -delete 2>/dev/null || true
        print_success "Rimossi $LOG_COUNT file di log"
        REMOVED_COUNT=$((REMOVED_COUNT + LOG_COUNT))
    else
        print_warning "Nessun log file trovato"
    fi
else
    print_warning "Directory logs non trovata"
fi

# ============================================================================
# 3. Rimuovi Cache Python
# ============================================================================

print_step "3. Rimozione Cache Python"

# __pycache__
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    # Calcola dimensione
    if command -v du &> /dev/null; then
        PYCACHE_SIZE=$(find . -type d -name "__pycache__" -exec du -sk {} + 2>/dev/null | awk '{sum+=$1} END {print sum}')
        FREED_SPACE=$((FREED_SPACE + PYCACHE_SIZE))
    fi

    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    print_success "Rimossi $PYCACHE_COUNT directory __pycache__"
    REMOVED_COUNT=$((REMOVED_COUNT + PYCACHE_COUNT))
fi

# *.pyc
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYC_COUNT" -gt 0 ]; then
    find . -type f -name "*.pyc" -delete
    print_success "Rimossi $PYC_COUNT file *.pyc"
    REMOVED_COUNT=$((REMOVED_COUNT + PYC_COUNT))
fi

# *.pyo
PYO_COUNT=$(find . -type f -name "*.pyo" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYO_COUNT" -gt 0 ]; then
    find . -type f -name "*.pyo" -delete
    print_success "Rimossi $PYO_COUNT file *.pyo"
    REMOVED_COUNT=$((REMOVED_COUNT + PYO_COUNT))
fi

if [ "$PYCACHE_COUNT" -eq 0 ] && [ "$PYC_COUNT" -eq 0 ] && [ "$PYO_COUNT" -eq 0 ]; then
    print_warning "Nessuna cache Python trovata"
fi

# ============================================================================
# 4. Rimuovi Cache Vite
# ============================================================================

print_step "4. Rimozione Cache Vite"

VITE_CACHE="frontend/rlcf-web/node_modules/.vite"
if [ -d "$VITE_CACHE" ]; then
    # Dimensione
    if command -v du &> /dev/null; then
        VITE_SIZE=$(du -sk "$VITE_CACHE" 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + VITE_SIZE))
    fi

    rm -rf "$VITE_CACHE"
    print_success "Cache Vite rimossa"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning "Cache Vite non trovata"
fi

# Rimuovi anche build dist
VITE_DIST="frontend/rlcf-web/dist"
if [ -d "$VITE_DIST" ]; then
    if command -v du &> /dev/null; then
        DIST_SIZE=$(du -sk "$VITE_DIST" 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + DIST_SIZE))
    fi

    rm -rf "$VITE_DIST"
    print_success "Build Vite rimossa"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

# ============================================================================
# 5. Rimuovi File Temporanei
# ============================================================================

print_step "5. Rimozione File Temporanei"

# .DS_Store (macOS)
DSSTORE_COUNT=$(find . -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$DSSTORE_COUNT" -gt 0 ]; then
    find . -name ".DS_Store" -delete
    print_success "Rimossi $DSSTORE_COUNT file .DS_Store"
    REMOVED_COUNT=$((REMOVED_COUNT + DSSTORE_COUNT))
fi

# *~ (backup files)
BACKUP_COUNT=$(find . -name "*~" 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt 0 ]; then
    find . -name "*~" -delete
    print_success "Rimossi $BACKUP_COUNT file di backup"
    REMOVED_COUNT=$((REMOVED_COUNT + BACKUP_COUNT))
fi

# *.swp (vim)
SWP_COUNT=$(find . -name "*.swp" 2>/dev/null | wc -l | tr -d ' ')
if [ "$SWP_COUNT" -gt 0 ]; then
    find . -name "*.swp" -delete
    print_success "Rimossi $SWP_COUNT file *.swp"
    REMOVED_COUNT=$((REMOVED_COUNT + SWP_COUNT))
fi

if [ "$DSSTORE_COUNT" -eq 0 ] && [ "$BACKUP_COUNT" -eq 0 ] && [ "$SWP_COUNT" -eq 0 ]; then
    print_warning "Nessun file temporaneo trovato"
fi

# ============================================================================
# 6. Rimuovi Coverage Reports
# ============================================================================

print_step "6. Rimozione Coverage Reports"

if [ -d "htmlcov" ]; then
    if command -v du &> /dev/null; then
        COV_SIZE=$(du -sk htmlcov 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + COV_SIZE))
    fi

    rm -rf htmlcov
    print_success "Coverage HTML report rimosso"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

if [ -f ".coverage" ]; then
    rm -f .coverage
    print_success "Coverage data file rimosso"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
fi

if [ ! -d "htmlcov" ] && [ ! -f ".coverage" ]; then
    print_warning "Nessun coverage report trovato"
fi

# ============================================================================
# 7. Rimuovi Pytest Cache
# ============================================================================

print_step "7. Rimozione Pytest Cache"

if [ -d ".pytest_cache" ]; then
    if command -v du &> /dev/null; then
        PYTEST_SIZE=$(du -sk .pytest_cache 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + PYTEST_SIZE))
    fi

    rm -rf .pytest_cache
    print_success "Pytest cache rimossa"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning "Pytest cache non trovata"
fi

# ============================================================================
# 8. Rimuovi mypy cache
# ============================================================================

print_step "8. Rimozione mypy Cache"

if [ -d ".mypy_cache" ]; then
    if command -v du &> /dev/null; then
        MYPY_SIZE=$(du -sk .mypy_cache 2>/dev/null | cut -f1)
        FREED_SPACE=$((FREED_SPACE + MYPY_SIZE))
    fi

    rm -rf .mypy_cache
    print_success "mypy cache rimossa"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
else
    print_warning "mypy cache non trovata"
fi

# ============================================================================
# 9. Ricrea Directory Essenziali
# ============================================================================

print_step "9. Ricreazione Directory Essenziali"

mkdir -p logs
if [ ! -f "logs/.gitkeep" ]; then
    touch logs/.gitkeep
fi
print_success "Directory logs ricreata"

# ============================================================================
# 10. Summary
# ============================================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✓ LIGHT CLEANUP COMPLETATO!${NC}"
echo ""

# Converti KB in MB se necessario
if [ "$FREED_SPACE" -gt 1024 ]; then
    FREED_MB=$((FREED_SPACE / 1024))
    echo -e "Spazio liberato: ${MAGENTA}${FREED_MB} MB${NC}"
else
    echo -e "Spazio liberato: ${MAGENTA}${FREED_SPACE} KB${NC}"
fi

echo -e "Elementi rimossi: ${MAGENTA}$REMOVED_COUNT${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verifica cosa è stato preservato
echo -e "${GREEN}✓ PRESERVATI:${NC}"
echo ""
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} File .env (configurazione)"
fi
if [ -f "merl_t.db" ]; then
    DB_SIZE=$(du -h merl_t.db 2>/dev/null | cut -f1)
    echo -e "  ${GREEN}✓${NC} Database SQLite ($DB_SIZE)"
fi
if [ -d "venv" ]; then
    echo -e "  ${GREEN}✓${NC} Virtual environment (venv/)"
fi
if [ -d "frontend/rlcf-web/node_modules" ]; then
    echo -e "  ${GREEN}✓${NC} Node modules"
fi
echo ""

echo -e "${CYAN}Prossimi Passi:${NC}"
echo ""
echo "  1. Riavvia il sistema:"
echo "     ${BLUE}./quickstart/start-dev.sh${NC}"
echo ""
echo "  2. I servizi si avvieranno normalmente senza re-setup"
echo ""

# Salva report di cleanup
REPORT_FILE="logs/cleanup_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" << EOF
MERL-T Light Cleanup Report
===========================
Data: $(date)
Spazio liberato: ${FREED_SPACE} KB
Elementi rimossi: $REMOVED_COUNT

Operazioni eseguite:
✓ Stop servizi
✓ Rimozione log files
✓ Rimozione cache Python
✓ Rimozione cache Vite
✓ Rimozione file temporanei
✓ Rimozione coverage reports
✓ Rimozione pytest cache
✓ Rimozione mypy cache

Elementi preservati:
✓ Database (SQLite/PostgreSQL)
✓ Virtual environment (venv/)
✓ Node modules (node_modules/)
✓ Configurazione (.env)
✓ Docker volumes
✓ Codice sorgente

Stato finale:
✓ Sistema pronto per riavvio immediato
✓ Nessun re-setup necessario
EOF

print_success "Report salvato in $REPORT_FILE"

echo ""
echo -e "${MAGENTA}Light cleanup completato con successo! ✨${NC}"
echo ""
echo -e "${YELLOW}Suggerimento: Per un reset completo usa cleanup-hard.sh${NC}"
echo ""
