# Phase5.5 Repair5G.5 Runtime Smoke Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `runtime_rows_full`: `True`
- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `semantic_parity_mismatch_count`: `0`
- `selector_logs_present`: `True`
- `allowed_feature_policy_passed`: `True`
- `forbidden_feature_policy_passed`: `True`
- `unexpected_runtime_features`: `[]`
- `force_additive_policy_compliant`: `False`
- `disable_policy_compliant`: `False`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `runtime_contextual_selector_mean_delta_ratio_vs_ltm`: `0.00350549546894118`
- `runtime_contextual_selector_mean_delta_ratio_vs_ltm_lt_0`: `False`
- `runtime_contextual_selector_not_broadly_harmful`: `False`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `aaai_ready`: `False`
- `runtime_smoke_gates_passed`: `False`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[126, 127, 128, 129, 130, 131, 132, 133, 134, 135]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `840`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 60 | 1 | 53 | 3 | 0.0 |
| `laur_disable` | 60 | 1 | 53 | 3 | 0.0 |
| `laur_force_additive_direct` | 60 | 1 | 52 | 4 | 0.0 |
| `repair5f_candidate_additive_ltm` | 60 | 0 | 53 | 3 | 0.0 |
| `repair5g2_best_frozen_static_candidate` | 60 | 35 | 14 | 8 | -0.02232529495036001 |
| `repair5g2_frozen_static_or_selector` | 60 | 35 | 14 | 9 | -0.026533959629559997 |
| `repair5g5_contextual_flow_shield_selector_disable` | 60 | 3 | 50 | 5 | -0.0003265706005882348 |
| `repair5g5_contextual_flow_shield_selector_force_additive_parity` | 60 | 2 | 51 | 5 | 0.0 |
| `repair5g5_contextual_flow_shield_selector_random_feature_diagnostic` | 60 | 34 | 14 | 10 | -0.020724342164560004 |
| `repair5g5_contextual_flow_shield_selector_runtime` | 60 | 8 | 27 | 23 | 0.00350549546894118 |
| `repair5g5_contextual_flow_shield_selector_shuffled_label_diagnostic` | 60 | 34 | 14 | 10 | -0.020724342164560004 |
| `repair5g_dual_additive_parity` | 60 | 2 | 50 | 5 | -1.9661913333329238e-05 |
| `repair5g_dual_c_equiv_additive` | 60 | 4 | 48 | 6 | -0.00035315716419999534 |
