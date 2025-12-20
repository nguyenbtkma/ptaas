#!/bin/bash

# PTaaS Test Script - Demo ZAP Scanner Integration

echo "PTaaS Test Suite"
echo "===================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
response=$(curl -s http://localhost:8000/health)
echo "$response"
echo ""

# Test 2: Start Nmap Scan
echo -e "${BLUE}Test 2: Start Nmap Scan${NC}"
echo "Target: scanme.nmap.org"
response=$(curl -s -X POST http://localhost:8000/scan/nmap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "scanme.nmap.org",
    "options": "-sV -F"
  }')
echo "$response"

# Extract task_id
nmap_task_id=$(echo "$response" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
echo -e "${GREEN}Task ID: $nmap_task_id${NC}"
echo ""

# Test 3: Start ZAP Scan (passive mode for faster demo)
echo -e "${BLUE}Test 3: Start ZAP Scan${NC}"
echo "Target: http://testphp.vulnweb.com"
response=$(curl -s -X POST http://localhost:8000/scan/zap \
  -H "Content-Type: application/json" \
  -d '{
    "target": "http://testphp.vulnweb.com",
    "options": "passive"
  }')
echo "$response"

# Extract task_id
zap_task_id=$(echo "$response" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
echo -e "${GREEN}Task ID: $zap_task_id${NC}"
echo ""

# Test 4: Monitor Progress
echo -e "${BLUE}Test 4: Monitor ZAP Scan Progress${NC}"
echo "Checking status every 5 seconds..."
echo ""

for i in {1..10}; do
    response=$(curl -s http://localhost:8000/scan/status/$zap_task_id)
    state=$(echo "$response" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo -e "${YELLOW}[$i] State: $state | Status: $status${NC}"
    
    if [ "$state" = "SUCCESS" ] || [ "$state" = "FAILURE" ]; then
        echo "$response"
        break
    fi
    
    sleep 5
done

echo ""
echo -e "${GREEN}Tests completed!${NC}"
echo ""
echo "View results:"
echo "   - DefectDojo: http://localhost:8080"
echo "   - MinIO: http://localhost:9001"
echo "   - API Docs: http://localhost:8000/docs"
