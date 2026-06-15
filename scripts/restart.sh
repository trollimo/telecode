#!/usr/bin/env bash
# =============================================================================
# restart.sh — Restart the Docker Compose stack
# =============================================================================
# Works on Linux and Windows (Git Bash / MinGW).
# Usage: ./restart.sh [service]
#   Without args — restarts all services.
#   With a service name — restarts only that service (e.g. ./restart.sh bot).
# =============================================================================

set -euo pipefail

SERVICE="${1:-}"
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker/compose.yml --project-directory ."

echo "🔄 Restarting Docker Compose stack${SERVICE:+ (service: $SERVICE)}..."

if [ -n "$SERVICE" ]; then
  $COMPOSE restart "$SERVICE"
else
  $COMPOSE down
  $COMPOSE up -d
fi

echo "✅ Done."
