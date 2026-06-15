#!/usr/bin/env bash
# Stop the project stack.
# Works on Linux and Windows (Git Bash / mingw).
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker/compose.yml --project-directory ."

echo "=== Stopping stack ==="
$COMPOSE down
echo "=== Done ==="
