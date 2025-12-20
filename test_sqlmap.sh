#!/bin/bash
set -e
API="http://localhost:8000"
TARGET="http://testphp.vulnweb.com/listproducts.php?cat=1"

echo "Start SQLMap"
resp=$(curl -s -X POST "$API/scan/sqlmap" \
  -H "Content-Type: application/json" \
  -d "{\"target\": \"$TARGET\"}")

echo "Response:" 
echo "$resp" | python3 -m json.tool

task=$(echo "$resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["task_id"])')
echo "Task: $task"

echo "Polling..."
for i in {1..8}; do
  sleep 5
  status=$(curl -s "$API/scan/status/$task")
  state=$(echo "$status" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("state"))')
  echo "[$i] $state"
  echo "$status" | python3 -m json.tool | head -30
  [ "$state" = "SUCCESS" ] && break
  [ "$state" = "FAILURE" ] && break
done
