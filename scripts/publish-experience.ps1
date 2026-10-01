# Publish a new version to the experience channel (SPEC-INFRA-001).
# Usage:  powershell -File scripts\publish-experience.ps1 -Note "what changed"
# Effect: builds the isolated experience exe and drops it + update.json
#         into %LOCALAPPDATA%\AIProjectViewer\updates\. The owner's client
#         lights up its Update button; nothing is disturbed until he clicks.

param([Parameter(Mandatory = $true)][string]$Note)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location $root
pnpm tauri build --config src-tauri/experience.conf.json --no-bundle
if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }
Pop-Location

$updates = Join-Path $env:LOCALAPPDATA "AIProjectViewer\updates"
New-Item -ItemType Directory -Force -Path $updates | Out-Null
Copy-Item (Join-Path $root "src-tauri\target\release\ai-project-viewer.exe") `
          (Join-Path $updates "ai-project-viewer.exe") -Force

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$json = @{ note = "[$stamp] $Note" } | ConvertTo-Json
# UTF-8 WITHOUT BOM: the client's JSON parser chokes on a BOM (lessons L2).
[System.IO.File]::WriteAllText((Join-Path $updates "update.json"), $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "PUBLISHED. Tell the owner: click the Update button in the client."
