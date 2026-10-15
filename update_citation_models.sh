#!/usr/bin/env bash
# ==============================================================================
# Dristik AI — Production AI Citation Frontier Models Updater
# ==============================================================================
# Safely updates or creates .env configuration with OpenRouter as provider and
# top frontier models:
#   - Gemini:   google/gemini-3.8-flash
#   - OpenAI:   openai/gpt-6.1-sol
#   - Claude:   anthropic/claude-haiku-4.5
#   - Qwen:     qwen/qwen3.8-flash
#   - DeepSeek: deepseek/deepseek-v4.1-flash
#
# Usage:
#   ./update_citation_models.sh [OPENROUTER_API_KEY] [PATH_TO_ENV_FILE]
# Examples:
#   ./update_citation_models.sh
#   ./update_citation_models.sh sk-or-v1-xxxxxxxxxxxxxxxx
#   ./update_citation_models.sh sk-or-v1-xxxxxxxxxxxxxxxx backend/.env
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARG_KEY="${1:-}"
ARG_ENV="${2:-}"

# 1. Determine which .env file to update
ENV_FILE=""
if [ -n "$ARG_ENV" ] && [ -f "$ARG_ENV" ]; then
    ENV_FILE="$ARG_ENV"
elif [ -f "${ROOT_DIR}/.env" ]; then
    ENV_FILE="${ROOT_DIR}/.env"
elif [ -f "${ROOT_DIR}/backend/.env" ]; then
    ENV_FILE="${ROOT_DIR}/backend/.env"
elif [ -f ".env" ]; then
    ENV_FILE=".env"
elif [ -f "backend/.env" ]; then
    ENV_FILE="backend/.env"
else
    # Create .env if not found
    ENV_FILE="${ROOT_DIR}/.env"
    touch "$ENV_FILE"
    echo -e "${YELLOW}Notice: Created new ${ENV_FILE}${RESET}"
fi

echo -e "${CYAN}${BOLD}"
echo "=================================================================="
echo " Dristik AI: Configure AI Citation Frontier Models via OpenRouter"
echo "=================================================================="
echo -e "${RESET}"
echo -e "Target file: ${BOLD}${ENV_FILE}${RESET}"

# 2. Create timestamped backup
BACKUP_FILE="${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
echo -e "Backup created: ${GREEN}${BACKUP_FILE}${RESET}"

# 3. Handle OPENROUTER_API_KEY
if [ -n "$ARG_KEY" ]; then
    NEW_OR_KEY="$ARG_KEY"
else
    # Check if key already exists in target .env
    EXISTING_KEY=$(grep -E '^OPENROUTER_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    if [ -n "$EXISTING_KEY" ]; then
        NEW_OR_KEY="$EXISTING_KEY"
        echo -e "Retaining existing OPENROUTER_API_KEY (${NEW_OR_KEY:0:10}...)"
    else
        NEW_OR_KEY=""
    fi
fi

# Python-based atomic .env updater to preserve comments, format, and existing variables
python3 - <<EOF
import os
import sys

env_path = "$ENV_FILE"
new_or_key = "$NEW_OR_KEY"

# The target key-value pairs for the frontier model citation suite
target_settings = {
    "AI_CITATION_PROVIDER": "openrouter",
    "AI_CITATION_CROSS_PROVIDER": "true",

    # Claude
    "AI_CITATION_CLAUDE_ACTIVE": "true",
    "AI_CITATION_CLAUDE_PROVIDER": "openrouter",
    "AI_CITATION_CLAUDE_MODEL": "anthropic/claude-haiku-4.5",
    "AI_CITATION_CLAUDE_API_KEY": "",

    # Google Gemini
    "AI_CITATION_GEMINI_ACTIVE": "true",
    "AI_CITATION_GEMINI_PROVIDER": "openrouter",
    "AI_CITATION_GEMINI_MODEL": "google/gemini-3.8-flash",

    # OpenAI / ChatGPT
    "AI_CITATION_CHATGPT_ACTIVE": "true",
    "AI_CITATION_CHATGPT_PROVIDER": "openrouter",
    "AI_CITATION_CHATGPT_MODEL": "openai/gpt-oss-20b",

    # Qwen (Alibaba)
    "AI_CITATION_QWEN_ACTIVE": "true",
    "AI_CITATION_QWEN_PROVIDER": "openrouter",
    "AI_CITATION_QWEN_MODEL": "qwen/qwen3.8-flash",

    # DeepSeek
    "AI_CITATION_DEEPSEEK_ACTIVE": "true",
    "AI_CITATION_DEEPSEEK_PROVIDER": "openrouter",
    "AI_CITATION_DEEPSEEK_MODEL": "deepseek/deepseek-v4.1-flash",

    # Perplexity Pro (temporarily stopped)
    "AI_CITATION_PERPLEXITY_ACTIVE": "false",
    "AI_CITATION_PERPLEXITY_PROVIDER": "openrouter",
    "AI_CITATION_PERPLEXITY_MODEL": "perplexity/sonar",

    # Meta Llama
    "AI_CITATION_LLAMA_ACTIVE": "true",
    "AI_CITATION_LLAMA_PROVIDER": "openrouter",
    "AI_CITATION_LLAMA_MODEL": "meta-llama/llama-3.3-70b-instruct",
}

if new_or_key:
    target_settings["OPENROUTER_API_KEY"] = new_or_key

lines = []
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

updated_keys = set()
new_lines = []

for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key = line.split("=", 1)[0].strip()
        if key in target_settings:
            new_lines.append(f"{key}={target_settings[key]}\n")
            updated_keys.add(key)
            continue
    new_lines.append(line)

# Append any settings not already in the file
missing_keys = [k for k in target_settings if k not in updated_keys]
if missing_keys:
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines.append("\n")
    new_lines.append("\n# ==============================================================================\n")
    new_lines.append("# AI Citation Tracker — Frontier Models Configuration via OpenRouter\n")
    new_lines.append("# ==============================================================================\n")
    for k in missing_keys:
        new_lines.append(f"{k}={target_settings[k]}\n")

with open(env_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Successfully written to", env_path)
EOF

# If backend/.env exists and is separate from root .env, sync it as well
if [ -f "${ROOT_DIR}/backend/.env" ] && [ "${ENV_FILE}" != "${ROOT_DIR}/backend/.env" ]; then
    echo -e "Syncing to secondary file: ${BOLD}${ROOT_DIR}/backend/.env${RESET}"
    cp "${ENV_FILE}" "${ROOT_DIR}/backend/.env"
fi

echo ""
echo -e "${GREEN}✓ Successfully updated environment variables for AI Citation!${RESET}"
echo ""
echo -e "${BOLD}Current Frontier Model Configuration in ${ENV_FILE}:${RESET}"
echo "------------------------------------------------------------------"
grep -E '^(AI_CITATION_PROVIDER|AI_CITATION_CROSS_PROVIDER|AI_CITATION_(CLAUDE|GEMINI|CHATGPT|QWEN|DEEPSEEK)_(MODEL|PROVIDER|ACTIVE)|OPENROUTER_API_KEY)' "$ENV_FILE" | while read -r line; do
    if [[ "$line" =~ ^OPENROUTER_API_KEY= ]]; then
        KEY_VAL="${line#*=}"
        if [ -n "$KEY_VAL" ]; then
            echo -e "  ${CYAN}OPENROUTER_API_KEY${RESET}=${KEY_VAL:0:12}...${KEY_VAL: -4}"
        else
            echo -e "  ${YELLOW}OPENROUTER_API_KEY${RESET}= (NOT SET! Add your sk-or-v1-... key)"
        fi
    else
        KEY_PART="${line%%=*}"
        VAL_PART="${line#*=}"
        echo -e "  ${CYAN}${KEY_PART}${RESET}=${GREEN}${VAL_PART}${RESET}"
    fi
done
echo "------------------------------------------------------------------"
echo ""
echo -e "${BOLD}Next Steps:${RESET}"
echo "1. If using Docker Compose: run 'docker compose restart api'"
echo "2. If running standalone: restart your backend process (systemctl restart dristik-api / pm2 restart dristik-api)"
echo ""
