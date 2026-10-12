# Publish a new version to the experience channel (SPEC-INFRA-001).
# Usage:  powershell -File scripts\publish-experience.ps1 -Note "what changed"
# Effect: builds the isolated experience exe and drops it + update.json
#         into %LOCALAPPDATA%\AIProjectViewer\updates\. The owner's client
#         lights up its Update button; nothing is disturbed until he clicks.

param([Parameter(Mandatory = $true)][string]$Note)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Version tag comes from tauri.conf.json — bump it there before publishing
# (owner 2026-10-09 scheme: one requirement owns a 0.x0 decade, e.g. all
# builds of the PDF requirement are 0.4x; the next requirement starts at
# 0.50; 1.0.0 when everything is done).
$conf = Get-Content (Join-Path $root "src-tauri\tauri.conf.json") -Raw | ConvertFrom-Json
$version = $conf.version
if (-not $version) { throw "no version in tauri.conf.json" }

# Owner isolation (2026-10-10 lesson): the experience build MUST NOT land
# in target\release — that file is the dev/e2e binary. An exp-identifier
# exe there single-instance hands off to the owner's RUNNING client (the
# test instance dies in ~100ms), or worse: e2e silently tests the wrong
# channel. A separate cargo target dir keeps both trees honest.
$env:CARGO_TARGET_DIR = Join-Path $root "src-tauri\target-exp"
Push-Location $root
pnpm tauri build --config src-tauri/experience.conf.json --no-bundle
if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }
Pop-Location
Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue

$updates = Join-Path $env:LOCALAPPDATA "AIProjectViewer\updates"
New-Item -ItemType Directory -Force -Path $updates | Out-Null

# Same-version republish guard (2026-10-12 incident: a publish ran without
# bumping the version, staging a mislabeled build — the owner's client then
# read "up to date" against a fix it never got). The staged note carries the
# last published version; refuse to publish the same version again.
$stagedJson = Join-Path $updates "update.json"
$stagedV = $null
if (Test-Path $stagedJson) {
    try {
        $staged = Get-Content $stagedJson -Raw | ConvertFrom-Json
        if ($staged.note -match '^\[(?<v>[0-9.]+) ') { $stagedV = $Matches.v }
    } catch {
        Write-Host "staged note unreadable, publishing $version"
    }
}
if ($stagedV -eq $version) {
    throw "version $version was already published — bump the version in src-tauri/tauri.conf.json (and package.json / Cargo.toml) before publishing."
}
if ($stagedV) { Write-Host "staged version: $stagedV -> publishing $version" }

$expExe = Join-Path $root "src-tauri\target-exp\release\ai-project-viewer.exe"
if (-not (Test-Path $expExe)) { throw "experience exe not found at $expExe" }
Copy-Item $expExe (Join-Path $updates "ai-project-viewer.exe") -Force

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$json = @{ note = "[$version | $stamp] $Note" } | ConvertTo-Json
# UTF-8 WITHOUT BOM: the client's JSON parser chokes on a BOM (lessons L2).
[System.IO.File]::WriteAllText((Join-Path $updates "update.json"), $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "PUBLISHED. Tell the owner: click the Update button in the client."
