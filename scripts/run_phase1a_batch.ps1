# Run Phase1a batch tasks. DryRun is a smoke gate; Full is the paper-scale run.
param(
  [switch]$DryRun,
  [switch]$Full,
  [switch]$Append,
  [string]$BuildDir = "build\phase1a-batch",
  [string]$Manifest = "configs\phase1a\manifest.jsonl",
  [string]$OutputJsonl = "outputs\logs\phase1a\phase1a_runs.jsonl",
  [double]$TimeLimitSec = 30,
  [double]$DryRunTimeLimitSec = 5,
  [string[]]$MapSubset = @(),
  [int[]]$AgentSubset = @(),
  [int[]]$InstanceSubset = @(),
  [int]$MaxTasks = 0,
  [uint32]$LtmMaxIterations = 100000,
  [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Binary = Join-Path $Root "$BuildDir\phase1a_batch.exe"
$ManifestPath = Join-Path $Root $Manifest
$OutputPath = Join-Path $Root $OutputJsonl

if (-not (Test-Path $Binary)) {
  throw "Missing $Binary. Build with scripts\build_phase1a_batch.ps1 first."
}

if ((-not $DryRun) -and (-not $Full) -and $MapSubset.Count -eq 0 -and $AgentSubset.Count -eq 0 -and $InstanceSubset.Count -eq 0 -and $MaxTasks -eq 0) {
  throw "Choose -DryRun, -Full, or an explicit subset."
}

$OutputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $OutputDir | Out-Null
if ((-not $Append) -and (Test-Path $OutputPath)) {
  Remove-Item -LiteralPath $OutputPath -Force
}

$ProjectCommit = (git -C $Root rev-parse HEAD).Trim()
$ExternalCommit = (git -C (Join-Path $Root "external\lacam2") rev-parse HEAD).Trim()
$Branch = (git -C $Root branch --show-current).Trim()
$TrackedStatus = (git -C $Root status --porcelain --untracked-files=no)
$UntrackedStatus = (git -C $Root status --porcelain --untracked-files=normal | Select-String '^\?\?')
$Dirty = if ($TrackedStatus) { "tracked-dirty" } elseif ($UntrackedStatus) { "tracked-clean_untracked-present" } else { "clean" }
$Platform = "Windows; PowerShell; MSVC-compatible build"

function Invoke-Phase1aTask {
  param(
    [string]$Method,
    [string]$MapName,
    [string]$MapPath,
    [string]$ScenPath,
    [string]$ScenId,
    [int]$Agents,
    [int]$Seed,
    [double]$RunTimeLimitSec
  )

  & $Binary `
    --method $Method `
    --map $MapPath `
    --scen $ScenPath `
    --agents $Agents `
    --seed $Seed `
    --time-limit-sec $RunTimeLimitSec `
    --output-jsonl $OutputPath `
    --map-name $MapName `
    --scen-id $ScenId `
    --manifest $ManifestPath `
    --project-commit $ProjectCommit `
    --external-commit $ExternalCommit `
    --branch $Branch `
    --dirty $Dirty `
    --platform $Platform `
    --ltm-max-iterations $LtmMaxIterations

  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2) {
    throw "phase1a_batch failed with exit $LASTEXITCODE for $Method $MapName N=$Agents seed=$Seed"
  }
}

if ($DryRun) {
  $LacamRoot = Join-Path $Root "external\lacam2"
  $MapPath = Join-Path $LacamRoot "assets\loop.map"
  $ScenPath = Join-Path $LacamRoot "assets\loop.scen"
  foreach ($Method in @("lacam_star", "lacam_star_ltm")) {
    Invoke-Phase1aTask `
      -Method $Method `
      -MapName "loop-dry-run" `
      -MapPath $MapPath `
      -ScenPath $ScenPath `
      -ScenId "loop.scen" `
      -Agents 3 `
      -Seed 1 `
      -RunTimeLimitSec $DryRunTimeLimitSec
  }
  Write-Host "Phase1a dry-run JSONL: $OutputPath"
  return
}

if (-not (Test-Path $ManifestPath)) {
  throw "Missing manifest: $ManifestPath"
}

$Records = Get-Content -LiteralPath $ManifestPath | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
$Methods = @("lacam_star", "lacam_star_ltm")
$TaskCount = 0

$ScenCache = Join-Path $Root "outputs\tmp\phase1a\scen"
New-Item -ItemType Directory -Force $ScenCache | Out-Null
$Archives = $Records | ForEach-Object { if ($_.scen_archive) { [string]$_.scen_archive } else { "external\lacam2\scripts\scen\scen-random.zip" } } | Sort-Object -Unique
foreach ($ArchiveRelative in $Archives) {
  $Archive = Join-Path $Root $ArchiveRelative
  if (-not (Test-Path $Archive)) {
    throw "Missing scenario archive: $Archive. Generate it first if this is a generated Phase1a manifest."
  }
  Expand-Archive -LiteralPath $Archive -DestinationPath $ScenCache -Force
}

function Get-ScenarioCapacity {
  param([string]$Path)

  $LineCount = (Get-Content -LiteralPath $Path | Where-Object { $_.Trim() } | Measure-Object).Count
  return [Math]::Max(0, $LineCount - 1)
}

if (-not $SkipPreflight) {
  $Issues = New-Object System.Collections.Generic.List[string]
  $PreflightTasks = 0

  foreach ($Record in $Records) {
    if ($MapSubset.Count -gt 0 -and $MapSubset -notcontains $Record.map) {
      continue
    }

    $MapPath = Join-Path $Root $Record.map_path
    if (-not (Test-Path $MapPath)) {
      $Issues.Add("$($Record.map): missing map $MapPath")
    }

    $Agents = @($Record.agent_counts)
    if ($AgentSubset.Count -gt 0) {
      $Agents = $Agents | Where-Object { $AgentSubset -contains [int]$_ }
    }
    $Instances = @($Record.instances)
    if ($InstanceSubset.Count -gt 0) {
      $Instances = $Instances | Where-Object { $InstanceSubset -contains [int]$_ }
    }

    if ($Agents.Count -eq 0) {
      $Issues.Add("$($Record.map): no selected agent counts")
      continue
    }
    if ($Instances.Count -eq 0) {
      $Issues.Add("$($Record.map): no selected instances")
      continue
    }

    $MaxAgents = ($Agents | Measure-Object -Maximum).Maximum
    foreach ($InstanceId in $Instances) {
      $Template = [string]$Record.scen_template
      $RelativeScen = $Template.Replace("{instance}", [string]$InstanceId)
      $ScenPath = Join-Path $ScenCache $RelativeScen
      if (-not (Test-Path $ScenPath)) {
        $Issues.Add("$($Record.map) instance ${InstanceId}: missing scenario $ScenPath")
        continue
      }
      $Capacity = Get-ScenarioCapacity -Path $ScenPath
      if ($Capacity -lt $MaxAgents) {
        $Issues.Add("$($Record.map) instance ${InstanceId}: scenario has $Capacity pairs, but selected max agent count is $MaxAgents")
      }
    }
    $PreflightTasks += $Agents.Count * $Instances.Count * $Methods.Count
  }

  if ($Issues.Count -gt 0) {
    $Preview = $Issues | Select-Object -First 20
    $Message = "Phase1a preflight failed:`n- " + ($Preview -join "`n- ")
    if ($Issues.Count -gt 20) {
      $Message += "`n- ... $($Issues.Count - 20) more issues"
    }
    throw $Message
  }

  Write-Host "Phase1a preflight passed. Tasks=$PreflightTasks"
}

foreach ($Record in $Records) {
  if ($MapSubset.Count -gt 0 -and $MapSubset -notcontains $Record.map) {
    continue
  }

  $MapPath = Join-Path $Root $Record.map_path
  $Agents = @($Record.agent_counts)
  if ($AgentSubset.Count -gt 0) {
    $Agents = $Agents | Where-Object { $AgentSubset -contains [int]$_ }
  }
  $Instances = @($Record.instances)
  if ($InstanceSubset.Count -gt 0) {
    $Instances = $Instances | Where-Object { $InstanceSubset -contains [int]$_ }
  }

  foreach ($N in $Agents) {
    foreach ($InstanceId in $Instances) {
      $Template = [string]$Record.scen_template
      $RelativeScen = $Template.Replace("{instance}", [string]$InstanceId)
      $ScenPath = Join-Path $ScenCache $RelativeScen
      if (-not (Test-Path $ScenPath)) {
        throw "Missing scenario after extraction: $ScenPath"
      }
      foreach ($Method in $Methods) {
        Invoke-Phase1aTask `
          -Method $Method `
          -MapName $Record.map `
          -MapPath $MapPath `
          -ScenPath $ScenPath `
          -ScenId $RelativeScen `
          -Agents ([int]$N) `
          -Seed ([int]$InstanceId) `
          -RunTimeLimitSec $TimeLimitSec

        $TaskCount += 1
        if ($MaxTasks -gt 0 -and $TaskCount -ge $MaxTasks) {
          Write-Host "Stopped after MaxTasks=$MaxTasks. JSONL: $OutputPath"
          return
        }
      }
    }
  }
}

Write-Host "Phase1a batch complete. Tasks=$TaskCount JSONL: $OutputPath"
