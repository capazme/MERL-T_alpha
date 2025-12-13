#!/bin/bash
# Ingestion Libro IV CC - Overnight Script
# Esegue l'ingestion in background con log

set -e

cd "$(dirname "$0")/.."
source .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/ingestion_libro_iv_${TIMESTAMP}.log"

echo "========================================"
echo "INGESTION LIBRO IV CC - OVERNIGHT"
echo "========================================"
echo "Start: $(date)"
echo "Log: $LOG_FILE"
echo ""
echo "Per controllare il progresso:"
echo "  tail -f $LOG_FILE"
echo ""
echo "Per vedere gli ultimi risultati:"
echo "  grep -E '\[.*\/887\]' $LOG_FILE | tail -5"
echo ""
echo "Avvio in background..."
echo ""

# Run ingestion in background
nohup python3 scripts/ingest_libro_iv_cc.py > "$LOG_FILE" 2>&1 &
PID=$!

echo "PID: $PID"
echo ""
echo "Ingestion avviata! Puoi chiudere il terminale."
echo "I risultati saranno in: docs/experiments/libro_iv_cc_ingestion.json"
