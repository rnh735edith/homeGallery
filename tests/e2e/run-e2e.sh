#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PORT=8080
HEALTH_URL="http://localhost:${PORT}/health"
SERVER_PID=""
MAX_WAIT=30
TEST_TIMEOUT=300

cleanup() {
    echo "Cleaning up..."
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    # Kill any leftover python processes on our port
    lsof -ti:${PORT} | xargs -r kill -9 2>/dev/null || true
    echo "Cleanup done."
}
trap cleanup EXIT INT TERM

echo "=== E2E Test Runner ==="
echo "Project root: $PROJECT_ROOT"

# Step 1: Kill existing server on port
echo "[1/5] Checking for existing server on port ${PORT}..."
if lsof -i:${PORT} >/dev/null 2>&1; then
    echo "  Found process on port ${PORT}, killing..."
    lsof -ti:${PORT} | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Step 2: Setup test environment
echo "[2/5] Setting up test environment..."
cd "$PROJECT_ROOT"
python tests/e2e/setup_test_env.py

# Step 3: Build frontend
echo "[3/5] Building frontend..."
cd "$PROJECT_ROOT/frontend"
npm run build --silent 2>/dev/null || echo "  Build skipped (already built)"

# Step 4: Start server
echo "[4/5] Starting server..."
cd "$PROJECT_ROOT"
python manage.py start
sleep 2

# Find the server PID
SERVER_PID=$(lsof -ti:${PORT} 2>/dev/null | head -1) || true
if [ -z "$SERVER_PID" ]; then
    echo "ERROR: Server did not start on port ${PORT}"
    exit 1
fi
echo "  Server started (PID: $SERVER_PID)"

# Wait for health check
echo "  Waiting for health check..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        echo "  Server is ready!"
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: Server did not become ready within ${MAX_WAIT}s"
    echo "  Server log:"
    cat "$PROJECT_ROOT/data/server.log" 2>/dev/null || echo "  (no log file)"
    exit 1
fi

# Step 5: Run tests
echo "[5/5] Running E2E tests (timeout: ${TEST_TIMEOUT}s)..."
cd "$PROJECT_ROOT"

# Run playwright tests with timeout
timeout "${TEST_TIMEOUT}" npx playwright test --reporter=list "$@"
TEST_EXIT=$?

if [ $TEST_EXIT -eq 124 ]; then
    echo "ERROR: Tests timed out after ${TEST_TIMEOUT}s"
    exit 124
fi

exit $TEST_EXIT
