# Build the Phase4D LAU update-rule probe binary.
param(
  [string]$BuildDir = "build\phase4-laur-ltm"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Vcvars = "C:\PROGRAMING\visual studio\Visual studio\VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $Vcvars)) {
  throw "MSVC vcvars not found: $Vcvars"
}

$Cmake = Join-Path $env:USERPROFILE ".conda\envs\czr004\Library\bin\cmake.exe"
if (-not (Test-Path $Cmake)) {
  $Cmake = "cmake"
}

$BuildPath = Join-Path $Root $BuildDir

$Command = "chcp 65001 >NUL && call `"$Vcvars`" -vcvars_ver=14.41 10.0.22621.0 && `"$Cmake`" -S `"$Root\cpp\ltm`" -B `"$BuildPath`" -G Ninja && `"$Cmake`" --build `"$BuildPath`" --config Release --target phase4_laur_probe --parallel 1"
cmd.exe /d /c $Command
if ($LASTEXITCODE -ne 0) {
  throw "Phase4 LAUR probe build failed with exit $LASTEXITCODE"
}

Write-Host "Phase4 LAUR probe build: $BuildPath"
