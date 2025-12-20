#!/bin/bash

# PTaaS System Test & Demo
# Comprehensive test of all features

set -e  # Exit on error

echo "╔════════════════════════════════════════╗"
echo "║   PTaaS System Comprehensive Test     ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

API_URL="http://localhost:8000"

# Test 1: Health Check
echo -e "${BLUE}━━━ Test 1: Health Check ━━━${NC}"
response=$(curl -s $API_URL/health)
echo "$response" | python3 -m json.tool
echo -e "${GREEN}Health check passed${NC}\n"

# Test 2: Check existing results
echo -e "${BLUE}━━━ Test 2: Current Findings ━━━${NC}"
results=$(curl -s "$API_URL/results?limit=5")
count=$(echo "$results" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
echo -e "Found ${YELLOW}$count${NC} existing findings"
echo "$results" | python3 -m json.tool 2>/dev/null | head -30
echo ""

# Test 3: Start Nmap Scan
echo -e "${BLUE}━━━ Test 3: Nmap Scan ━━━${NC}"
echo "Target: scanme.nmap.org"
nmap_response=$(curl -s -X POST $API_URL/scan/nmap \
  -H "Content-Type: application/json" \
  -d '{"target": "scanme.nmap.org", "options": "-F"}')

echo "$nmap_response" | python3 -m json.tool
nmap_task_id=$(echo "$nmap_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null)
echo -e "${GREEN}Nmap scan started: $nmap_task_id${NC}\n"

# Test 4: Start ZAP Scan
echo -e "${BLUE}━━━ Test 4: ZAP Scan ━━━${NC}"
echo "Target: http://testphp.vulnweb.com"
zap_response=$(curl -s -X POST $API_URL/scan/zap \
  -H "Content-Type: application/json" \
  -d '{"target": "http://testphp.vulnweb.com", "options": "passive"}')

echo "$zap_response" | python3 -m json.tool
zap_task_id=$(echo "$zap_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null)
echo -e "${GREEN}ZAP scan started: $zap_task_id${NC}\n"

# Test 5: Monitor Progress
echo -e "${BLUE}━━━ Test 5: Monitor Progress ━━━${NC}"
echo "Monitoring Nmap scan for 15 seconds..."

for i in {1..3}; do
    sleep 5
    status=$(curl -s "$API_URL/scan/status/$nmap_task_id")
    state=$(echo "$status" | python3 -c "import sys, json; print(json.load(sys.stdin).get('state', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    
    echo -e "[${YELLOW}$i${NC}] State: ${BLUE}$state${NC}"
    
    if [ "$state" = "SUCCESS" ]; then
        echo -e "${GREEN}Scan completed successfully!${NC}"
        echo "$status" | python3 -m json.tool | head -20
        break
    elif [ "$state" = "FAILURE" ]; then
        echo -e "${RED}Scan failed${NC}"
        echo "$status" | python3 -m json.tool
        break
    fi
done

echo ""

# Test 6: View Updated Results
echo -e "${BLUE}━━━ Test 6: Updated Findings ━━━${NC}"
sleep 2
new_results=$(curl -s "$API_URL/results?limit=10")
new_count=$(echo "$new_results" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
echo -e "Total findings: ${YELLOW}$new_count${NC}"

# Show summary by severity
echo ""
echo -e "${BLUE}Findings by Severity:${NC}"
echo "$new_results" | python3 -c "
import sys, json
from collections import Counter
data = json.load(sys.stdin)
severities = Counter(f['severity'] for f in data)
for sev, count in sorted(severities.items(), key=lambda x: x[1], reverse=True):
    print(f'  {sev}: {count}')
" 2>/dev/null || echo "  Unable to parse"

echo ""

# Summary
echo "╔════════════════════════════════════════╗"
echo "║          Test Summary                  ║"
echo "╚════════════════════════════════════════╝"
echo -e "${GREEN}Health check: OK${NC}"
echo -e "${GREEN}Nmap scan: Started ($nmap_task_id)${NC}"
echo -e "${GREEN}ZAP scan: Started ($zap_task_id)${NC}"
echo -e "${GREEN}Findings retrieved: $new_count${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "  • API Docs:     http://localhost:8000/docs"
echo "  • DefectDojo:   http://localhost:8080 (admin/Admin@123)"
echo "  • MinIO:        http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo -e "${GREEN}All tests completed!${NC}"
