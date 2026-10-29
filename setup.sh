#!/usr/bin/env bash

# ==============================================================================
# Dristik AI — Production Server Setup Script
# ==============================================================================
# Sets up Docker, Docker Compose, 4GB Swap memory, and initializes .env
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# ==============================================================================

set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"

# Helper to check for sudo or root
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo -e "${RED}✗ Error: This script requires root privileges or sudo access.${RESET}"
        exit 1
    fi
fi

echo -e "${CYAN}${BOLD}"
echo "  ██████╗ ██████╗ ██╗███████╗████████╗██╗██╗  ██╗    █████╗ ██╗"
echo "  ██╔══██╗██╔══██╗██║██╔════╝╚══██╔══╝██║██║ ██╔╝   ██╔══██╗██║"
echo "  ██║  ██║██████╔╝██║███████╗   ██║   ██║█████╔╝    ███████║██║"
echo "  ██║  ██║██╔══██╗██║╚════██║   ██║   ██║██╔═██╗    ██╔══██║██║"
echo "  ██████╔╝██║  ██║██║███████║   ██║   ██║██║  ██╗██╗██║  ██║██║"
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝"
echo -e "${RESET}"
echo -e "  ${BOLD}Server Initialization & Environment Setup${RESET}"
echo "  ----------------------------------------------------------------"
echo ""

# ------------------------------------------------------------------------------
# 1. Setup 4GB Swap (Essential for 4GB RAM VPS)
# ------------------------------------------------------------------------------
echo -e "${CYAN}▶ Step 1: Checking system swap memory...${RESET}"
CURRENT_SWAP_KB=$(grep SwapTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
CURRENT_SWAP_MB=$((CURRENT_SWAP_KB / 1024))

if [ "$CURRENT_SWAP_MB" -lt 2000 ]; then
    echo -e "  ${YELLOW}Detected only ${CURRENT_SWAP_MB}MB swap. Creating 4GB swapfile to prevent out-of-memory errors...${RESET}"
    if [ ! -f /swapfile ]; then
        $SUDO fallocate -l 4G /swapfile 2>/dev/null || $SUDO dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress
        $SUDO chmod 600 /swapfile
        $SUDO mkswap /swapfile
        $SUDO swapon /swapfile
        if ! grep -q "/swapfile" /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab >/dev/null
        fi
        echo -e "  ${GREEN}✓ 4GB Swapfile configured and activated successfully.${RESET}"
    else
        $SUDO swapon /swapfile 2>/dev/null || true
        echo -e "  ${GREEN}✓ Existing /swapfile activated.${RESET}"
    fi
else
    echo -e "  ${GREEN}✓ Swap memory already sufficient (${CURRENT_SWAP_MB}MB).${RESET}"
fi
echo ""

# ------------------------------------------------------------------------------
# 2. Check and Install Docker & Docker Compose
# ------------------------------------------------------------------------------
echo -e "${CYAN}▶ Step 2: Verifying Docker installation...${RESET}"

if ! command -v docker >/dev/null 2>&1; then
    echo -e "  ${YELLOW}Docker is not installed. Installing Docker Engine via official automated script...${RESET}"
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    $SUDO sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
    
    $SUDO systemctl enable docker || true
    $SUDO systemctl start docker || true

    if [ -n "$SUDO" ] && [ -n "$USER" ]; then
        $SUDO usermod -aG docker "$USER" 2>/dev/null || true
    fi
    echo -e "  ${GREEN}✓ Docker installed successfully.${RESET}"
else
    echo -e "  ${GREEN}✓ Docker is already installed: $(docker --version)${RESET}"
fi

# Ensure docker daemon is running
if ! $SUDO docker info >/dev/null 2>&1; then
    echo -e "  ${YELLOW}Starting Docker daemon...${RESET}"
    $SUDO systemctl start docker || true
fi

# Check Docker Compose (v2 plugin)
if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "  ${YELLOW}Installing Docker Compose plugin...${RESET}"
    $SUDO apt-get update -y && $SUDO apt-get install -y docker-compose-plugin || true
fi
echo -e "  ${GREEN}✓ Docker Compose is ready.${RESET}"
echo ""

# ------------------------------------------------------------------------------
# 3. Initialize Production .env File
# ------------------------------------------------------------------------------
echo -e "${CYAN}▶ Step 3: Configuring environment settings...${RESET}"

if [ -f "$ENV_FILE" ]; then
    echo -e "  ${GREEN}✓ Existing .env file found at ${ENV_FILE}.${RESET}"
else
    echo -e "  ${YELLOW}Generating production .env file with cryptographically secure secrets...${RESET}"
    
    # Generate 64-character random hex secret for AUTH_SECRET
    RANDOM_AUTH_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Generate secure random admin password with mixed characters
    RANDOM_ADMIN_PASS="Dristik-$(openssl rand -hex 6 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(6))')!"

    cp "$ENV_EXAMPLE" "$ENV_FILE"

    # Replace generated secrets in .env
    # Using python for cross-platform safe in-place replacement
    python3 -c "
with open('${ENV_FILE}', 'r') as f:
    content = f.read()

content = content.replace('AUTH_SECRET=', 'AUTH_SECRET=${RANDOM_AUTH_SECRET}')
content = content.replace('SYSTEM_ADMIN_PASSWORD=', 'SYSTEM_ADMIN_PASSWORD=${RANDOM_ADMIN_PASS}')

with open('${ENV_FILE}', 'w') as f:
    f.write(content)
" 2>/dev/null || {
        sed -i.bak "s|^AUTH_SECRET=.*|AUTH_SECRET=${RANDOM_AUTH_SECRET}|" "$ENV_FILE"
        sed -i.bak "s|^SYSTEM_ADMIN_PASSWORD=.*|SYSTEM_ADMIN_PASSWORD=${RANDOM_ADMIN_PASS}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
    }

    # Also sync to backend/.env if needed
    cp "$ENV_FILE" "${ROOT_DIR}/backend/.env" 2>/dev/null || true

    echo -e "  ${GREEN}✓ Generated secure production .env successfully.${RESET}"
fi

# Ensure deploy.sh, redeploy.sh and start.sh are executable
chmod +x "${ROOT_DIR}/deploy.sh" "${ROOT_DIR}/redeploy.sh" "${ROOT_DIR}/setup.sh" "${ROOT_DIR}/start.sh" 2>/dev/null || true

echo ""
echo "================================================================"
echo -e "${GREEN}${BOLD}🎉 Host Setup Complete!${RESET}"
echo "================================================================"
echo ""
echo -e "Your initial Admin credentials (saved in ${BOLD}.env${RESET}):"
ADMIN_EMAIL=$(grep '^SYSTEM_ADMIN_EMAIL=' "$ENV_FILE" | cut -d '=' -f2- || echo "admin@dristik.ai")
ADMIN_PASS=$(grep '^SYSTEM_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2- || echo "(Check .env)")
echo -e "  ${BOLD}Email:${RESET}    ${ADMIN_EMAIL}"
echo -e "  ${BOLD}Password:${RESET} ${ADMIN_PASS}"
echo ""
echo -e "${BOLD}NEXT STEPS:${RESET}"
echo -e "1. Edit ${BOLD}.env${RESET} to insert your LLM API Key (OpenRouter, Anthropic, or Groq):"
echo -e "   ${CYAN}nano .env${RESET}"
echo ""
echo -e "2. Run the deployment script to build and launch the site:"
echo -e "   ${GREEN}./deploy.sh${RESET}  (or ./redeploy.sh)"
echo "================================================================"
echo ""
