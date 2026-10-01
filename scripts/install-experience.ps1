# Experience-channel installer (SPEC-INFRA-001). Run ONCE per machine.
# Requires: the experience build already produced via
#   pnpm tauri build --config src-tauri/experience.conf.json --no-bundle
# Actions:
#   1. %LOCALAPPDATA%\AIProjectViewer\app\ai-project-viewer.exe   (the client)
#   2. migrate the existing dev-channel state.json once (projects/tabs/settings)
#   3. repoint the desktop shortcut "AI Project Viewer" at the experience exe
# After this, development builds never touch the owner's running client.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot   # repo root (scripts/ lives in it)
$built = Join-Path $root "src-tauri\target\release\ai-project-viewer.exe"
if (-not (Test-Path $built)) { throw "Build the experience exe first (see header)." }

$base = Join-Path $env:LOCALAPPDATA "AIProjectViewer"
$appDir = Join-Path $base "app"
$updatesDir = Join-Path $base "updates"
New-Item -ItemType Directory -Force -Path $appDir, $updatesDir | Out-Null

$dest = Join-Path $appDir "ai-project-viewer.exe"
Copy-Item $built $dest -Force
Write-Host "installed: $dest"

# --- one-time state migration: dev channel -> experience channel ---
$oldState = Join-Path $env:APPDATA "com.aiprojectviewer.app\state.json"
$newStateDir = Join-Path $env:APPDATA "com.aiprojectviewer.app.exp"
$newState = Join-Path $newStateDir "state.json"
if ((Test-Path $oldState) -and (-not (Test-Path $newState))) {
    New-Item -ItemType Directory -Force -Path $newStateDir | Out-Null
    Copy-Item $oldState $newState
    Write-Host "state migrated: $newState"
}

# --- repoint the desktop shortcut ---
$ws = New-Object -ComObject WScript.Shell
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI Project Viewer.lnk"
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $dest
$s.WorkingDirectory = $appDir
$s.Save()
Write-Host "shortcut -> $dest"
Write-Host "DONE. Owner: fully close any running instance, then double-click the shortcut."
