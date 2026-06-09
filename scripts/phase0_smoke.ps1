# Phase0 acceptance smoke: upstream unit tests + project-owned library smoke.
param(
  [string]$UpstreamBuildDir = "build-czr004-msvc-compat"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LacamRoot = Join-Path $Root "external\lacam2"
$UpstreamBuild = Join-Path $LacamRoot $UpstreamBuildDir
$TestAll = Join-Path $UpstreamBuild "test_all.exe"
$Phase0Smoke = Join-Path $Root "build\phase0-smoke\phase0_smoke.exe"

if (-not (Test-Path $TestAll)) {
  throw "Missing $TestAll. Run scripts/build_lacam2_upstream.ps1 first."
}

Push-Location $LacamRoot
try {
  & $TestAll
  if ($LASTEXITCODE -ne 0) { throw "test_all.exe failed with exit $LASTEXITCODE" }
}
finally {
  Pop-Location
}

if (Test-Path $Phase0Smoke) {
  Push-Location $LacamRoot
  try {
    & $Phase0Smoke
    if ($LASTEXITCODE -ne 0) { throw "phase0_smoke.exe failed with exit $LASTEXITCODE" }
  }
  finally {
    Pop-Location
  }
}
else {
  Write-Warning "phase0_smoke.exe not found. Build with: scripts/build_lacam2_upstream.ps1 -WithPhase0Smoke"
}

Write-Host "Phase0 smoke passed."
