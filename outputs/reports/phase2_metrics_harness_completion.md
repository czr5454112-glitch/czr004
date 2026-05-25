# Phase2 Metrics Harness Completion Report

Date: 2026-05-25
Status: Phase2 complete; Phase3 teacher-data work may begin

## Scope

Phase2 turns the Phase1a one-off reproduction metrics into a shared metrics harness before any learning/NTM work starts. It does not introduce a model and does not rerun the full paper benchmark as a new claim.

## Implemented Artifacts

| Requirement | Evidence |
| --- | --- |
| SoL, lower bound, SoL ratio definitions and tests | `src/czr004_metrics/core.py`; `tests/test_czr004_metrics.py` |
| incumbent log parser | `src/czr004_metrics/incumbent.py` |
| anytime AUC | `czr004_metrics.incumbent.anytime_auc`; tested in `tests/test_czr004_metrics.py` |
| returned solutions count | schema-normalized in `src/czr004_metrics/schema.py`; emitted by the updated batch runner |
| planning-and-execution metrics | `czr004_metrics.summary.summarize_planning_execution` with `planning_execution_step_sec` / `planning_execution_window` fields |
| expanded nodes / high-level expansions / low-level PIBT calls | schema fields in `src/czr004_metrics/schema.py`; emitted by `cpp/tools/phase1a_batch.cpp`; LTM low-level PIBT calls instrumented in `cpp/ltm/ltm.cpp` |
| paired statistical tests | `czr004_metrics.summary.summarize_paired_methods` with sign-test p-value |
| JSONL metadata schema | `src/czr004_metrics/schema.py`; strict dry-run validation passed |
| all methods use common statistical code | `scripts/run_phase2_metrics.py` and `src/eval/phase1a_summarize.py` both use `src/czr004_metrics` |

## Phase1a Replay

The shared harness replayed the completed Phase1a server JSONL:

- input: `outputs/logs/phase1a/phase1a_plus_3000_runs.jsonl`
- report: `outputs/reports/phase2_metrics_harness_report.md`
- summary CSV: `outputs/tables/phase2_phase1a_replay_summary.csv`
- paired CSV: `outputs/tables/phase2_phase1a_replay_paired.csv`

Replay results:

- rows: 3800
- schema errors: 0
- base paper-parity groups: 72
- LTM group wins: 72 / 72
- Pass-A replay: `True`
- paired successes across plus-3000 manifest: 1840
- LTM better paired rows: 1779
- baseline mean ratio: 2.97712
- LTM mean ratio: 2.54513
- relative improvement: 0.145102

The refactored `src/eval/phase1a_summarize.py` reproduced the tracked Phase1a CSV exactly:

- tracked CSV SHA256: `e195ba30641e067d79dced648944c6b670daea972b4b1d779d9f52e550f1f59f`
- replay CSV SHA256: `e195ba30641e067d79dced648944c6b670daea972b4b1d779d9f52e550f1f59f`

## New Runner Schema Smoke

After adding Phase2 fields to the batch runner:

- `scripts/build_phase1a_batch.ps1` completed.
- `scripts/run_phase1a_batch.ps1 -DryRun -DryRunTimeLimitSec 2 -OutputJsonl outputs\logs\phase2\phase2_schema_dry_run.jsonl` completed.
- strict Phase2 schema validation over that dry-run JSONL completed with 0 schema errors.

The new one-shot JSONL rows include:

- `returned_solutions_count`
- `expanded_nodes`
- `high_level_expansions`
- `low_level_pibt_calls`

For upstream `LaCAM*`, `low_level_pibt_calls` remains `null` because upstream solver source is intentionally left unmodified. The project-owned LTM adapter emits that field.

## Known Boundaries

- Historical Phase1a server logs predate the new runner fields, so `expanded_nodes`, `low_level_pibt_calls`, and `time_to_first_solution_ms` are missing in those old rows. The Phase2 harness normalizes old rows and reports coverage rather than inventing values.
- `time_to_first_solution_ms` is schema-supported and parsed from incumbent logs, but current one-shot runner rows still emit `null` until the solver writes incumbent events.
- Planning-and-execution aggregation is implemented at the metrics layer. No P&E experiment is claimed in Phase2 because P&E belongs to later benchmark phases.

## Verification Commands

```powershell
python -m py_compile scripts\run_phase2_metrics.py src\eval\phase1a_summarize.py src\czr004_metrics\__init__.py src\czr004_metrics\core.py src\czr004_metrics\io.py src\czr004_metrics\schema.py src\czr004_metrics\incumbent.py src\czr004_metrics\summary.py src\czr004_metrics\cli.py

& 'C:\PROGRAMING\anaconda\Scripts\conda.exe' run -n czr004 python -m pytest tests\test_czr004_metrics.py

python scripts\run_phase2_metrics.py --input outputs\logs\phase1a\phase1a_plus_3000_runs.jsonl --summary-csv outputs\tables\phase2_phase1a_replay_summary.csv --paired-csv outputs\tables\phase2_phase1a_replay_paired.csv --planning-execution-csv outputs\tables\phase2_planning_execution_summary.csv --report-md outputs\reports\phase2_metrics_harness_report.md

python src\eval\phase1a_summarize.py --input outputs\logs\phase1a\phase1a_plus_3000_runs.jsonl --output-csv outputs\tmp\phase2_verify\phase1a_resummary.csv --output-figure outputs\tmp\phase2_verify\phase1a_resummary.png

powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1

powershell -ExecutionPolicy Bypass -File scripts\run_phase1a_batch.ps1 -DryRun -DryRunTimeLimitSec 2 -OutputJsonl outputs\logs\phase2\phase2_schema_dry_run.jsonl

python scripts\run_phase2_metrics.py --input outputs\logs\phase2\phase2_schema_dry_run.jsonl --summary-csv outputs\tmp\phase2_verify\schema_dry_run_summary.csv --paired-csv outputs\tmp\phase2_verify\schema_dry_run_paired.csv --report-md outputs\tmp\phase2_verify\schema_dry_run_report.md --strict-schema
```

## Phase2 Gate

The Phase2 gate is satisfied: future `LaCAM*`, `LaCAM*+LTM`, and NTM experiments now have one shared metrics/schema/statistical path under `src/czr004_metrics`, and the path has been verified against both the historical Phase1a full-batch data and the current runner schema.
