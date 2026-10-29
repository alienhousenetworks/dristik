#!/usr/bin/env bash

# ==============================================================================
# Dristik AI — Primary Production Deployment Script
# ==============================================================================
# Official Repository: https://github.com/alienhousenetworks/dristik.git
# Usage:
#   ./deploy.sh            # Complete end-to-end deployment (setup + git sync + build)
#   ./deploy.sh --no-pull  # Deploy current code without git sync
#   ./deploy.sh --setup    # Run environment initialization only
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
REPO_URL="https://github.com/alienhousenetworks/dristik.git"
REPO_BRANCH="main"

echo -e "${CYAN}${BOLD}"
echo "  ██████╗ ██████╗ ██╗███████╗████████╗██╗██╗  ██╗    █████╗ ██╗"
echo "  ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝██║██║ ██╔╝   ██╔══██╗██║"
echo "  ██║  ██║██████╔╝██║███████╗   ██║   ██║█████╔╝    ███████║██║"
echo "  ██║  ██║██╔══██╗██║╚════██║   ██║   ██║██╔═██╗    ██╔══██║██║"
echo "  ██████╔╝██║  ██║██║███████║   ██║   ██║██║  ██╗██╗██║  ██║██║"
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝"
echo -e "${RESET}"
echo -e "  ${BOLD}Official Deployment Suite — ${REPO_URL}${RESET}"
echo "  ----------------------------------------------------------------"
echo ""

# Handle --help
for arg in "$@"; do
    if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
        echo "Usage: ./deploy.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  ./deploy.sh            Full deploy: verifies environment, syncs repo, builds and runs containers"
        echo "  ./deploy.sh --no-pull  Build and deploy current local code without git pull"
        echo "  ./deploy.sh --setup    Run host setup (Swap, Docker, .env) only"
        echo "  ./deploy.sh --help     Show this message"
        echo ""
        exit 0
    fi
    if [ "$arg" = "--setup" ]; then
        bash "${ROOT_DIR}/setup.sh"
        exit 0
    fi
done

# Step 1: Ensure host environment and .env exist
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚡ Initializing server environment and generating .env...${RESET}"
    bash "${ROOT_DIR}/setup.sh"
fi

# Step 2: Ensure git remote origin points to updated repository
if [ -d "${ROOT_DIR}/.git" ]; then
    CURRENT_ORIGIN=$(git config --get remote.origin.url 2>/dev/null || true)
    if [ -z "$CURRENT_ORIGIN" ]; then
        git remote add origin "$REPO_URL" 2>/dev/null || true
        echo -e "${GREEN}✓ Set origin to official repo: ${REPO_URL}${RESET}"
    elif [ "$CURRENT_ORIGIN" != "$REPO_URL" ] && [ "$CURRENT_ORIGIN" != "git@github.com:alienhousenetworks/dristik.git" ]; then
        echo -e "${YELLOW}⚡ Updating git remote origin: ${CURRENT_ORIGIN} -> ${REPO_URL}${RESET}"
        git remote set-url origin "$REPO_URL" 2>/dev/null || true
    fi
fi

# Step 3: Ensure scripts are executable
chmod +x "${ROOT_DIR}/deploy.sh" "${ROOT_DIR}/redeploy.sh" "${ROOT_DIR}/setup.sh" "${ROOT_DIR}/start.sh" 2>/dev/null || true

# Step 4: Delegate to redeploy.sh for container build, healthcheck & live status
exec "${ROOT_DIR}/redeploy.sh" "$@"
