# Build upstream lacam2 (library tests + optional project smoke binary).
param(
  [string]$BuildDir = "build-czr004-msvc-compat",
  [switch]$WithPhase0Smoke
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LacamRoot = Join-Path $Root "external\lacam2"
$Compat = Join-Path $Root "cpp\compat\lacam2_windows_compat.hpp"
$Vcvars = "C:\PROGRAMING\visual studio\Visual studio\VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $Vcvars)) {
  throw "MSVC vcvars not found: $Vcvars"
}
if (-not (Test-Path $Compat)) {
  throw "Compatibility header not found: $Compat"
}

$Cmake = Join-Path $env:USERPROFILE ".conda\envs\czr004\Library\bin\cmake.exe"
if (-not (Test-Path $Cmake)) {
  $Cmake = "cmake"
}

$UpstreamBuild = Join-Path $LacamRoot $BuildDir
$fi = "/FI$Compat"

cmd.exe /d /c @"
chcp 65001 >NUL
call "$Vcvars" -vcvars_ver=14.41 10.0.22621.0
"$Cmake" -S "$LacamRoot" -B "$UpstreamBuild" -G Ninja -DCMAKE_CXX_FLAGS="/EHsc $fi"
"$Cmake" --build "$UpstreamBuild" --config Release
"@ | Out-Host

if ($WithPhase0Smoke) {
  $SmokeBuild = Join-Path $Root "build\phase0-smoke"
  cmd.exe /d /c @"
chcp 65001 >NUL
call "$Vcvars" -vcvars_ver=14.41 10.0.22621.0
"$Cmake" -S "$Root\cpp\tools" -B "$SmokeBuild" -G Ninja
"$Cmake" --build "$SmokeBuild" --config Release
"@ | Out-Host
}

Write-Host "Upstream build: $UpstreamBuild"
if ($WithPhase0Smoke) {
  Write-Host "Phase0 smoke build: $(Join-Path $Root 'build\phase0-smoke')"
}
