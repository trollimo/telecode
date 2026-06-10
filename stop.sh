#!/usr/bin/env bash
# Stop the project stack.
# Works on Linux and Windows (Git Bash / mingw).
set -euo pipefail

cd "$(dirname "$0")"

echo "=== Stopping stack ==="
docker compose down
echo "=== Done ==="
