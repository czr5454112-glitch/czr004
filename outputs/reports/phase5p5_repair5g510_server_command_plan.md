# Phase5.5 Repair5G.5.10 Server Command Plan

Use this package if the desktop cannot finish the full observed-ID lattice run.

## Expected Rows

- primary 1000/2000 only: `1680` rows
- full 250/500/1000/2000: `3360` rows
- contexts: `60`
- candidates: `14`

## Commands

1. `powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1`
2. `python scripts/run_repair5g510_executable_lattice_smoke.py --overwrite --max-workers 1`
3. `python scripts/analyze_repair5g510_lattice_adapter_parity.py`
4. `python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py --overwrite --instance-ids 146..155 --budgets-ms 250 500 1000 2000 --max-contexts-per-group 1 --max-workers 4 --checkpoint-topk-edges 256 --include-full-traffic`
5. `python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py`
6. `python scripts/create_repair5g510_feature_matrix_v2.py`
7. `python scripts/analyze_repair5g510_feature_signal_v2.py`
8. `python scripts/create_repair5g510_confidence_targets_v4.py`
9. `python scripts/analyze_repair5g510_confidence_targets_v4.py`
10. `python scripts/train_repair5g510_abstention_parameter_policy.py`
11. `python scripts/eval_repair5g510_abstention_parameter_policy.py`
12. `python scripts/write_repair5g510_decision.py`

## Resume

`python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py --instance-ids 146..155 --budgets-ms 250 500 1000 2000 --max-contexts-per-group 1 --max-workers 4 --checkpoint-topk-edges 256 --include-full-traffic`

## Pull Back

- `outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv`
- `outputs/tables/phase5p5_repair5g510_lattice_oracle_by_context.csv`
- `outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv`
- `outputs/tables/phase5p5_repair5g510_confidence_targets_v4.csv`
- `outputs/reports/phase5p5_repair5g510_*.json`
- `outputs/reports/phase5p5_repair5g510_*.md`
- `outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/*.jsonl`

## Sanity Checks

- JSON summaries parse with python -m json.tool
- CSV result rows >= 3360 for full 250/500/1000/2000 run
- candidate_id count is 14 for lattice results
- no seed in 166..205
- adapter parity summary decision is lattice_adapter_parity_passed
