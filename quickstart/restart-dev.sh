#!/bin/bash

# ============================================================================
# MERL-T Development Environment Restart Script
# ============================================================================

set -e

# Colori
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    🔄  MERL-T Development Environment Restart Script      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Stop tutto
echo "Stopping services..."
./stop-dev.sh

# Aspetta un po'
echo ""
echo "Waiting 3 seconds..."
sleep 3

# Riavvia
echo ""
echo "Starting services..."
./start-dev.sh
