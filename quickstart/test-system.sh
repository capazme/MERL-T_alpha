#!/bin/bash

# ============================================================================
# MERL-T System Quick Test Script
# ============================================================================
# Esegue test rapidi su tutti i componenti del sistema (5 servizi)
# ============================================================================

set -e

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    🧪  MERL-T System Quick Test                           ║
║    5 Services: visualex, Orchestration, RLCF,             ║
║                Ingestion, Frontend                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

print_test() {
    echo -e "\n${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}  ✓ PASS${NC} - $1"
}

print_fail() {
    echo -e "${RED}  ✗ FAIL${NC} - $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

FAILED_TESTS=0

# API Key for authenticated endpoints (development key)
API_KEY="supersecretkey"

# ============================================================================
# Test 1: Health Endpoints (All 5 Services)
# ============================================================================

print_test "Verifica Health Endpoints (5 servizi)"

# visualex API (port 5000)
if curl -s http://localhost:5000/health 2>/dev/null | grep -q "healthy"; then
    print_pass "visualex API (5000) health OK"
else
    print_fail "visualex API (5000) health FAILED"
fi

# Backend Orchestration (port 8000)
if curl -s http://localhost:8000/health 2>/dev/null | grep -q "healthy"; then
    print_pass "Backend Orchestration (8000) health OK"
else
    print_fail "Backend Orchestration (8000) health FAILED"
fi

# Backend RLCF (port 8001)
if curl -s http://localhost:8001/health 2>/dev/null | grep -q "healthy"; then
    print_pass "Backend RLCF (8001) health OK"
else
    print_fail "Backend RLCF (8001) health FAILED"
fi

# Ingestion API (port 8002)
if curl -s http://localhost:8002/health 2>/dev/null | grep -q "healthy"; then
    print_pass "Ingestion API (8002) health OK"
else
    print_fail "Ingestion API (8002) health FAILED"
fi

# Frontend (port 3000)
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_pass "Frontend (3000) responding OK"
else
    print_fail "Frontend (3000) not responding"
fi

# ============================================================================
# Test 2: API Endpoints
# ============================================================================

print_test "Verifica API Endpoints"

# visualex norms search (no auth required)
if curl -s "http://localhost:5000/search?query=responsabilità" 2>/dev/null > /dev/null; then
    print_pass "GET /search (visualex) OK"
else
    print_fail "GET /search (visualex) FAILED"
fi

# Query history (orchestration - requires auth)
if curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/query/history/test_user?limit=10" 2>/dev/null > /dev/null; then
    print_pass "GET /query/history (orchestration) OK"
else
    print_fail "GET /query/history (orchestration) FAILED"
fi

# Feedback stats (orchestration - requires auth)
if curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/feedback/stats 2>/dev/null > /dev/null; then
    print_pass "GET /feedback/stats (orchestration) OK"
else
    print_fail "GET /feedback/stats (orchestration) FAILED"
fi

# Tasks list (RLCF)
if curl -s http://localhost:8001/tasks/all 2>/dev/null > /dev/null; then
    print_pass "GET /tasks/all (RLCF) OK"
else
    print_fail "GET /tasks/all (RLCF) FAILED"
fi

# Users list (RLCF)
if curl -s http://localhost:8001/users/all 2>/dev/null > /dev/null; then
    print_pass "GET /users/all (RLCF) OK"
else
    print_fail "GET /users/all (RLCF) FAILED"
fi

# Batch list (Ingestion API)
if curl -s http://localhost:8002/batch/list 2>/dev/null > /dev/null; then
    print_pass "GET /batch/list (Ingestion) OK"
else
    print_fail "GET /batch/list (Ingestion) FAILED"
fi

# ============================================================================
# Test 3: Query Execution End-to-End
# ============================================================================

print_test "Test Query Execution End-to-End"

# Create query via Orchestration API
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/query/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "query": "Quali sono gli elementi della responsabilità extracontrattuale secondo l'\''art. 2043 c.c.?",
    "context": {
      "domain": "civil_law",
      "jurisdiction": "italy"
    },
    "options": {
      "max_iterations": 1,
      "timeout_seconds": 60
    }
  }' 2>/dev/null)

if echo "$QUERY_RESPONSE" | grep -q "trace_id"; then
    TRACE_ID=$(echo "$QUERY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['trace_id'])" 2>/dev/null || echo "$QUERY_RESPONSE" | grep -o '"trace_id":"[^"]*"' | cut -d'"' -f4)
    print_pass "Query creata con trace_id: $TRACE_ID"

    # Verifica status query
    sleep 2
    STATUS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/query/status/$TRACE_ID" 2>/dev/null)

    if echo "$STATUS_RESPONSE" | grep -q "status"; then
        STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        print_pass "Query status: $STATUS"
    else
        print_fail "Impossibile recuperare stato query"
    fi
else
    print_fail "Impossibile creare query (verificare auth e orchestration API)"
fi

# ============================================================================
# Test 4: RLCF Task Creation
# ============================================================================

print_test "Test Creazione Task RLCF"

TASK_RESPONSE=$(curl -s -X POST http://localhost:8001/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "classification",
    "input_data": {
      "text": "Il venditore deve consegnare la cosa al compratore.",
      "domain": "civil_law",
      "options": ["contract_law", "tort_law", "property_law"]
    },
    "ground_truth": {
      "correct_class": "contract_law",
      "confidence": 0.95
    },
    "status": "OPEN"
  }' 2>/dev/null)

if echo "$TASK_RESPONSE" | grep -q "id"; then
    TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "$TASK_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*')
    print_pass "Task RLCF creato con ID: $TASK_ID"
else
    print_fail "Impossibile creare task RLCF"
fi

# ============================================================================
# Test 5: Database Connectivity
# ============================================================================

print_test "Verifica Database"

# Check SQLite databases
DB_COUNT=0
for db in rlcf.db orchestration.db; do
    if [ -f "$db" ]; then
        print_pass "Database SQLite: $db trovato"
        DB_COUNT=$((DB_COUNT + 1))
    fi
done

if [ $DB_COUNT -eq 0 ]; then
    # Check PostgreSQL Docker container
    if docker ps 2>/dev/null | grep -q postgres; then
        print_pass "PostgreSQL container attivo"
    else
        print_fail "Nessun database trovato (né SQLite né PostgreSQL)"
    fi
fi

# ============================================================================
# Test 6: Configuration Files
# ============================================================================

print_test "Verifica File di Configurazione"

if [ -f ".env" ]; then
    print_pass "File .env presente"

    # Verifica API key OpenRouter
    if grep -q "OPENROUTER_API_KEY=sk-or" .env; then
        print_pass "OPENROUTER_API_KEY configurata"
    else
        print_fail "OPENROUTER_API_KEY non configurata correttamente"
    fi
else
    print_fail "File .env mancante"
fi

# Verifica config YAML orchestration
if [ -f "backend/orchestration/config/orchestration_config.yaml" ]; then
    print_pass "orchestration_config.yaml presente"
else
    print_fail "orchestration_config.yaml mancante"
fi

# Verifica config YAML RLCF
if [ -f "backend/rlcf_framework/model_config.yaml" ]; then
    print_pass "model_config.yaml presente"
else
    print_fail "model_config.yaml mancante"
fi

# ============================================================================
# Test 7: Log Files
# ============================================================================

print_test "Verifica Log Files"

if [ -d "logs" ]; then
    LOG_COUNT=$(ls -1 logs/*.log 2>/dev/null | wc -l | tr -d ' ')
    if [ $LOG_COUNT -gt 0 ]; then
        print_pass "Log files trovati ($LOG_COUNT file)"

        # Controlla errori critici nei log
        CRITICAL_COUNT=$(grep -i "critical\|fatal" logs/*.log 2>/dev/null | wc -l | tr -d ' ')
        if [ $CRITICAL_COUNT -eq 0 ]; then
            print_pass "Nessun errore critico nei log"
        else
            print_fail "Trovati $CRITICAL_COUNT errori critici nei log (controlla logs/*.log)"
        fi
    else
        print_fail "Nessun log file trovato"
    fi
else
    print_fail "Directory logs mancante"
fi

# ============================================================================
# Test 8: Docker Services (Optional)
# ============================================================================

print_test "Verifica Docker Services (Opzionale)"

# Check if Docker is running
if command -v docker &> /dev/null; then
    # Check Neo4j
    if docker ps 2>/dev/null | grep -q neo4j; then
        print_pass "Neo4j/Memgraph container attivo"
    else
        echo -e "${YELLOW}  ⚠ INFO${NC} - Neo4j container non attivo (opzionale per sviluppo)"
    fi

    # Check Redis
    if docker ps 2>/dev/null | grep -q redis; then
        print_pass "Redis container attivo"
    else
        echo -e "${YELLOW}  ⚠ INFO${NC} - Redis container non attivo (opzionale per sviluppo)"
    fi

    # Check Qdrant
    if docker ps 2>/dev/null | grep -q qdrant; then
        print_pass "Qdrant container attivo"
    else
        echo -e "${YELLOW}  ⚠ INFO${NC} - Qdrant container non attivo (opzionale per sviluppo)"
    fi
else
    echo -e "${YELLOW}  ⚠ INFO${NC} - Docker non disponibile (OK per sviluppo native)"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ TUTTI I TEST PASSATI! 🎉${NC}"
    echo ""
    echo "Il sistema MERL-T è completamente funzionante:"
    echo "  ✓ visualex API (5000)"
    echo "  ✓ Orchestration API (8000)"
    echo "  ✓ RLCF API (8001)"
    echo "  ✓ Ingestion API (8002)"
    echo "  ✓ Frontend (3000)"
    echo ""
    echo "Accedi a:"
    echo "  • Frontend: http://localhost:3000"
    echo "  • Orchestration Docs: http://localhost:8000/docs"
    echo "  • RLCF Docs: http://localhost:8001/docs"
    echo "  • Ingestion Docs: http://localhost:8002/docs"
    echo ""
    exit 0
else
    echo -e "${RED}✗ $FAILED_TESTS TEST FALLITI${NC}"
    echo ""
    echo "Controlla i log per maggiori dettagli:"
    echo "  • logs/visualex.log"
    echo "  • logs/orchestration.log"
    echo "  • logs/rlcf.log"
    echo "  • logs/ingestion.log"
    echo "  • logs/frontend.log"
    echo ""
    echo "Debug rapido:"
    echo "  1. Verifica servizi attivi: ps aux | grep -E 'uvicorn|vite|quart'"
    echo "  2. Verifica porte: lsof -ti:5000,8000,8001,8002,3000"
    echo "  3. Riavvia sistema: ./quickstart/restart-dev.sh"
    echo ""
    exit 1
fi
