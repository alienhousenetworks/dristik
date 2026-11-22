#!/usr/bin/env bash
# =============================================================================
# Dristik Local LLM Server Setup (4 GB Total RAM Edition)
# =============================================================================
# Installs & tunes Ollama for a 4 GB RAM Linux server (Ubuntu / Debian),
# configures a 4 GB swapfile to prevent OOM when Playwright + Python + Ollama
# run together, pulls a 4 GB-safe model (default: qwen2.5:1.5b-instruct),
# verifies the OpenAI-compatible /v1/chat/completions endpoint, and prints
# (or writes) the exact Dristik .env configuration.
#
# Usage:
#   sudo bash scripts/setup_local_llm_4gb.sh                       # default qwen2.5:1.5b-instruct (~1.1 GB RAM)
#   sudo bash scripts/setup_local_llm_4gb.sh qwen2.5:3b-instruct   # larger ~2.3 GB RAM (tighter on 4 GB total)
#   sudo bash scripts/setup_local_llm_4gb.sh llama3.2:3b           # Meta Llama 3.2 3B (~2.2 GB RAM)
#   WRITE_ENV=/path/to/.env sudo -E bash scripts/setup_local_llm_4gb.sh
# =============================================================================
set -euo pipefail

MODEL_NAME="${1:-qwen2.5:1.5b-instruct}"
OLLAMA_HOST_ADDR="127.0.0.1:11434"
BASE_URL="http://${OLLAMA_HOST_ADDR}/v1"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-4}"
WRITE_ENV="${WRITE_ENV:-}"

echo "============================================================"
echo " Dristik Local LLM Setup (4 GB RAM Server)"
echo " Model    : ${MODEL_NAME}"
echo " Endpoint : ${BASE_URL}"
echo "============================================================"

# 1. Inspect RAM & ensure 4 GB swapfile exists (prevents OOM kills with Chromium + Ollama)
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
TOTAL_SWAP_MB=$(free -m | awk '/^Swap:/ {print $2}')
echo "[1/5] Detected RAM: ${TOTAL_RAM_MB} MB | Swap: ${TOTAL_SWAP_MB} MB"

if [ "${TOTAL_SWAP_MB}" -lt 2048 ]; then
    echo "      Creating ${SWAP_SIZE_GB}G swapfile at /swapfile..."
    if [ ! -f /swapfile ]; then
        fallocate -l "${SWAP_SIZE_GB}G" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=$((SWAP_SIZE_GB * 1024)) status=progress
        chmod 600 /swapfile
        mkswap /swapfile
    fi
    swapon /swapfile || true
    if ! grep -q '^/swapfile ' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    sysctl -w vm.swappiness=20 >/dev/null || true
    echo "      Swap enabled: $(free -m | awk '/^Swap:/ {print $2}') MB"
else
    echo "      Existing swap (${TOTAL_SWAP_MB} MB) is sufficient."
fi

# 2. Install Ollama if missing
echo "[2/5] Checking Ollama installation..."
if ! command -v ollama >/dev/null 2>&1; then
    if ! command -v curl >/dev/null 2>&1; then
        apt-get update -y && apt-get install -y curl zstd
    fi
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "      Ollama already installed: $(ollama --version)"
fi

# 3. Lock Ollama memory limits via systemd override so it never spawns parallel models on 4 GB RAM
echo "[3/5] Configuring low-RAM Ollama service overrides..."
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^ollama.service'; then
    mkdir -p /etc/systemd/system/ollama.service.d
    cat > /etc/systemd/system/ollama.service.d/override.conf <<EOF
[Service]
Environment="OLLAMA_HOST=${OLLAMA_HOST_ADDR}"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=5m"
EOF
    systemctl daemon-reload
    systemctl enable ollama >/dev/null 2>&1 || true
    systemctl restart ollama
else
    echo "      systemd ollama.service not found; starting ollama serve in background..."
    OLLAMA_HOST="${OLLAMA_HOST_ADDR}" OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=5m \
        nohup ollama serve >/var/log/ollama.log 2>&1 &
fi

# Wait for Ollama API to be ready
echo "      Waiting for Ollama on http://${OLLAMA_HOST_ADDR}..."
for i in $(seq 1 30); do
    if curl -fsS "http://${OLLAMA_HOST_ADDR}/api/tags" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 4. Pull the model
echo "[4/5] Pulling local model '${MODEL_NAME}'..."
ollama pull "${MODEL_NAME}"

# 5. Smoke-test OpenAI-compatible JSON completion endpoint
echo "[5/5] Verifying OpenAI-compatible endpoint (${BASE_URL}/chat/completions)..."
SMOKE_RESP=$(curl -fsS "${BASE_URL}/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer local" \
    -d "{
      \"model\": \"${MODEL_NAME}\",
      \"temperature\": 0.0,
      \"max_tokens\": 64,
      \"response_format\": {\"type\": \"json_object\"},
      \"messages\": [
        {\"role\": \"system\", \"content\": \"Respond with JSON only.\"},
        {\"role\": \"user\", \"content\": \"Return {\\\"status\\\": \\\"ok\\\"}\"}
      ]
    }")
echo "      Model response: ${SMOKE_RESP}"

ENV_BLOCK=$(cat <<EOF
# --- Dristik Local LLM (4 GB RAM Server Config) ---
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=${BASE_URL}
LOCAL_LLM_MODEL=${MODEL_NAME}
LOCAL_LLM_API_KEY=local

# Low-RAM concurrency & context tuning (prevents OOM on 4 GB servers)
LLM_MAX_CONCURRENCY=1
LLM_TIMEOUT_SECONDS=180
ANALYSIS_TIMEOUT_SECONDS=1200
ENABLE_CROSS_PROVIDER_CASCADE=false
AI_EVIDENCE_MAX_TOKENS=2000
AI_SLICE_MAX_CHARS=600
REPORT_SIZING_MODE=standard
EOF
)

if [ -n "${WRITE_ENV}" ]; then
    echo ""
    echo "Appending local LLM config to ${WRITE_ENV}..."
    printf "\n%s\n" "${ENV_BLOCK}" >> "${WRITE_ENV}"
fi

echo ""
echo "============================================================"
echo " DONE! Paste this into dristik/backend/.env:"
echo "============================================================"
echo "${ENV_BLOCK}"
echo ""
echo "To switch models anytime, just pull it and update LOCAL_LLM_MODEL in .env:"
echo "  ollama pull qwen2.5:3b-instruct"
echo "  # then set LOCAL_LLM_MODEL=qwen2.5:3b-instruct in .env"
echo ""
echo "Quick 1-page smoke test:"
echo "  cd dristik/backend && python3 scripts/capture_baseline.py --max-pages 1 --urls https://example.com"
echo "============================================================"
