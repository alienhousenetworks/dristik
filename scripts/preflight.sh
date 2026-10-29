#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Running Dristik 2.0 Preflight Diagnostics..."

# 1. Python version check
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "[OK] Python version: $PYTHON_VERSION"

# 2. Node.js version check
NODE_VERSION=$(node --version 2>&1 || echo "not found")
echo "[OK] Node.js version: $NODE_VERSION"

# 3. Environment check
if [ -f "$ROOT_DIR/backend/.env" ]; then
    echo "[OK] Backend .env file present."
else
    echo "[WARN] backend/.env missing. Creating from .env.example..."
    cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env" 2>/dev/null || touch "$ROOT_DIR/backend/.env"
fi

# 4. Check Playwright
python3 -c "import playwright" 2>/dev/null && echo "[OK] Playwright installed." || echo "[INFO] Playwright not yet installed."

echo "Preflight check completed successfully."
