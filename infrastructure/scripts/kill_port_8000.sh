#!/bin/bash

# Script per terminare tutti i processi sulla porta 8000
PORT=8000

echo "Cercando processi sulla porta $PORT..."

# Trova tutti i PID dei processi che usano la porta 8000
PIDS=$(lsof -t -i:$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "Nessun processo trovato sulla porta $PORT"
    exit 0
fi

echo "Processi trovati sulla porta $PORT:"
lsof -i:$PORT

echo ""
echo "Terminando i processi..."

# Termina tutti i processi trovati
for PID in $PIDS; do
    echo "Terminando processo PID: $PID"
    kill $PID
    
    # Aspetta un momento per la terminazione graceful
    sleep 1
    
    # Se il processo è ancora in esecuzione, forza la terminazione
    if kill -0 $PID 2>/dev/null; then
        echo "Forzando la terminazione del processo PID: $PID"
        kill -9 $PID
    fi
done

echo "Tutti i processi sulla porta $PORT sono stati terminati."

# Verifica che non ci siano più processi sulla porta
REMAINING=$(lsof -t -i:$PORT 2>/dev/null)
if [ -z "$REMAINING" ]; then
    echo "Porta $PORT ora libera."
else
    echo "ATTENZIONE: Alcuni processi potrebbero essere ancora attivi sulla porta $PORT"
fi 