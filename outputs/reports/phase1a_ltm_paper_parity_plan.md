# Phase1a LTM Paper-Parity Plan

Date: 2026-05-21  
Project: `C:\PROGRAMING\czr004`  
Status: planning instructions only; experiments not yet run.

Execution checklist: `outputs/reports/phase1a_execution_checklist.md`

## Purpose

Phase1a is inserted after Phase1 and before Phase2. Its purpose is to complete full paper-level quantitative reproduction for the LTM route before the project proceeds to the unified metrics harness and later NTM stages.

Phase1 built the structural `LaCAM*+LTM` implementation. Phase1a must answer the stricter question: under the LTM paper's reported experimental setting, does the local `LaCAM*+LTM` reproduce the paper's main quantitative trend relative to LaCAM*?

## Blocking Rule

Do not enter Phase2 until Phase1a is complete, unless the user explicitly pauses Phase1a and the reason is recorded in `docs/codex-worklog.md`.

## Required Scope

- Setting: LTM paper one-shot MAPF.
- Maps: eight grid maps used by the LTM paper, or a documented local substitute only if the exact set cannot be obtained.
- Instances: 25 random instances per map.
- Runtime: 30 seconds per run.
- Objective: sum-of-loss / `sum_of_loss_ratio`.
- Required columns:
  - `LaCAM*`
  - local `LaCAM*+LTM`
- Conditional columns:
  - `LaCAM*+TO`
  - `LaCAM*+SUO`
  Include these only if original implementations or auditable reproductions are available. Do not silently replace them with casual local approximations.

## Required Records

Every run must record:

- commit hash
- branch
- dirty status
- map
- instance or seed
- agent count
- time limit
- objective
- method
- binary path
- config path
- hardware summary
- raw solver output path

## Required Outputs

- raw JSONL or CSV for every run
- summary CSV grouped by map, agent count, and method
- paper-style table or figure data
- `outputs/reports/phase1a_ltm_paper_parity_report.md`

## Acceptance Gate

Phase1a passes when:

- all commands and configs are reproducible;
- `LaCAM*+LTM` can be compared directly against `LaCAM*`;
- the result trend is aligned with the LTM paper's main claim, or the deviation is diagnosed and recorded;
- missing `TO/SUO` baselines, if any, are explicitly marked as unavailable / not reproduced;
- implementation deviations are recorded in `docs/implementation-notes.md`.

## Next Implementation Tasks

1. Follow `outputs/reports/phase1a_execution_checklist.md`.
2. Re-read the LTM paper experiment section and list the exact eight maps and agent schedules.
3. Locate or generate the benchmark instances.
4. Freeze `configs/phase1a/agent_schedule.yaml` or an equivalent manifest before any parity claim.
5. Create the Phase1a batch runner.
6. Create a minimal Phase1a summarizer for `sum_of_loss_ratio`.
7. Run a small dry-run before launching the full 30s batch.
