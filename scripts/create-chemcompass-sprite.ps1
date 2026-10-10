# Create and bootstrap a Fly.io Sprite for ChemCompass (https://fly.io/sprites/)
# Prereq: payment method on org (Sprites trial credit), then: sprite login

$ErrorActionPreference = "Stop"
$sprite = "$env:LOCALAPPDATA\Programs\Sprite\sprite.exe"
if (-not (Test-Path $sprite)) {
    Write-Host "Installing Sprite CLI..."
    iwr https://sprites.dev/install.ps1 -useb | iex
    $sprite = "$env:LOCALAPPDATA\Programs\Sprite\sprite.exe"
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

& $sprite org list 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: sprite login"
    & $sprite login
}

Write-Host "Creating sprite 'chemcompass'..."
& $sprite create chemcompass --skip-console
& $sprite use chemcompass
& $sprite info

$bootstrap = "set -e; cd /home/sprite; if [ ! -d ChemCompass ]; then git clone https://github.com/sgcharan/ChemCompass.git; fi; cd ChemCompass; git pull --ff-only || true; npm ci; python3 -m pip install --user -r scripts/pyq-llm/requirements.txt; test -f data/pyq-corpus/corpus.sqlite && echo corpus:OK || echo corpus:MISSING"

Write-Host "Bootstrapping repo on the Sprite..."
& $sprite exec -- bash -lc $bootstrap

Write-Host @"

Next:
  sprite console
  sprite proxy 5173:5173
  sprite checkpoint create --comment "after bootstrap"

Docs: docs/SPRITES.md
"@
