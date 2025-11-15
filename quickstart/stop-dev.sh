#!/bin/bash

# ============================================================================
# MERL-T Development Environment Stop Script
# ============================================================================

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    🛑  MERL-T Development Environment Stop Script         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

print_step() {
    echo -e "\n${CYAN}==>${NC} $1\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ============================================================================
# 1. Stop Servizi dall PID files
# ============================================================================

print_step "Stopping MERL-T Services"

# Stop visualex
if [ -f "logs/visualex.pid" ]; then
    PID=$(cat logs/visualex.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        print_success "visualex API (PID: $PID) stopped"
    else
        print_warning "visualex API già fermato"
    fi
    rm logs/visualex.pid
fi

# Stop Backend Orchestration
if [ -f "logs/orchestration.pid" ]; then
    PID=$(cat logs/orchestration.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        print_success "Backend Orchestration (PID: $PID) stopped"
    else
        print_warning "Backend Orchestration già fermato"
    fi
    rm logs/orchestration.pid
fi

# Stop Backend RLCF
if [ -f "logs/rlcf.pid" ]; then
    PID=$(cat logs/rlcf.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        print_success "Backend RLCF (PID: $PID) stopped"
    else
        print_warning "Backend RLCF già fermato"
    fi
    rm logs/rlcf.pid
fi

# Stop Ingestion API
if [ -f "logs/ingestion.pid" ]; then
    PID=$(cat logs/ingestion.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        print_success "KG Ingestion API (PID: $PID) stopped"
    else
        print_warning "KG Ingestion API già fermato"
    fi
    rm logs/ingestion.pid
fi

# Stop Frontend
if [ -f "logs/frontend.pid" ]; then
    PID=$(cat logs/frontend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        print_success "Frontend (PID: $PID) stopped"
    else
        print_warning "Frontend già fermato"
    fi
    rm logs/frontend.pid
fi

# ============================================================================
# 2. Cleanup Porte (fallback)
# ============================================================================

print_step "Cleanup Ports (fallback)"

# Kill any remaining processes on our ports
for port in 3000 5000 8000 8001 8002; do
    if lsof -ti:$port > /dev/null 2>&1; then
        lsof -ti:$port | xargs kill -9
        print_warning "Processo sulla porta $port terminato forzatamente"
    fi
done

# ============================================================================
# 3. Stop Docker Containers (opzionale)
# ============================================================================

print_warning "Vuoi fermare anche i container Docker? [y/N]"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    if command -v docker-compose &> /dev/null; then
        print_step "Stopping Docker Containers"
        docker-compose -f docker-compose.dev.yml down
        print_success "Docker containers fermati"
    fi
fi

# ============================================================================
# 4. Cleanup Logs (opzionale)
# ============================================================================

print_warning "Vuoi cancellare i file di log? [y/N]"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    rm -f logs/*.log
    rm -f logs/runtime.info
    print_success "Log files cancellati"
fi

echo ""
print_success "MERL-T development environment stopped ✓"
echo ""
echo -e "${CYAN}Per riavviare: ${NC}./start-dev.sh"
echo ""
