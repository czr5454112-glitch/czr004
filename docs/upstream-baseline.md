# Upstream Baseline Selection

Date: 2026-05-20

## Selected Upstream

Primary upstream for Phase0 and Phase1:

- Repository: `https://github.com/Kei18/lacam2`
- Role: LaCAM* baseline and LTM implementation base.
- Rationale: the IJCAI-23 LaCAM* paper states that code is available from `https://kei18.github.io/lacam2/`, and the public repository is titled `Improving LaCAM for Scalable Eventually Optimal Multi-Agent Pathfinding (IJCAI-23)`.

Reference links:

- GitHub: https://github.com/Kei18/lacam2
- IJCAI paper page: https://www.ijcai.org/proceedings/2023/28

## 2026-05-20 Clone Attempts

Command:

```powershell
git submodule add https://github.com/Kei18/lacam2.git external/lacam2
```

First result:

```text
Could not resolve host: github.com
```

No partial submodule state remained after the first failure.

Second result:

```text
Submodule added successfully.
```

Recorded submodule:

```text
61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d external/lacam2 (v0.1-13-g61a4c40)
```

Recursive submodules:

```text
09a158196e513252cfb468ad46e33568787c1e92 external/lacam2/scripts
e9ae471ea46a0f3dcd2bbbd26fa3d14433ec7884 external/lacam2/third_party/argparse
5376968f6948923e2411081fd9372e71a59d8e77 external/lacam2/third_party/googletest
```

## Phase0 Build Record

Unmodified upstream sources were built on Windows with a local force-include compatibility header:

```powershell
cmd.exe /d /c "chcp 65001 >NUL && ""C:\PROGRAMING\visual studio\Visual studio\VC\Auxiliary\Build\vcvars64.bat"" -vcvars_ver=14.41 10.0.22621.0 && ""C:\Users\38908\.conda\envs\czr004\Library\bin\cmake.exe"" -S external/lacam2 -B external/lacam2/build-czr004-msvc-compat -G Ninja -DCMAKE_CXX_FLAGS=""/EHsc /FIC:\PROGRAMING\czr004\cpp\compat\lacam2_windows_compat.hpp"""
cmd.exe /d /c "chcp 65001 >NUL && ""C:\PROGRAMING\visual studio\Visual studio\VC\Auxiliary\Build\vcvars64.bat"" -vcvars_ver=14.41 10.0.22621.0 && ""C:\Users\38908\.conda\envs\czr004\Library\bin\cmake.exe"" --build external\lacam2\build-czr004-msvc-compat --config Release"
```

Result:

```text
Build succeeded.
```

The compatibility header is build-only and does not alter LaCAM* source files.

## Phase0 Smoke Record

Passing smoke:

```powershell
build-czr004-msvc-compat\test_all.exe
```

Working directory:

```text
C:\PROGRAMING\czr004\external\lacam2
```

Result:

```text
7 tests from 6 test suites ran.
7 passed.
```

CLI caveat:

```powershell
build-czr004-msvc-compat\main.exe -m assets\loop.map -i assets\loop.scen -N 3 -s 0 -v 1 -t 3 -o build-czr004-msvc-compat\phase0_loop_N3_result.txt -O 2
```

This command timed out locally. Since the library-level planner tests pass, Phase0 accepts the upstream library as the baseline base but records the upstream CLI entrypoint as not yet trusted for experiments.

Likely cause: argparse registers both default `-v/--version` and custom `-v/--verbose` in upstream `main.cpp`. Do not use `main.exe -v ...` in experiment scripts.

## Project Smoke Entrypoint

Preferred Phase0/Phase1 smoke instead of upstream `main.exe`:

```text
C:\PROGRAMING\czr004\build\phase0-smoke\phase0_smoke.exe
```

Run from `external/lacam2` so relative `assets/*` paths resolve:

```powershell
Set-Location C:\PROGRAMING\czr004\external\lacam2
C:\PROGRAMING\czr004\build\phase0-smoke\phase0_smoke.exe
```

Batch runner:

```powershell
powershell -File C:\PROGRAMING\czr004\scripts\phase0_smoke.ps1
```

Build helper:

```powershell
powershell -File C:\PROGRAMING\czr004\scripts\build_lacam2_upstream.ps1 -WithPhase0Smoke
```

## Phase0 Rule

No solver semantic code should be changed until the upstream commit hash and baseline smoke command are recorded here. This condition is satisfied for Phase0 via the recorded submodule hash, `test_all.exe`, and `phase0_smoke.exe`. Phase1/Phase1a benchmark runs should use the project smoke/adapter entrypoint, not upstream `main.exe -v`.
