# Phase1a LTM Paper-Parity Plan

Date: 2026-05-21  
Project: `C:\PROGRAMING\czr004`  
Status: partial + reason -- manifest, runner, summarizer, dry-run, and one 30s manifest probe are complete; full 3600-run paper-scale batch has not been executed.

Execution checklist: `outputs/reports/phase1a_execution_checklist.md`

## Purpose

Phase1a is inserted after Phase1 and before Phase2. Its purpose is to complete full paper-level quantitative reproduction for the LTM route before the project proceeds to the unified metrics harness and later NTM stages.

Phase1 built the structural `LaCAM*+LTM` implementation. Phase1a must answer the stricter question: under the LTM paper's reported experimental setting, does the local `LaCAM*+LTM` reproduce the paper's main quantitative trend relative to LaCAM*?

## Blocking Rule

Do not enter Phase2 until Phase1a is complete, unless the user explicitly pauses Phase1a and the reason is recorded in `docs/codex-worklog.md`.

## Required Scope

- Setting: LTM paper one-shot MAPF.
- Maps: eight grid maps used by the LTM paper Figure 1, all present locally under `external/lacam2/scripts/map/`.
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

## Frozen Benchmark Manifest

Manifest files:

- `configs/phase1a/agent_schedule.yaml`
- `configs/phase1a/manifest.yaml`
- `configs/phase1a/manifest.jsonl`
- `src/data/benchmark_index.md`

Scenario source: `external/lacam2/scripts/scen/scen-random.zip`, extracted by the run script into `outputs/tmp/phase1a/scen/`.

| Map | Local map path | Agent counts |
| --- | --- | --- |
| `empty-32-32` | `external/lacam2/scripts/map/empty-32-32.map` | 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000 |
| `empty-48-48` | `external/lacam2/scripts/map/empty-48-48.map` | 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000 |
| `random-32-32-20` | `external/lacam2/scripts/map/random-32-32-20.map` | 100, 200, 300, 400, 500, 600, 700 |
| `maze-32-32-4` | `external/lacam2/scripts/map/maze-32-32-4.map` | 100, 200, 300, 400, 500 |
| `random-64-64-20` | `external/lacam2/scripts/map/random-64-64-20.map` | 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000 |
| `room-64-64-8` | `external/lacam2/scripts/map/room-64-64-8.map` | 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000 |
| `warehouse-10-20-10-2-1` | `external/lacam2/scripts/map/warehouse-10-20-10-2-1.map` | 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000 |
| `warehouse-10-20-10-2-2` | `external/lacam2/scripts/map/warehouse-10-20-10-2-2.map` | 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000 |

The agent schedule is read from Figure 1 x-axis ticks. The paper text does not publish CSV values.

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

## Project Entrypoints

- Build: `scripts/build_phase1a_batch.ps1`
- Run: `scripts/run_phase1a_batch.ps1`
- Linux build: `scripts/build_phase1a_batch.sh`
- Linux run: `scripts/run_phase1a_batch.py` or `scripts/run_phase1a_batch.sh`
- Runner: `build/phase1a-batch/phase1a_batch.exe`
- Summary: `src/eval/phase1a_summarize.py`

The runner emits one JSONL row per method/map/scenario/agent-count tuple. Full paper-scale execution is:

```powershell
powershell -ExecutionPolicy Bypass -File C:\PROGRAMING\czr004\scripts\run_phase1a_batch.ps1 -Full
python C:\PROGRAMING\czr004\src\eval\phase1a_summarize.py --input C:\PROGRAMING\czr004\outputs\logs\phase1a\phase1a_runs.jsonl
```

## Acceptance Gate

Phase1a passes when:

- all commands and configs are reproducible;
- `LaCAM*+LTM` can be compared directly against `LaCAM*`;
- the result trend is aligned with the LTM paper's main claim, or the deviation is diagnosed and recorded;
- missing `TO/SUO` baselines, if any, are explicitly marked as unavailable / not reproduced;
- implementation deviations are recorded in `docs/implementation-notes.md`.

## Next Implementation Tasks

1. Build `phase1a_batch`.
2. Run `scripts/run_phase1a_batch.ps1 -DryRun`.
3. Summarize the dry-run JSONL.
4. If the dry-run gate passes, launch `-Full` or a documented user-approved subset.
5. Write `outputs/reports/phase1a_ltm_paper_parity_report.md` from the generated data.
