# Phase5B LAUR Solver Integration Report

Status: completed local Phase5B parity integration on 2026-05-27.

## Scope

- Integrated LAUR/LAU-LTM runtime selection into the existing `solve_with_ltm` update step through `LtmOptions::update_policy`.
- Preserved the original `solve_with_ltm(const Instance&, const LtmOptions&)` call surface; default LTM behavior uses the existing additive update params when no policy is installed.
- Added `lacam_star_lau_ltm` support to `phase1a_batch` with:
  - `--laur-enable`
  - `--laur-disable`
  - `--laur-force-additive`
  - `--laur-model-path`
  - `--laur-post-first-solution-only`
  - `--laur-every-k-restarts`
  - `--laur-safety-threshold`
- Added Phase5B LAUR JSONL diagnostics and metrics-schema normalization:
  - `laur_enabled`
  - `laur_force_additive`
  - `laur_update_mode`
  - `laur_model_path`
  - `laur_inference_count`
  - `laur_inference_total_ms`
  - `laur_update_runtime_ms`
  - `laur_additive_fallback_count`
  - `laur_safety_disabled_count`
  - `laur_selected_rules`
  - `laur_update_period_restarts`
  - `laur_post_first_solution_only`

## Parity Result

`scripts\phase5_laur_solver_parity_smoke.ps1` ran three solver rows on the same `loop.map` smoke instance:

- baseline: `lacam_star_ltm`
- force-additive LAUR: `lacam_star_lau_ltm --laur-force-additive`
- disabled LAUR: `lacam_star_lau_ltm --laur-disable`

Strict parity passed for:

- `success`
- `feasible`
- `sum_of_loss`
- `lower_bound`
- `sum_of_loss_ratio` within `1e-9`
- `returned_solutions_count`
- `committed_events`
- `blocked_events`
- `nonzero_ltm_edges`

Warn-only runtime fields differed only in `runtime_ms`, as expected for repeated local solver invocations.

Output JSONL:

- `outputs\logs\phase5\phase5b_laur_parity_20260527033612339.jsonl`

Metrics replay:

- `outputs\reports\phase5_laur_solver_parity_metrics_replay.md`
- schema errors: 0

## Compatibility Checks

- `python -m pytest tests/test_czr004_metrics.py tests/test_phase5_laur_runtime_parity.py`: 9 passed.
- `python -m pytest tests/test_phase4_laur_features.py tests/test_phase4_laur_schema.py`: 7 passed.
- `scripts\build_phase1a_batch.ps1`: passed.
- `scripts\build_phase5_laur_runtime_smoke.ps1`: passed.
- `scripts\phase5_laur_runtime_smoke.ps1`: passed.
- `scripts\phase5_laur_solver_parity_smoke.ps1`: passed.
- `scripts\run_phase1a_batch.py --dry-run --dry-run-time-limit-sec 3 --ltm-max-iterations 3`: passed.
- Metrics replay for old Phase1a dry-run JSONL: schema errors 0.
- `scripts\build_phase4_laur_smoke.ps1`: passed.
- `scripts\phase4_laur_update_smoke.ps1`: passed.
- `scripts\build_phase1_ltm.ps1`: passed.
- `scripts\phase1_ltm_smoke.ps1`: passed.

## Boundary

This Phase5B step is solver-safe runtime wiring plus parity validation. It does not add learned restart logic, does not change PIBT candidate-domain/conflict semantics, and does not claim learned closed-loop performance improvement.
