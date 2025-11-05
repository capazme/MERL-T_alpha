#!/bin/bash
# ===========================================
# Neo4j Setup and Schema Initialization Script
# ===========================================
#
# This script:
# 1. Starts Neo4j and Redis with Docker Compose
# 2. Waits for Neo4j to be healthy
# 3. Loads the schema from init-schema.cypher
# 4. Verifies the schema was loaded correctly
#
# Usage:
#   ./infrastructure/scripts/setup_neo4j.sh
#
# ===========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MERL-T Neo4j Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Start Neo4j and Redis
echo -e "${YELLOW}Step 1: Starting Neo4j and Redis...${NC}"
cd "$PROJECT_ROOT"

docker-compose --profile phase2 up -d neo4j redis

echo -e "${GREEN}✓ Docker containers starting${NC}"
echo ""

# Step 2: Wait for Neo4j to be healthy
echo -e "${YELLOW}Step 2: Waiting for Neo4j to be healthy...${NC}"
echo "This may take 30-60 seconds on first startup..."

MAX_WAIT=120  # Maximum wait time in seconds
WAIT_TIME=0
SLEEP_INTERVAL=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    # Check if container is running
    if ! docker ps | grep -q merl-t-neo4j; then
        echo -e "${RED}✗ Neo4j container is not running${NC}"
        echo "Check logs: docker logs merl-t-neo4j"
        exit 1
    fi

    # Check health status
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' merl-t-neo4j 2>/dev/null || echo "unknown")

    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ Neo4j is healthy${NC}"
        break
    fi

    echo "Waiting for Neo4j... ($WAIT_TIME seconds elapsed, status: $HEALTH_STATUS)"
    sleep $SLEEP_INTERVAL
    WAIT_TIME=$((WAIT_TIME + SLEEP_INTERVAL))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}✗ Neo4j did not become healthy within $MAX_WAIT seconds${NC}"
    echo "Check logs: docker logs merl-t-neo4j"
    exit 1
fi

echo ""

# Step 2.5: Copy schema file to container
echo -e "${YELLOW}Step 2.5: Copying schema file to container...${NC}"

SCHEMA_FILE="$PROJECT_ROOT/infrastructure/docker/init-schema.cypher"

if [ ! -f "$SCHEMA_FILE" ]; then
    echo -e "${RED}✗ Schema file not found: $SCHEMA_FILE${NC}"
    exit 1
fi

docker cp "$SCHEMA_FILE" merl-t-neo4j:/var/lib/neo4j/import/init-schema.cypher

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Schema file copied to container${NC}"
else
    echo -e "${RED}✗ Failed to copy schema file${NC}"
    exit 1
fi

echo ""

# Step 3: Load schema
echo -e "${YELLOW}Step 3: Loading schema from init-schema.cypher...${NC}"

# Load schema via cypher-shell
cat "$SCHEMA_FILE" | docker exec -i merl-t-neo4j cypher-shell \
    -u neo4j \
    -p merl_t_password \
    --database neo4j \
    --format plain

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Schema loaded successfully${NC}"
else
    echo -e "${RED}✗ Failed to load schema${NC}"
    exit 1
fi

echo ""

# Step 4: Verify schema
echo -e "${YELLOW}Step 4: Verifying schema...${NC}"

# Check constraints
echo "Checking constraints..."
docker exec merl-t-neo4j cypher-shell \
    -u neo4j \
    -p merl_t_password \
    --database neo4j \
    "SHOW CONSTRAINTS;" \
    --format plain

echo ""

# Check indexes
echo "Checking indexes..."
docker exec merl-t-neo4j cypher-shell \
    -u neo4j \
    -p merl_t_password \
    --database neo4j \
    "SHOW INDEXES;" \
    --format plain

echo ""

# Count nodes
echo "Counting nodes by label..."
docker exec merl-t-neo4j cypher-shell \
    -u neo4j \
    -p merl_t_password \
    --database neo4j \
    "MATCH (n) RETURN labels(n)[0] AS type, count(*) AS count ORDER BY count DESC;" \
    --format plain

echo ""

# Test sample data
echo "Testing sample data (Art. 1321 c.c.)..."
docker exec merl-t-neo4j cypher-shell \
    -u neo4j \
    -p merl_t_password \
    --database neo4j \
    "MATCH (a:Articolo {id: 'cc_art_1321'}) RETURN a.numero, a.titolo;" \
    --format plain

echo ""

# Step 5: Check Redis
echo -e "${YELLOW}Step 5: Checking Redis connection...${NC}"

if docker exec merl-t-redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ Redis is responding${NC}"
else
    echo -e "${RED}✗ Redis is not responding${NC}"
    exit 1
fi

echo ""

# Success summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Neo4j Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Neo4j Browser: http://localhost:7474"
echo "  Username: neo4j"
echo "  Password: merl_t_password"
echo "  Database: neo4j (default)"
echo ""
echo "Bolt URI: bolt://localhost:7687"
echo ""
echo "Next steps:"
echo "1. Access Neo4j Browser to explore the graph"
echo "2. Run data ingestion scripts to load 5,000+ articles"
echo "3. Test backend connection with Python scripts"
echo ""
echo "To stop Neo4j and Redis:"
echo "  docker-compose --profile phase2 down"
echo ""
echo "To view logs:"
echo "  docker logs merl-t-neo4j"
echo "  docker logs merl-t-redis"
echo ""
