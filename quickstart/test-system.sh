#!/bin/bash

# ============================================================================
# MERL-T System Quick Test Script
# ============================================================================
# Esegue test rapidi su tutti i componenti del sistema
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

# ============================================================================
# Test 1: Health Endpoints
# ============================================================================

print_test "Verifica Health Endpoints"

# Backend Orchestration
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    print_pass "Backend Orchestration health OK"
else
    print_fail "Backend Orchestration health FAILED"
fi

# Backend RLCF
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    print_pass "Backend RLCF health OK"
else
    print_fail "Backend RLCF health FAILED"
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_pass "Frontend responding OK"
else
    print_fail "Frontend not responding"
fi

# ============================================================================
# Test 2: API Endpoints
# ============================================================================

print_test "Verifica API Endpoints"

# Lista query (orchestration)
if curl -s -H "X-API-Key: dev-admin-key-12345" http://localhost:8000/api/v1/queries | grep -q "\["; then
    print_pass "GET /api/v1/queries OK"
else
    print_fail "GET /api/v1/queries FAILED"
fi

# Stats (orchestration)
if curl -s -H "X-API-Key: dev-admin-key-12345" "http://localhost:8000/api/v1/stats/queries?days=7" > /dev/null 2>&1; then
    print_pass "GET /api/v1/stats/queries OK"
else
    print_fail "GET /api/v1/stats/queries FAILED"
fi

# Tasks list (RLCF)
if curl -s http://localhost:8001/tasks | grep -q "tasks"; then
    print_pass "GET /tasks OK"
else
    print_fail "GET /tasks FAILED"
fi

# Users list (RLCF)
if curl -s http://localhost:8001/users | grep -q "users"; then
    print_pass "GET /users OK"
else
    print_fail "GET /users FAILED"
fi

# ============================================================================
# Test 3: Creazione Query End-to-End
# ============================================================================

print_test "Test Query End-to-End"

# Crea query
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/queries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-admin-key-12345" \
  -d '{
    "query_text": "Test query: Quali sono gli elementi della responsabilità extracontrattuale?",
    "context": {
      "domain": "civil_law",
      "jurisdiction": "italy"
    }
  }')

if echo "$QUERY_RESPONSE" | grep -q "query_id"; then
    QUERY_ID=$(echo "$QUERY_RESPONSE" | grep -o '"query_id":"[^"]*"' | cut -d'"' -f4)
    print_pass "Query creata con ID: $QUERY_ID"

    # Aspetta elaborazione
    echo -e "${YELLOW}     Attesa 15 secondi per elaborazione...${NC}"
    sleep 15

    # Verifica risultato
    RESULT=$(curl -s http://localhost:8000/api/v1/queries/$QUERY_ID \
      -H "X-API-Key: dev-admin-key-12345")

    if echo "$RESULT" | grep -q "status"; then
        STATUS=$(echo "$RESULT" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        print_pass "Query status: $STATUS"

        if [ "$STATUS" = "completed" ]; then
            print_pass "Query completata con successo!"

            # Salva risultato per ispezione
            echo "$RESULT" | jq '.' > logs/test_query_result.json 2>/dev/null || echo "$RESULT" > logs/test_query_result.json
            print_pass "Risultato salvato in logs/test_query_result.json"
        elif [ "$STATUS" = "failed" ]; then
            print_fail "Query fallita"
        fi
    else
        print_fail "Impossibile recuperare stato query"
    fi
else
    print_fail "Impossibile creare query"
fi

# ============================================================================
# Test 4: RLCF Task Creation
# ============================================================================

print_test "Test Creazione Task RLCF"

TASK_RESPONSE=$(curl -s -X POST http://localhost:8001/tasks \
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
    }
  }')

if echo "$TASK_RESPONSE" | grep -q "task_id"; then
    TASK_ID=$(echo "$TASK_RESPONSE" | grep -o '"task_id":[0-9]*' | grep -o '[0-9]*')
    print_pass "Task RLCF creato con ID: $TASK_ID"
else
    print_fail "Impossibile creare task RLCF"
fi

# ============================================================================
# Test 5: Database Connectivity
# ============================================================================

print_test "Verifica Database"

# Controlla se SQLite DB esiste
if [ -f "merl_t.db" ]; then
    print_pass "Database SQLite trovato"
elif docker ps | grep -q merl-t-postgres; then
    print_pass "PostgreSQL container attivo"
else
    print_fail "Nessun database trovato"
fi

# ============================================================================
# Test 6: Configuration Files
# ============================================================================

print_test "Verifica File di Configurazione"

if [ -f ".env" ]; then
    print_pass "File .env presente"

    # Verifica API key
    if grep -q "OPENROUTER_API_KEY=sk-or" .env; then
        print_pass "OPENROUTER_API_KEY configurata"
    else
        print_fail "OPENROUTER_API_KEY non configurata"
    fi
else
    print_fail "File .env mancante"
fi

# Verifica config YAML
if [ -f "backend/orchestration/config/orchestration_config.yaml" ]; then
    print_pass "orchestration_config.yaml presente"
else
    print_fail "orchestration_config.yaml mancante"
fi

# ============================================================================
# Test 7: Log Files
# ============================================================================

print_test "Verifica Log Files"

if [ -d "logs" ]; then
    LOG_COUNT=$(ls -1 logs/*.log 2>/dev/null | wc -l)
    if [ $LOG_COUNT -gt 0 ]; then
        print_pass "Log files trovati ($LOG_COUNT file)"

        # Controlla errori nei log
        ERROR_COUNT=$(grep -i "error" logs/*.log 2>/dev/null | wc -l)
        if [ $ERROR_COUNT -eq 0 ]; then
            print_pass "Nessun errore nei log"
        else
            print_fail "Trovati $ERROR_COUNT errori nei log (controlla logs/*.log)"
        fi
    else
        print_fail "Nessun log file trovato"
    fi
else
    print_fail "Directory logs mancante"
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
    echo "Il sistema MERL-T è completamente funzionante."
    echo ""
    exit 0
else
    echo -e "${RED}✗ $FAILED_TESTS TEST FALLITI${NC}"
    echo ""
    echo "Controlla i log per maggiori dettagli:"
    echo "  • logs/orchestration.log"
    echo "  • logs/rlcf.log"
    echo "  • logs/frontend.log"
    echo ""
    exit 1
fi
