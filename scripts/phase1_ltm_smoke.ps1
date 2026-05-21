# Phase1 structural smoke: LTM update semantics + LTM-guided LaCAM* adapter.
param(
  [string]$BuildDir = "build\phase1-ltm"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LacamRoot = Join-Path $Root "external\lacam2"
$Smoke = Join-Path $Root "$BuildDir\phase1_ltm_smoke.exe"

if (-not (Test-Path $Smoke)) {
  throw "Missing $Smoke. Build with scripts\build_phase1_ltm.ps1 first."
}

Push-Location $LacamRoot
try {
  & $Smoke
  if ($LASTEXITCODE -ne 0) {
    throw "phase1_ltm_smoke.exe failed with exit $LASTEXITCODE"
  }
}
finally {
  Pop-Location
}

Write-Host "Phase1 LTM smoke passed."
