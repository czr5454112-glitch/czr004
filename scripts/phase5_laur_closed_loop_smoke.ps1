# Phase5C closed-loop smoke and ablation runner for LAU-LTM.
param(
  [string]$BuildDir = "build\phase1a-batch",
  [string]$OutputJsonl = "",
  [double]$TimeLimitSec = 3,
  [uint32]$LtmMaxIterations = 4,
  [uint32[]]$AgentCounts = @(50, 100),
  [uint32]$InstanceId = 1,
  [string]$WeightsJson = "artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp\laur_mlp_v1_weights.json",
  [string]$RuntimeModelDir = "outputs\tmp\phase5\laur_repair3_stable_tie001_mlp_runtime",
  [string]$CondaExe = "C:\PROGRAMING\anaconda\Scripts\conda.exe"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Binary = Join-Path $Root "$BuildDir\phase1a_batch.exe"
$AdditiveModel = Join-Path $Root "configs\phase5\laur_additive_only"
$WeightsPath = Join-Path $Root $WeightsJson
$RuntimeModel = Join-Path $Root $RuntimeModelDir
$ScenarioDir = Join-Path $Root "outputs\tmp\phase1a\generated\phase1a-generated-random"

if (-not (Test-Path $Binary)) {
  throw "Missing $Binary. Build with scripts\build_phase1a_batch.ps1 first."
}
if (-not (Test-Path $AdditiveModel)) {
  throw "Missing additive runtime config: $AdditiveModel"
}
if (-not (Test-Path $WeightsPath)) {
  throw "Missing learned MLP JSON export: $WeightsPath"
}
if ([string]::IsNullOrWhiteSpace($OutputJsonl)) {
  $Stamp = [DateTime]::UtcNow.ToString("yyyyMMddHHmmssfff")
  $OutputJsonl = "outputs\logs\phase5\phase5c_laur_closed_loop_$Stamp.jsonl"
}

$OutputPath = Join-Path $Root $OutputJsonl
if (Test-Path $OutputPath) {
  throw "Output JSONL already exists: $OutputPath"
}
$OutputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $OutputDir | Out-Null

function Invoke-ProjectPython {
  param([string[]]$PythonArgs)
  if (Test-Path $CondaExe) {
    & $CondaExe run -n czr004 python @PythonArgs
  } else {
    & python @PythonArgs
  }
  if ($LASTEXITCODE -ne 0) {
    throw "python command failed with exit ${LASTEXITCODE}: $($PythonArgs -join ' ')"
  }
}

Invoke-ProjectPython @(
  "scripts\export_phase5_laur_mlp_runtime.py",
  "--weights-json",
  $WeightsPath,
  "--output-dir",
  $RuntimeModel
)

$RequiredScenario = Join-Path $ScenarioDir "random-32-32-20-random-$InstanceId.scen"
if (-not (Test-Path $RequiredScenario)) {
  Invoke-ProjectPython @(
    "scripts\generate_phase1a_scenarios.py",
    "--manifest",
    "configs\phase1a\manifest.jsonl",
    "--output-dir",
    "outputs\tmp\phase1a\generated\phase1a-generated-random",
    "--output-zip",
    "outputs\tmp\phase1a\generated\phase1a-generated-random.zip",
    "--metadata",
    "outputs\reports\phase1a_generated_scenarios_manifest.json",
    "--overwrite"
  )
}

$Cases = @(
  @{ MapName = "random-32-32-20"; MapPath = "external\lacam2\scripts\map\random-32-32-20.map" },
  @{ MapName = "maze-32-32-4"; MapPath = "external\lacam2\scripts\map\maze-32-32-4.map" },
  @{ MapName = "warehouse-10-20-10-2-1"; MapPath = "external\lacam2\scripts\map\warehouse-10-20-10-2-1.map" }
)

$Methods = @(
  @{ Method = "lacam_star"; Alias = "lacam_star"; Extra = @() },
  @{ Method = "lacam_star_ltm"; Alias = "lacam_star_ltm"; Extra = @() },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_force_additive"
    Extra = @("--laur-force-additive", "--laur-model-path", $AdditiveModel)
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_static_block_heavy"
    Extra = @("--laur-static-rule", "block_heavy", "--laur-allow-pre-first-solution")
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_static_decay_095"
    Extra = @("--laur-static-rule", "decay_095", "--laur-allow-pre-first-solution")
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_learned_safety"
    Extra = @("--laur-model-path", $RuntimeModel, "--laur-safety-threshold", "0.30")
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_learned_no_safety"
    Extra = @("--laur-model-path", $RuntimeModel, "--laur-disable-safety")
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_learned_every_restart"
    Extra = @("--laur-model-path", $RuntimeModel, "--laur-allow-pre-first-solution", "--laur-safety-threshold", "0.30")
  },
  @{
    Method = "lacam_star_lau_ltm"
    Alias = "lacam_star_lau_ltm_learned_every_k2"
    Extra = @("--laur-model-path", $RuntimeModel, "--laur-every-k-restarts", "2", "--laur-safety-threshold", "0.30")
  }
)

foreach ($Case in $Cases) {
  $Map = Join-Path $Root $Case.MapPath
  $Scen = Join-Path $ScenarioDir "$($Case.MapName)-random-$InstanceId.scen"
  if (-not (Test-Path $Map)) {
    throw "Missing map: $Map"
  }
  if (-not (Test-Path $Scen)) {
    throw "Missing scenario: $Scen"
  }

  foreach ($Agents in $AgentCounts) {
    foreach ($Entry in $Methods) {
      $Method = [string]$Entry.Method
      $Alias = [string]$Entry.Alias
      $ExtraArgs = [string[]]$Entry.Extra
      & $Binary `
        --method $Method `
        --method-alias $Alias `
        --map $Map `
        --scen $Scen `
        --agents $Agents `
        --seed $InstanceId `
        --time-limit-sec $TimeLimitSec `
        --ltm-max-iterations $LtmMaxIterations `
        --output-jsonl $OutputPath `
        --map-name $Case.MapName `
        --scen-id "$($Case.MapName)-random-$InstanceId.scen" `
        --manifest phase5c-smoke `
        --project-commit phase5c-local `
        --external-commit phase5c-local `
        --branch phase5c-local `
        --dirty local `
        --platform "Windows Phase5C closed-loop smoke" `
        @ExtraArgs
      if ($LASTEXITCODE -eq 1) {
        throw "phase1a_batch crashed for $Alias map=$($Case.MapName) agents=$Agents"
      }
      if ($LASTEXITCODE -ne 0) {
        Write-Warning "solver row recorded non-success exit $LASTEXITCODE for $Alias map=$($Case.MapName) agents=$Agents"
      }
    }
  }
}

$SummaryCsv = Join-Path $Root "outputs\tables\phase5c_laur_closed_loop_smoke_summary.csv"
$ReportMd = Join-Path $Root "outputs\reports\phase5c_laur_closed_loop_smoke_report.md"
Invoke-ProjectPython @(
  "scripts\summarize_phase5_laur_smoke.py",
  "--input-jsonl",
  $OutputPath,
  "--summary-csv",
  $SummaryCsv,
  "--report-md",
  $ReportMd
)

$MetricsSummary = Join-Path $Root "outputs\metrics\phase5\phase5c_laur_smoke_summary.csv"
$MetricsPaired = Join-Path $Root "outputs\metrics\phase5\phase5c_laur_smoke_paired.csv"
$MetricsReport = Join-Path $Root "outputs\reports\phase5c_laur_metrics_replay.md"
Invoke-ProjectPython @(
  "scripts\run_phase2_metrics.py",
  "--input",
  $OutputPath,
  "--summary-csv",
  $MetricsSummary,
  "--paired-csv",
  $MetricsPaired,
  "--report-md",
  $MetricsReport,
  "--baseline",
  "lacam_star_ltm",
  "--contender",
  "lacam_star_lau_ltm_learned_safety"
)

Write-Host "Phase5C LAUR closed-loop smoke complete."
Write-Host "JSONL: $OutputPath"
Write-Host "Report: $ReportMd"
