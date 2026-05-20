# Phase0 Startup Plan

Date: 2026-05-20  
Project: `C:\PROGRAMING\czr004`

## Purpose

Phase0 exists to make the project reproducible before implementation starts. The immediate goal is not solver performance. The goal is to lock down the research route, environment, git discipline, and baseline responsibilities.

## Confirmed Corrections

- LTM paper alignment should start from the original LaCAM* codebase.
- LaCAM3 should be treated as a project target and engineering baseline, not as the default LTM paper base.
- LTM edge weights should default to `[0,10]` according to the local PDF.
- Any LTM implementation here should be described as `paper-faithful reimplementation`, not official reproduction.

## Required Phase0 Tasks

1. Initialize git in `C:\PROGRAMING\czr004`.
2. Commit the initial documentation and environment files.
3. Update the existing `czr004` conda environment from `environment.yml`.
4. Record `conda list -n czr004` after installation.
5. Select upstream repositories:
   - LaCAM* for paper alignment.
   - LaCAM3 for project-target comparison.
6. Add upstream code as submodules or clean mirrors, recording exact commits.
7. Run minimal baseline smoke commands only after the upstream commits are recorded.

## Phase0 Gate

Phase0 passes when:

- git exists and has an initial commit;
- `czr004` environment can run Python;
- required build/analysis dependencies are installed or any failed packages are documented;
- upstream baseline choice is recorded;
- no solver code has been changed without a Markdown worklog entry.

## Not Yet Done

- No LaCAM* or LaCAM3 repository has been cloned.
- No C++ baseline has been built.
- No MAPF experiment has been run.
