#!/usr/bin/env bash
set -e

echo "Starting Dristik 2.0 Development Environment..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to kill child processes on exit
cleanup() {
    echo "Stopping development servers..."
    kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT SIGINT SIGTERM

# Determine Python / Uvicorn runner
UVICORN_CMD="uvicorn"
if [ -f "$ROOT_DIR/backend/venv/bin/uvicorn" ]; then
    UVICORN_CMD="$ROOT_DIR/backend/venv/bin/uvicorn"
elif [ -f "$ROOT_DIR/backend/.venv/bin/uvicorn" ]; then
    UVICORN_CMD="$ROOT_DIR/backend/.venv/bin/uvicorn"
fi

# 1. Start Backend FastAPI
echo "Starting FastAPI Backend on port 8000..."
cd "$ROOT_DIR/backend"
$UVICORN_CMD app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 2. Start Frontend Vite
echo "Starting React Vite Frontend on port 5173..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  Dristik 2.0 is running!"
echo "  Backend API:   http://localhost:8000"
echo "  Swagger Docs:  http://localhost:8000/docs"
echo "  Frontend UI:   http://localhost:5173"
echo "=========================================================="
echo ""

wait
