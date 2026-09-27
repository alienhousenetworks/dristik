#!/usr/bin/env bash

# ==============================================================================
# Dristik AI — Production Deployment & Redeployment Script
# ==============================================================================
# Pulls latest changes, rebuilds containers, runs healthchecks, and launches.
# Usage:
#   ./redeploy.sh           # Pull git updates, rebuild & restart
#   ./redeploy.sh --no-pull # Rebuild & restart without pulling git
# ==============================================================================

set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
DIM='\033[2m'
RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

echo -e "${CYAN}${BOLD}"
echo "  ██████╗ ██████╗ ██╗███████╗████████╗██╗██╗  ██╗    █████╗ ██╗"
echo "  ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝██║██║ ██╔╝   ██╔══██╗██║"
echo "  ██║  ██║██████╔╝██║███████╗   ██║   ██║█████╔╝    ███████║██║"
echo "  ██║  ██║██╔══██╗██║╚════██║   ██║   ██║██╔═██╗    ██╔══██║██║"
echo "  ██████╔╝██║  ██║██║███████║   ██║   ██║██║  ██╗██╗██║  ██║██║"
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝"
echo -e "${RESET}"
echo -e "  ${BOLD}Automated Production Deployment${RESET}"
echo "  ----------------------------------------------------------------"
echo ""

# ------------------------------------------------------------------------------
# 1. Environment Verification
# ------------------------------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ Error: .env file not found at ${ENV_FILE}!${RESET}"
    echo -e "  Please run ${BOLD}./setup.sh${RESET} first to initialize your environment."
    exit 1
fi

# Load variables from .env
set -a
source "$ENV_FILE" 2>/dev/null || true
set +a

# Validate AUTH_SECRET length
if [ -z "$AUTH_SECRET" ] || [ ${#AUTH_SECRET} -lt 32 ] || [ "$AUTH_SECRET" = "dristik-dev-secret-change-me" ]; then
    echo -e "${RED}✗ Error: AUTH_SECRET in .env is missing or weaker than 32 characters!${RESET}"
    echo -e "  Generate one using: openssl rand -hex 32"
    exit 1
fi

# Validate SYSTEM_ADMIN_PASSWORD
if [ -z "$SYSTEM_ADMIN_PASSWORD" ] || [ "$SYSTEM_ADMIN_PASSWORD" = "DristikAdmin1!" ]; then
    echo -e "${YELLOW}⚠ Warning: Using default or empty SYSTEM_ADMIN_PASSWORD in .env.${RESET}"
fi

# Check Docker
DOCKER_CMD="docker"
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}✗ Error: Docker is not installed. Run ./setup.sh to install it.${RESET}"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    if sudo docker info >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
    else
        echo -e "${RED}✗ Error: Docker daemon is not running.${RESET}"
        exit 1
    fi
fi

# Check Docker Compose command syntax
if $DOCKER_CMD compose version >/dev/null 2>&1; then
    COMPOSE_CMD="$DOCKER_CMD compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}✗ Error: Neither 'docker compose' nor 'docker-compose' found.${RESET}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Optional Git Pull
# ------------------------------------------------------------------------------
SKIP_PULL=false
for arg in "$@"; do
    if [ "$arg" = "--no-pull" ]; then
        SKIP_PULL=true
    fi
done

if [ "$SKIP_PULL" = false ] && [ -d "${ROOT_DIR}/.git" ]; then
    echo -e "${CYAN}▶ Pulling latest code from git repository...${RESET}"
    git pull origin main 2>/dev/null || echo -e "  ${YELLOW}⚠ Git pull skipped (working directory dirty or branch up-to-date).${RESET}"
    echo ""
fi

# ------------------------------------------------------------------------------
# 3. Docker Compose Build & Launch
# ------------------------------------------------------------------------------
echo -e "${CYAN}▶ Building and starting containers in background...${RESET}"
cd "${ROOT_DIR}"

# Ensure backend/.env is synchronized with root .env
cp "${ENV_FILE}" "${ROOT_DIR}/backend/.env" 2>/dev/null || true

# Shut down any previous containers cleanly
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# Build and start services
$COMPOSE_CMD up -d --build

echo -e "  ${GREEN}✓ Containers built and started.${RESET}"
echo ""

# ------------------------------------------------------------------------------
# 4. Healthcheck
# ------------------------------------------------------------------------------
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo -e "${CYAN}▶ Waiting for backend healthcheck (http://localhost:${BACKEND_PORT}/health)...${RESET}"

RETRIES=40
HEALTHY=false
while [ $RETRIES -gt 0 ]; do
    if curl -s -f "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    printf "."
    sleep 2
    RETRIES=$((RETRIES - 1))
done
echo ""

if [ "$HEALTHY" = true ]; then
    echo -e "  ${GREEN}✓ Backend is healthy and ready!${RESET}"
else
    echo -e "  ${YELLOW}⚠ Healthcheck did not respond within timeout.${RESET}"
    echo -e "    Check container logs using: ${BOLD}${COMPOSE_CMD} logs api${RESET}"
fi

# ------------------------------------------------------------------------------
# 5. Public IP Detection & Deployment Summary
# ------------------------------------------------------------------------------
PUBLIC_IP=$(curl -s --max-time 3 https://api.ipify.org 2>/dev/null || curl -s --max-time 3 https://ifconfig.me 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_SERVER_IP")

echo ""
echo "================================================================"
echo -e "${GREEN}${BOLD}🚀 Dristik AI is Live & Operational!${RESET}"
echo "================================================================"
echo ""
echo -e "  ${BOLD}🌐 Web Dashboard:${RESET}    ${CYAN}http://${PUBLIC_IP}:${FRONTEND_PORT}${RESET}"
echo -e "  ${BOLD}🔌 Backend API:${RESET}      ${CYAN}http://${PUBLIC_IP}:${BACKEND_PORT}${RESET}"
echo -e "  ${BOLD}📚 API Documentation:${RESET} ${CYAN}http://${PUBLIC_IP}:${BACKEND_PORT}/docs${RESET}"
echo ""
echo -e "  ${BOLD}🔐 Admin Login:${RESET}"
echo -e "     Email:    ${BOLD}${SYSTEM_ADMIN_EMAIL:-admin@dristik.ai}${RESET}"
echo -e "     Password: ${BOLD}${SYSTEM_ADMIN_PASSWORD}${RESET}"
echo ""
echo -e "  ${BOLD}📋 Useful Operations:${RESET}"
echo -e "     • View live logs:     ${CYAN}${COMPOSE_CMD} logs -f${RESET}"
echo -e "     • Check container:    ${CYAN}${COMPOSE_CMD} ps${RESET}"
echo -e "     • Re-deploy updates:  ${CYAN}./redeploy.sh${RESET}"
echo -e "     • Stop services:      ${CYAN}${COMPOSE_CMD} down${RESET}"
echo "================================================================"
echo ""
