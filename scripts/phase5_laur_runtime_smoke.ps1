# Phase5A runtime skeleton smoke: additive-only load and force-additive parity.
param(
  [string]$BuildDir = "build\phase5-laur-runtime",
  [string]$ModelPath = "configs\phase5\laur_additive_only"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LacamRoot = Join-Path $Root "external\lacam2"
$Smoke = Join-Path $Root "$BuildDir\phase5_laur_runtime_smoke.exe"
$Model = Join-Path $Root $ModelPath

if (-not (Test-Path $Smoke)) {
  throw "Missing $Smoke. Build with scripts\build_phase5_laur_runtime_smoke.ps1 first."
}
if (-not (Test-Path $Model)) {
  throw "Missing additive-only runtime config: $Model"
}

Push-Location $LacamRoot
try {
  & $Smoke $Model
  if ($LASTEXITCODE -ne 0) {
    throw "phase5_laur_runtime_smoke.exe failed with exit $LASTEXITCODE"
  }
}
finally {
  Pop-Location
}

Write-Host "Phase5 LAUR runtime smoke passed."
