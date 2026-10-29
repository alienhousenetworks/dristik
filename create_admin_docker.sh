#!/bin/bash
set -e

# ==============================================================================
# Dristik AI - Docker Admin Account Creator & Password Reset
# ==============================================================================

EMAIL="${1:-admin@dristik.ai}"
PASSWORD="${2:-A@admin123456}"
NAME="${3:-Dristik Admin}"

echo "=========================================================="
echo "  Dristik AI - Docker Admin Account Setup"
echo "=========================================================="
echo "Target Email:    $EMAIL"
echo "Target Password: $PASSWORD"
echo "----------------------------------------------------------"

# Detect Docker Compose command (docker compose vs docker-compose)
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "[-] Error: docker compose or docker-compose is not installed or not in PATH."
    exit 1
fi

# Check if 'api' service container is running
API_CONTAINER=$($DOCKER_COMPOSE ps -q api 2>/dev/null || true)

if [ -n "$API_CONTAINER" ] && docker ps -q --no-trunc | grep -q "$API_CONTAINER"; then
    echo "[+] Found running backend API container ($API_CONTAINER)..."
    echo "[+] Executing admin creation script inside container..."
    $DOCKER_COMPOSE exec -T api python3 scripts/create_or_reset_admin.py \
        --email "$EMAIL" \
        --password "$PASSWORD" \
        --name "$NAME"
else
    echo "[!] API service is not currently running. Running temporary container..."
    $DOCKER_COMPOSE run --rm -T api python3 scripts/create_or_reset_admin.py \
        --email "$EMAIL" \
        --password "$PASSWORD" \
        --name "$NAME"
fi

# Update .env if present in root or backend to ensure persistence on reboot
for env_file in .env backend/.env; do
    if [ -f "$env_file" ]; then
        if grep -q "^SYSTEM_ADMIN_PASSWORD=" "$env_file"; then
            sed -i.bak "s|^SYSTEM_ADMIN_PASSWORD=.*|SYSTEM_ADMIN_PASSWORD=$PASSWORD|" "$env_file" && rm -f "${env_file}.bak"
        fi
        if grep -q "^SYSTEM_ADMIN_EMAIL=" "$env_file"; then
            sed -i.bak "s|^SYSTEM_ADMIN_EMAIL=.*|SYSTEM_ADMIN_EMAIL=$EMAIL|" "$env_file" && rm -f "${env_file}.bak"
        fi
    fi
done

echo "----------------------------------------------------------"
echo "[✓] Admin setup complete!"
echo "    Email:    $EMAIL"
echo "    Password: $PASSWORD"
echo "=========================================================="
