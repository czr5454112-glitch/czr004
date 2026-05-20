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

## Phase0 Gate

Phase0 passes when:

- git exists and has a corrected route commit;
- `czr004` environment can run Python;
- required build/analysis dependencies are installed or any failed packages are documented;
- upstream LaCAM* baseline choice is recorded;
- no solver code has been changed without a Markdown worklog entry.

## Not Yet Done

- No LaCAM* repository has been cloned.
- No C++ baseline has been built.
- No MAPF experiment has been run.
- Dependency installation was interrupted and still needs to be rerun.
