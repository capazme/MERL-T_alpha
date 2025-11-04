#!/bin/bash
# Test script for Dynamic Configuration System
# Tests hot-reload, API endpoints, and validation

set -e  # Exit on error

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${ADMIN_API_KEY:-supersecretkey}"

echo "========================================"
echo "Testing Dynamic Configuration System"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper function for tests
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    echo -n "Testing: $name... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" \
            -H "X-API-KEY: $API_KEY")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-KEY: $API_KEY" \
            -d "$data")
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-KEY: $API_KEY" \
            -d "$data")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$endpoint" \
            -H "X-API-KEY: $API_KEY")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        echo "  Response: $(echo $body | jq -c . 2>/dev/null || echo $body | head -c 80)"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "  Error: $(echo $body | jq . 2>/dev/null || echo $body)"
        return 1
    fi
}

echo "1. Configuration Status"
echo "----------------------"
test_endpoint "Get config status" GET "/config/status"
echo ""

echo "2. List Task Types"
echo "------------------"
test_endpoint "List all task types" GET "/config/task/types"
echo ""

echo "3. Create New Task Type"
echo "-----------------------"
NEW_TASK='{
  "task_type_name": "TEST_DYNAMIC_TASK",
  "schema": {
    "input_data": {
      "test_input": "str",
      "test_number": "int"
    },
    "feedback_data": {
      "test_result": "str",
      "confidence": "float"
    },
    "ground_truth_keys": ["test_result"]
  }
}'
test_endpoint "Create TEST_DYNAMIC_TASK" POST "/config/task/type" "$NEW_TASK"
echo ""

echo "4. Verify New Task Type"
echo "-----------------------"
test_endpoint "Check task type exists" GET "/config/task/types"
echo ""

echo "5. Get Task Type Schema"
echo "-----------------------"
test_endpoint "Get TEST_DYNAMIC_TASK schema" GET "/config/task/type/TEST_DYNAMIC_TASK"
echo ""

echo "6. Update Task Type"
echo "-------------------"
UPDATED_SCHEMA='{
  "schema": {
    "input_data": {
      "test_input": "str",
      "test_number": "int",
      "new_field": "str"
    },
    "feedback_data": {
      "test_result": "str",
      "confidence": "float",
      "notes": "str"
    },
    "ground_truth_keys": ["test_result"]
  }
}'
test_endpoint "Update TEST_DYNAMIC_TASK" PUT "/config/task/type/TEST_DYNAMIC_TASK" "$UPDATED_SCHEMA"
echo ""

echo "7. List Backups"
echo "---------------"
test_endpoint "List configuration backups" GET "/config/backups?config_type=task"
echo ""

echo "8. Validation Test (Should Fail)"
echo "--------------------------------"
INVALID_TASK='{
  "task_type_name": "INVALID_TASK",
  "schema": {
    "input_data": {},
    "feedback_data": {}
  }
}'
echo -n "Testing: Create invalid task (should fail)... "
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/config/task/type" \
    -H "Content-Type: application/json" \
    -H "X-API-KEY: $API_KEY" \
    -d "$INVALID_TASK")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -ge 400 ]; then
    echo -e "${GREEN}✓ PASS${NC} (Correctly rejected, HTTP $http_code)"
else
    echo -e "${RED}✗ FAIL${NC} (Should have been rejected)"
fi
echo ""

echo "9. Delete Task Type"
echo "-------------------"
test_endpoint "Delete TEST_DYNAMIC_TASK" DELETE "/config/task/type/TEST_DYNAMIC_TASK"
echo ""

echo "10. Verify Deletion"
echo "-------------------"
test_endpoint "Confirm task type deleted" GET "/config/task/types"
echo ""

echo "========================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "========================================"
echo ""
echo -e "${YELLOW}Note:${NC} Check server logs for hot-reload messages:"
echo "  tail -f rlcf_detailed.log | grep ConfigManager"
echo ""
echo -e "${YELLOW}Manual test:${NC} Edit task_config.yaml and watch for auto-reload"
