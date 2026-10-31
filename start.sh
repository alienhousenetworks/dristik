#!/usr/bin/env bash

# ==============================================================================
# Dristik AI — Unified Full-Stack Run Script (Frontend + Backend + DB)
# ==============================================================================
# Usage:
#   ./run.sh              # Start Frontend + Backend + DB (Streams Backend Logs)
#   ./run.sh --debug      # Start with backend debug log level
#   ./run.sh --docker     # Start Full-Stack via Docker Compose
#   ./run.sh --test       # Run test suite before launching
#   ./run.sh --backend    # Run Backend only (port 8000)
#   ./run.sh --frontend   # Run Frontend only (port 5173)
#   ./run.sh --with-db    # Start local DB/Redis container with native dev servers
# ==============================================================================

set -e

# Terminal colors
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
DIM='\033[2m'
RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
BACKEND_LOG="${ROOT_DIR}/backend.log"
FRONTEND_LOG="${ROOT_DIR}/frontend.log"

BACKEND_PID=""
FRONTEND_PID=""
TAIL_PID=""
DB_CONTAINER_STARTED=false
LOG_LEVEL="info"
ENABLE_RELOAD=true

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "  ██████╗ ██████╗ ██╗███████╗████████╗██╗██╗  ██╗    █████╗ ██╗"
    echo "  ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝██║██║ ██╔╝   ██╔══██╗██║"
    echo "  ██║  ██║██████╔╝██║███████╗   ██║   ██║█████╔╝    ███████║██║"
    echo "  ██║  ██║██╔══██╗██║╚════██║   ██║   ██║██╔═██╗    ██╔══██║██║"
    echo "  ██████╔╝██║  ██║██║███████║   ██║   ██║██║  ██╗██╗██║  ██║██║"
    echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝"
    echo -e "${RESET}"
    echo -e "  ${BOLD}Enterprise Evidence-Driven Website Intelligence & Growth Auditor${RESET}"
    echo -e "  ${DIM}Unified Full-Stack Launcher (Frontend + Backend + DB)${RESET}"
    echo "  ----------------------------------------------------------------"
    echo ""
}

# ------------------------------------------------------------------------------
# Cleanup handler on exit or Ctrl+C
# ------------------------------------------------------------------------------
cleanup() {
    # If no services or tail were started, exit silently
    if [ -z "${BACKEND_PID}" ] && [ -z "${FRONTEND_PID}" ] && [ -z "${TAIL_PID}" ] && [ "$DB_CONTAINER_STARTED" != true ]; then
        exit 0
    fi

    echo ""
    echo -e "${YELLOW}>> Shutting down all Dristik AI services cleanly...${RESET}"
    
    # Terminate tail first so terminal log streaming stops immediately
    if [ -n "${TAIL_PID}" ] && kill -0 "${TAIL_PID}" 2>/dev/null; then
        kill -TERM "${TAIL_PID}" 2>/dev/null || true
    fi

    if [ -n "${BACKEND_PID}" ] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
        echo -e "${DIM}  Stopping Backend (PID ${BACKEND_PID})...${RESET}"
        kill -TERM "${BACKEND_PID}" 2>/dev/null || true
    fi

    if [ -n "${FRONTEND_PID}" ] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        echo -e "${DIM}  Stopping Frontend (PID ${FRONTEND_PID})...${RESET}"
        kill -TERM "${FRONTEND_PID}" 2>/dev/null || true
    fi

    if [ "$DB_CONTAINER_STARTED" = true ]; then
        if command -v docker >/dev/null 2>&1; then
            echo -e "${DIM}  Stopping local DB containers...${RESET}"
            docker compose stop db redis 2>/dev/null || true
        fi
    fi

    # Free ports 8000 and 5173 if lingering
    check_and_free_port 8000 "Backend" >/dev/null 2>&1 || true
    check_and_free_port 5173 "Frontend" >/dev/null 2>&1 || true

    sleep 0.5
    echo -e "${GREEN}✓ All services stopped. Goodbye!${RESET}"
    exit 0
}

trap cleanup INT TERM EXIT

# ------------------------------------------------------------------------------
# Port check and kill stale processes
# ------------------------------------------------------------------------------
check_and_free_port() {
    local port=$1
    local name=$2
    local pids
    pids=$(lsof -ti :${port} 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠ Port ${port} (${name}) is currently in use by PID(s): ${pids}.${RESET}"
        echo -e "${DIM}  Releasing port ${port}...${RESET}"
        kill -9 ${pids} 2>/dev/null || true
        sleep 1
    fi
}

# ------------------------------------------------------------------------------
# Environment and dependency validations
# ------------------------------------------------------------------------------
validate_environment() {
    echo -e "${BLUE}▶ Checking system prerequisites...${RESET}"

    # Python check
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: python3 is not installed or not in PATH.${RESET}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${RESET} Python $(python3 --version | cut -d' ' -f2)"

    # Node.js & npm check
    if ! command -v node >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: node is not installed or not in PATH.${RESET}"
        exit 1
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: npm is not installed or not in PATH.${RESET}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${RESET} Node $(node --version), npm $(npm --version)"

    # Check .env in backend
    if [ ! -f "${BACKEND_DIR}/.env" ]; then
        if [ -f "${BACKEND_DIR}/.env.example" ]; then
            echo -e "${YELLOW}⚠ backend/.env not found. Creating from .env.example...${RESET}"
            cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
            echo -e "  ${GREEN}✓${RESET} Created backend/.env"
        fi
    fi

    # Check backend virtual environment
    if [ ! -d "${BACKEND_DIR}/venv" ] || [ ! -f "${BACKEND_DIR}/venv/.installed" ]; then
        if [ ! -d "${BACKEND_DIR}/venv" ]; then
            echo -e "${YELLOW}⚠ Virtual environment not found in backend/venv. Creating...${RESET}"
            python3 -m venv "${BACKEND_DIR}/venv"
            echo -e "  ${GREEN}✓${RESET} Created virtualenv"
        fi
        echo -e "${DIM}  Installing backend requirements...${RESET}"
        "${BACKEND_DIR}/venv/bin/pip" install --upgrade pip
        "${BACKEND_DIR}/venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
        PLAYWRIGHT_SKIP_FFMPEG_INSTALL=1 "${BACKEND_DIR}/venv/bin/playwright" install chromium 2>/dev/null || true
        touch "${BACKEND_DIR}/venv/.installed"
        echo -e "  ${GREEN}✓${RESET} Backend dependencies installed"
    fi

    # Check frontend node_modules
    if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
        echo -e "${YELLOW}⚠ node_modules not found in frontend. Installing...${RESET}"
        (cd "${FRONTEND_DIR}" && npm install --silent)
        echo -e "  ${GREEN}✓${RESET} Frontend dependencies installed"
    fi
    echo ""
}

# ------------------------------------------------------------------------------
# Start DB / Cache (Docker or Local state)
# ------------------------------------------------------------------------------
start_database() {
    echo -e "${MAGENTA}▶ Initializing Database & Evidence Store Layer...${RESET}"
    
    if [ "$WITH_DB_CONTAINER" = true ]; then
        if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
            echo -e "  ${CYAN}Starting PostgreSQL & Redis via Docker...${RESET}"
            (cd "${ROOT_DIR}" && docker compose up -d db redis)
            DB_CONTAINER_STARTED=true
            echo -e "  ${GREEN}✓${RESET} Database containers running."
        else
            echo -e "  ${YELLOW}⚠ Docker daemon is not active. Using embedded Evidence & Ledger Store.${RESET}"
        fi
    else
        echo -e "  ${GREEN}✓${RESET} Active: High-Speed In-Memory Deterministic Evidence Store & Cryptographic Ledger"
    fi
    echo ""
}

# ------------------------------------------------------------------------------
# Preload / Install AI Vector Embedding Model (intfloat/e5-small-v2)
# ------------------------------------------------------------------------------
ensure_embedding_model() {
    echo -e "${MAGENTA}▶ Verifying & Installing AI Vector Embedding Model (E5-Small: ~130 MB, 384-dim)...${RESET}"
    if [ -f "${BACKEND_DIR}/venv/bin/python" ]; then
        (
            cd "${BACKEND_DIR}" && \
            # Source HF_TOKEN from .env if present
            if [ -f "${BACKEND_DIR}/.env" ]; then
                export $(grep -v '^#' "${BACKEND_DIR}/.env" | grep -E '^(HF_TOKEN|HUGGINGFACE_TOKEN)=' | xargs) 2>/dev/null || true
            fi
            PYTHONPATH=. "${BACKEND_DIR}/venv/bin/python" -c "
import os, sys
try:
    print('  Checking local Hugging Face cache for intfloat/e5-small-v2 (~130 MB)...')
    from sentence_transformers import SentenceTransformer
    token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
    extra = {'token': token} if token else {}
    SentenceTransformer('intfloat/e5-small-v2', **extra)
    print('  \033[0;32m✓\033[0m Local E5-Small embedding model (384-dim) is verified and ready.')
except Exception as e:
    print(f'  \033[0;33m⚠\033[0m Embedding model preload notice: {e}')
    print('  (Analysis pipeline will use runtime embedding fallback if unavailable)')
"
        )
    fi
    echo ""
}

# ------------------------------------------------------------------------------
# Run Tests (Optional)
# ------------------------------------------------------------------------------
run_tests() {
    echo -e "${BLUE}▶ Running Backend Pipeline Test Suite...${RESET}"
    (cd "${BACKEND_DIR}" && PYTHONPATH=. "${BACKEND_DIR}/venv/bin/pytest" tests/test_pipeline.py -q)
    echo -e "  ${GREEN}✓ Backend tests passed successfully!${RESET}"
    echo ""
}

# ------------------------------------------------------------------------------
# Start Backend
# ------------------------------------------------------------------------------
start_backend() {
    echo -e "${GREEN}▶ Starting FastAPI Backend Gateway (port 8000)...${RESET}"
    check_and_free_port 8000 "Backend FastAPI"

    # Reset backend log file
    : > "${BACKEND_LOG}"

    local reload_args=()
    if [ "$ENABLE_RELOAD" = true ]; then
        reload_args=(
            "--reload"
            "--reload-dir" "${BACKEND_DIR}/app"
            "--reload-exclude" "data/*"
            "--reload-exclude" "*.db"
            "--reload-exclude" "*.log"
        )
    fi

    (
        cd "${BACKEND_DIR}" && \
        export PYTHONUNBUFFERED=1 && \
        exec "${BACKEND_DIR}/venv/bin/python" -m uvicorn app.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            "${reload_args[@]}" \
            --use-colors \
            --access-log \
            --log-level "${LOG_LEVEL}"
    ) > "${BACKEND_LOG}" 2>&1 &
    BACKEND_PID=$!

    # Wait for backend health check
    local retries=40
    local ready=false
    while [ $retries -gt 0 ]; do
        # Detect early crash on startup
        if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
            echo -e "  ${RED}✗ Backend process terminated unexpectedly during startup!${RESET}"
            echo -e "${RED}--- Backend Startup Log (${BACKEND_LOG}) ---${RESET}"
            cat "${BACKEND_LOG}"
            echo -e "${RED}------------------------------------------------${RESET}"
            exit 1
        fi

        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            ready=true
            break
        fi
        sleep 0.3
        retries=$((retries - 1))
    done

    if [ "$ready" = true ]; then
        echo -e "  ${GREEN}✓${RESET} Backend is healthy and ready at ${BOLD}http://localhost:8000${RESET}"
    else
        echo -e "  ${YELLOW}⚠ Backend started (PID ${BACKEND_PID}), health check pending...${RESET}"
    fi
    echo ""
}

# ------------------------------------------------------------------------------
# Start Frontend
# ------------------------------------------------------------------------------
start_frontend() {
    echo -e "${CYAN}▶ Starting Vite Frontend Dashboard (port 5173)...${RESET}"
    check_and_free_port 5173 "Frontend Vite"

    # Reset frontend log file
    : > "${FRONTEND_LOG}"

    (
        cd "${FRONTEND_DIR}" && \
        exec npm run dev -- --host 0.0.0.0 --port 5173 --clearScreen false
    ) > "${FRONTEND_LOG}" 2>&1 &
    FRONTEND_PID=$!

    local retries=40
    local ready=false
    while [ $retries -gt 0 ]; do
        # Detect early crash on startup
        if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
            echo -e "  ${RED}✗ Frontend process terminated unexpectedly during startup!${RESET}"
            echo -e "${RED}--- Frontend Startup Log (${FRONTEND_LOG}) ---${RESET}"
            cat "${FRONTEND_LOG}"
            echo -e "${RED}------------------------------------------------${RESET}"
            exit 1
        fi

        if curl -s http://localhost:5173 >/dev/null 2>&1; then
            ready=true
            break
        fi
        sleep 0.3
        retries=$((retries - 1))
    done

    if [ "$ready" = true ]; then
        echo -e "  ${GREEN}✓${RESET} Frontend is live at ${BOLD}http://localhost:5173${RESET}"
    else
        echo -e "  ${YELLOW}⚠ Frontend started (PID ${FRONTEND_PID})...${RESET}"
    fi
    echo ""
}

# ------------------------------------------------------------------------------
# Docker Compose full runner
# ------------------------------------------------------------------------------
run_docker_compose() {
    echo -e "${BLUE}▶ Starting Dristik AI full stack via Docker Compose...${RESET}"
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: Docker is not installed.${RESET}"
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: Docker daemon is not running. Please start Docker Desktop.${RESET}"
        exit 1
    fi

    (cd "${ROOT_DIR}" && docker compose up --build)
    exit 0
}

# ------------------------------------------------------------------------------
# Main Dispatcher
# ------------------------------------------------------------------------------
MODE="all"
WITH_DB_CONTAINER=false
RUN_TESTS=false
PRELOAD_MODEL=true

for arg in "$@"; do
    case $arg in
        --docker)
            MODE="docker"
            ;;
        --with-db|--db)
            WITH_DB_CONTAINER=true
            ;;
        --test|--tests)
            RUN_TESTS=true
            ;;
        --backend|--backend-only)
            MODE="backend"
            ;;
        --frontend|--frontend-only)
            MODE="frontend"
            ;;
        --install-model|--download-model|--preload-model)
            MODE="install-model"
            ;;
        --skip-model|--no-model|--skip-embedding)
            PRELOAD_MODEL=false
            ;;
        --debug)
            LOG_LEVEL="debug"
            ;;
        --no-reload)
            ENABLE_RELOAD=false
            ;;
        --log-level=*)
            LOG_LEVEL="${arg#*=}"
            ;;
        --help|-h)
            print_banner
            echo "Options:"
            echo "  ./start.sh                       Start full stack (Live backend logs streamed to terminal)"
            echo "  ./start.sh --install-model       Preload & cache Hugging Face E5-Small embedding model only"
            echo "  ./start.sh --skip-model          Start full stack skipping local embedding model verification"
            echo "  ./start.sh --debug               Start with backend debug log level"
            echo "  ./start.sh --log-level=LEVEL     Set uvicorn log level (debug, info, warning, error)"
            echo "  ./start.sh --backend             Start Backend only (port 8000)"
            echo "  ./start.sh --frontend            Start Frontend only (port 5173)"
            echo "  ./start.sh --with-db             Start with background Docker Postgres/Redis if available"
            echo "  ./start.sh --docker              Start everything via Docker Compose"
            echo "  ./start.sh --test                Run backend pipeline tests before starting"
            echo "  ./start.sh --help                Show this help dialog"
            exit 0
            ;;
    esac
done

print_banner

if [ "$MODE" = "docker" ]; then
    run_docker_compose
fi

validate_environment

if [ "$MODE" = "install-model" ]; then
    ensure_embedding_model
    echo -e "${GREEN}✓ E5-Small embedding model installation complete.${RESET}"
    exit 0
fi

if [ "$RUN_TESTS" = true ]; then
    run_tests
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "backend" ]; then
    start_database
    if [ "$PRELOAD_MODEL" = true ]; then
        ensure_embedding_model
    fi
    start_backend
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "frontend" ]; then
    start_frontend
fi

# Print ready summary
echo "================================================================"
echo -e "${GREEN}${BOLD}  🚀 DRISTIK AI IS FULLY OPERATIONAL!${RESET}"
echo "================================================================"
echo -e "  ${BOLD}🖥️  Frontend Dashboard:${RESET}    ${CYAN}http://localhost:5173${RESET}"
echo -e "  ${BOLD}⚡ Backend API Gateway:${RESET}   ${CYAN}http://localhost:8000${RESET}"
echo -e "  ${BOLD}📖 Interactive Docs:${RESET}      ${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  ${BOLD}🩺 Health Check:${RESET}          ${CYAN}http://localhost:8000/health${RESET}"
echo -e "  ${BOLD}📄 Frontend Log:${RESET}          ${DIM}${FRONTEND_LOG}${RESET}"
echo -e "  ${BOLD}📄 Backend Log:${RESET}           ${DIM}${BACKEND_LOG}${RESET}"
echo "================================================================"
echo -e "${DIM}  Press Ctrl+C at any time to cleanly stop all services.${RESET}"
echo ""

if [ "$MODE" = "frontend" ]; then
    echo -e "${CYAN}${BOLD}▶ Streaming Frontend Logs (tail -f):${RESET}"
    echo -e "${DIM}----------------------------------------------------------------${RESET}"
    tail -n +1 -f "${FRONTEND_LOG}" &
    TAIL_PID=$!
else
    echo -e "${GREEN}${BOLD}▶ Streaming Live Backend Logs (tail -f):${RESET}"
    echo -e "${DIM}----------------------------------------------------------------${RESET}"
    tail -n +1 -f "${BACKEND_LOG}" &
    TAIL_PID=$!
fi

# Keep parent script running and monitor processes
while true; do
    if [ -n "${BACKEND_PID}" ] && ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ Backend server process (PID ${BACKEND_PID}) stopped unexpectedly.${RESET}"
        break
    fi
    if [ -n "${FRONTEND_PID}" ] && ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        echo ""
        echo -e "${RED}✗ Frontend server process (PID ${FRONTEND_PID}) stopped unexpectedly.${RESET}"
        break
    fi
    sleep 1
done
