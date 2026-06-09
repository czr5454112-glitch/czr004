# Phase5B solver-loop parity smoke for LAU-LTM runtime integration.
param(
  [string]$BuildDir = "build\phase1a-batch",
  [string]$ModelPath = "configs\phase5\laur_additive_only",
  [string]$OutputJsonl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Binary = Join-Path $Root "$BuildDir\phase1a_batch.exe"
$Model = Join-Path $Root $ModelPath

if (-not (Test-Path $Binary)) {
  throw "Missing $Binary. Build with scripts\build_phase1a_batch.ps1 first."
}
if (-not (Test-Path $Model)) {
  throw "Missing LAUR additive-only config: $Model"
}
if ([string]::IsNullOrWhiteSpace($OutputJsonl)) {
  $Stamp = [DateTime]::UtcNow.ToString("yyyyMMddHHmmssfff")
  $OutputJsonl = "outputs\logs\phase5\phase5b_laur_parity_$Stamp.jsonl"
}

$OutputPath = Join-Path $Root $OutputJsonl
$OutputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $OutputDir | Out-Null

$Map = Join-Path $Root "external\lacam2\assets\loop.map"
$Scen = Join-Path $Root "external\lacam2\assets\loop.scen"

function Invoke-Phase5ParityRun {
  param(
    [string]$Method,
    [string[]]$ExtraArgs
  )

  & $Binary `
    --method $Method `
    --map $Map `
    --scen $Scen `
    --agents 3 `
    --seed 1 `
    --time-limit-sec 3 `
    --ltm-max-iterations 3 `
    --output-jsonl $OutputPath `
    --map-name loop-phase5b `
    --scen-id loop.scen `
    --manifest phase5b-smoke `
    --project-commit phase5b-local `
    --external-commit phase5b-local `
    --branch phase5b-local `
    --dirty local `
    --platform "Windows Phase5B parity smoke" `
    @ExtraArgs
  if ($LASTEXITCODE -ne 0) {
    throw "phase1a_batch failed with exit $LASTEXITCODE for $Method"
  }
}

Invoke-Phase5ParityRun "lacam_star_ltm" @()
Invoke-Phase5ParityRun "lacam_star_lau_ltm" @(
  "--laur-force-additive",
  "--laur-model-path",
  $Model
)
Invoke-Phase5ParityRun "lacam_star_lau_ltm" @("--laur-disable")

$Rows = Get-Content $OutputPath | Where-Object { $_.Trim().Length -gt 0 } | ForEach-Object {
  $_ | ConvertFrom-Json
}
if ($Rows.Count -ne 3) {
  throw "Expected 3 parity rows, got $($Rows.Count)"
}

$Baseline = $Rows[0]
$Force = $Rows[1]
$Disabled = $Rows[2]

function Assert-EqualField {
  param(
    $Left,
    $Right,
    [string]$Field,
    [string]$Label
  )
  if ($Left.$Field -ne $Right.$Field) {
    throw "$Label mismatch for $Field baseline=$($Left.$Field) candidate=$($Right.$Field)"
  }
}

function Assert-CloseField {
  param(
    $Left,
    $Right,
    [string]$Field,
    [double]$Tolerance,
    [string]$Label
  )
  $A = [double]$Left.$Field
  $B = [double]$Right.$Field
  if ([Math]::Abs($A - $B) -gt $Tolerance) {
    throw "$Label mismatch for $Field baseline=$A candidate=$B tolerance=$Tolerance"
  }
}

foreach ($Candidate in @($Force, $Disabled)) {
  $Label = $Candidate.method
  Assert-EqualField $Baseline $Candidate "success" $Label
  Assert-EqualField $Baseline $Candidate "feasible" $Label
  Assert-EqualField $Baseline $Candidate "sum_of_loss" $Label
  Assert-EqualField $Baseline $Candidate "lower_bound" $Label
  Assert-CloseField $Baseline $Candidate "sum_of_loss_ratio" 1.0e-9 $Label
  Assert-EqualField $Baseline $Candidate "returned_solutions_count" $Label
  Assert-EqualField $Baseline $Candidate "committed_events" $Label
  Assert-EqualField $Baseline $Candidate "blocked_events" $Label
  Assert-EqualField $Baseline $Candidate "nonzero_ltm_edges" $Label
}

if (-not $Force.laur_enabled -or -not $Force.laur_force_additive) {
  throw "force-additive row did not report LAUR force-additive mode"
}
if ($Disabled.laur_enabled) {
  throw "disabled row unexpectedly reported LAUR enabled"
}

foreach ($Field in @("expanded_nodes", "low_level_pibt_calls", "runtime_ms")) {
  if ($Baseline.$Field -ne $Force.$Field) {
    Write-Warning "warn-only parity field differs for force-additive: $Field baseline=$($Baseline.$Field) force=$($Force.$Field)"
  }
  if ($Baseline.$Field -ne $Disabled.$Field) {
    Write-Warning "warn-only parity field differs for disabled: $Field baseline=$($Baseline.$Field) disabled=$($Disabled.$Field)"
  }
}

Write-Host "Phase5B LAUR solver parity passed. JSONL: $OutputPath"
