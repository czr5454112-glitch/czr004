# Phase0 Startup Plan

Date: 2026-05-20  
Project: `C:\PROGRAMING\czr004`

## Purpose

Phase0 exists to make the project reproducible before implementation starts. The immediate goal is not solver performance. The goal is to lock down the single research route, environment, git discipline, and baseline responsibilities.

## Corrected Route

The project has only one technical route:

```text
LaCAM* baseline
  -> LaCAM* + LTM paper-faithful reimplementation
  -> LaCAM* + NTM
```

There is no cross-base migration line in this project. The project stays on the LTM paper route.

## Confirmed Corrections

- LTM paper alignment should start from the original LaCAM* codebase.
- Baselines should follow the LTM paper: LaCAM*, LaCAM*+TO, LaCAM*+SUO, LaCAM*+LTM, plus this project's LaCAM*+NTM.
- LTM edge weights should default to `[0,10]` according to the local PDF.
- Any LTM implementation here should be described as `paper-faithful reimplementation`, not official reproduction.

## Required Phase0 Tasks

1. Keep git initialized in `C:\PROGRAMING\czr004`.
2. Commit the corrected documentation and environment files.
3. Update the existing `czr004` conda environment from `environment.yml`.
4. Record `conda list -n czr004` after installation.
5. Select the upstream LaCAM* repository and record exact commit.
6. Add upstream LaCAM* code as submodule or clean mirror.
7. Run minimal LaCAM* baseline smoke only after the upstream commit is recorded.

## Phase0 Progress

- Git repository exists.
- Initial and route-correction documentation commits exist.
- Project directory skeleton has been created.
- `Kei18/lacam2` is selected as the LaCAM* upstream candidate.
- `czr004` conda environment is installed and verified.
- GPU PyTorch is installed and verified in `czr004` via pip CUDA 12.4 wheels (`torch 2.5.1+cu124`).
- `Kei18/lacam2` is added as `external/lacam2`.
- Upstream commit is recorded: `61a4c40ce91ce18c06eb2fe070aa9f1951eecb8d`.
- Recursive upstream submodules are initialized.
- LaCAM* upstream builds on Windows through a documented build-only compatibility header.
- Upstream library smoke passes via `build-czr004-msvc-compat\test_all.exe`.
- Upstream `main.exe` CLI smoke timed out locally; an argparse `-v` flag clash is a known risk but not a fully proven root cause. Phase1 uses `build/phase0-smoke/phase0_smoke.exe`, `scripts/phase0_smoke.ps1`, or a project-owned adapter CLI instead.
- Project smoke binary `build/phase0-smoke/phase0_smoke.exe` passes on `assets/loop.*` (sum_of_loss=15).
- GPU PyTorch verification passes on the RTX 4070 Laptop GPU.

## Phase0 Gate

Phase0 passes when:

- git exists and has a corrected route commit;
- `czr004` environment can run Python;
- GPU PyTorch import and a CUDA tensor smoke pass;
- required build/analysis dependencies are installed or any failed packages are documented;
- upstream LaCAM* baseline choice and exact commit are recorded;
- a LaCAM* library smoke passes;
- no solver code has been changed without a Markdown worklog entry.

## Not Yet Done

- No LTM implementation has been started.
- No benchmark experiment has been run.
- No upstream solver semantic code has been changed.

## Phase0 Status

Phase0 gate is satisfied. Phase1 can start with LTM paper-faithful implementation planning.

Experiment entrypoint policy:

- Allowed: `test_all.exe`, `phase0_smoke.exe`, future `cpp/ltm` adapter CLI.
- Disallowed for experiments until revalidated: upstream `main.exe`, especially with `-v` short flag.
