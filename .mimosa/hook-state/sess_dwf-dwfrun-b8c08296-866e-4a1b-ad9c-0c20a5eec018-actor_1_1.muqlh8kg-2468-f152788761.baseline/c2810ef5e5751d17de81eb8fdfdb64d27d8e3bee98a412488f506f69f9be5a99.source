#!/bin/bash
# SCP Linux Boot Reality Check
# Ensures that on a clean Linux environment, the server boots without crashing,
# and /health binds and responds.

set -e
echo "========================================="
echo " SCP Linux Boot E2E Test (Reality Check)"
echo "========================================="

export SCP_ADMIN_KEY="test-admin-token"
export SCP_OLLAMA_HOST="http://127.0.0.1:11434"
export SCP_DEEP_AUDIT_INTERVAL_SEC="86400"

echo "[1/3] Testing Static Imports..."
python3 -c "
import sys
try:
    from scp.api_server import app
    print('  -> Imports OK')
except Exception as e:
    print('  -> FAILED:', str(e))
    sys.exit(1)
"

echo "[2/3] Booting API Server in background..."
PORT=18765
python3 -m uvicorn scp.api_server:app --port $PORT --host 127.0.0.1 > boot.log 2>&1 &
SERVER_PID=$!

echo "  -> Server PID: $SERVER_PID"
sleep 5

echo "[3/3] Checking /health endpoint..."
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health || echo "000")

kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true
rm -f boot.log

if [ "$STATUS_CODE" = "200" ]; then
    echo "  -> /health responded with 200 OK."
    echo "========================================="
    echo " BOOT TEST PASSED"
    echo "========================================="
    exit 0
else
    echo "  -> FAILED: /health responded with $STATUS_CODE"
    echo "========================================="
    echo " BOOT TEST FAILED"
    echo "========================================="
    exit 1
fi
