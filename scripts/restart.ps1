# =============================================================================
# restart.ps1 — Restart the Docker Compose stack
# =============================================================================
# Works on Windows (PowerShell 5.1+).
# Usage: .\restart.ps1 [[-Service] <string>]
#   Without args — restarts all services.
#   With -Service — restarts only that service (e.g. .\restart.ps1 -Service bot).
# =============================================================================

param(
    [string]$Service = ""
)

# Move to project root (parent of scripts/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location -LiteralPath $projectRoot

if ($Service) {
    Write-Host "🔄 Restarting service: $Service ..."
    & docker compose -f docker/compose.yml --project-directory . restart $Service
} else {
    Write-Host "🔄 Restarting full stack..."
    & docker compose -f docker/compose.yml --project-directory . down
    & docker compose -f docker/compose.yml --project-directory . up -d
}

Write-Host "✅ Done."
