# Phase4B update API smoke: additive wrapper parity and minimal UpdateParams.
param(
  [string]$BuildDir = "build\phase4-laur-ltm"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LacamRoot = Join-Path $Root "external\lacam2"
$Smoke = Join-Path $Root "$BuildDir\phase4_laur_update_smoke.exe"

if (-not (Test-Path $Smoke)) {
  throw "Missing $Smoke. Build with scripts\build_phase4_laur_smoke.ps1 first."
}

Push-Location $LacamRoot
try {
  & $Smoke
  if ($LASTEXITCODE -ne 0) {
    throw "phase4_laur_update_smoke.exe failed with exit $LASTEXITCODE"
  }
}
finally {
  Pop-Location
}

Write-Host "Phase4 LAUR update smoke passed."
