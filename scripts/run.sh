#!/usr/bin/env bash
# Start the project stack.
# Works on Linux and Windows (Git Bash / mingw).
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker/compose.yml --project-directory ."

echo "=== Starting Telegram → OpenCode stack ==="

# Ensure config exists
CONFIG_DIR="${HOME}/.rem-opencode"
mkdir -p "$CONFIG_DIR"

# Telegram bot config
CONFIG_FILE="${CONFIG_DIR}/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[INFO] Config not found. Creating template at ${CONFIG_FILE}..."
    cat > "$CONFIG_FILE" <<- EOF
{
  "telegram_token": "YOUR_BOT_TOKEN_HERE",
  "allowed_user_id": 0,
  "opencode_url": "http://opencode:4096"
}
EOF
    echo "[WARN] Edit ${CONFIG_FILE} with your real token and user ID, then re-run."
    exit 1
fi

# OpenCode model config
OC_CONFIG="${CONFIG_DIR}/opencode.json"
if [ ! -f "$OC_CONFIG" ]; then
    echo "[INFO] Creating default opencode.json at ${OC_CONFIG}..."
    cat > "$OC_CONFIG" <<- 'EOF'
{
  "$schema": "https://opencode.ai/config.json"
}
EOF
    echo "[INFO] Edit ${OC_CONFIG} to change model providers if needed."
fi

# Build images only if they don't exist yet
if ! docker image inspect opencode-telegram:latest > /dev/null 2>&1; then
    echo "[BUILD] opencode-telegram:latest not found, building..."
    $COMPOSE build opencode
fi
if ! docker image inspect tg-bot:latest > /dev/null 2>&1; then
    echo "[BUILD] tg-bot:latest not found, building..."
    $COMPOSE build bot
fi

$COMPOSE up -d

echo "=== Stack started ==="
echo "  Bot logs: $COMPOSE logs -f bot"
echo "  Stop:     scripts/stop.sh"
