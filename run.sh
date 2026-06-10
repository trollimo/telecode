#!/usr/bin/env bash
# Start the project stack.
# Works on Linux and Windows (Git Bash / mingw).
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Starting Telegram → OpenCode stack ==="

# Ensure config exists
CONFIG_DIR="${HOME}/.rem-opencode"
CONFIG_FILE="${CONFIG_DIR}/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[INFO] Config not found. Creating template at ${CONFIG_FILE}..."
    mkdir -p "$CONFIG_DIR"
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

# Create external volumes if needed
mkdir -p docker-data/gradle-cache

# Build images only if they don't exist yet
if ! docker image inspect opencode-telegram:latest > /dev/null 2>&1; then
    echo "[BUILD] opencode-telegram:latest not found, building..."
    docker compose build opencode
fi
if ! docker image inspect tg-bot:latest > /dev/null 2>&1; then
    echo "[BUILD] tg-bot:latest not found, building..."
    docker compose build bot
fi

docker compose up -d

echo "=== Stack started ==="
echo "  Bot logs: docker compose logs -f bot"
echo "  Stop:     ./stop.sh"
