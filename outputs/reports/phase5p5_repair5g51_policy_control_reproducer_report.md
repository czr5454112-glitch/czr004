# Phase5.5 RepairG.5.1 Policy Control Reproducer Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `runtime_rows_full`: `True`
- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `semantic_parity_mismatch_count`: `0`
- `selector_logs_present`: `True`
- `selector_update_log_rows`: `190`
- `allowed_feature_policy_passed`: `True`
- `forbidden_feature_policy_passed`: `True`
- `unexpected_runtime_features`: `[]`
- `forbidden_runtime_features`: `[]`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `force_additive_policy_compliant`: `False`
- `disable_policy_compliant`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `aaai_ready`: `False`
- `policy_control_reproducer_passed`: `False`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[136, 137, 138, 139, 140, 141, 142, 143, 144, 145]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `540`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 60 | 0 | 50 | 0 | 0.0 |
| `laur_disable` | 60 | 0 | 50 | 0 | 0.0 |
| `laur_force_additive_direct` | 60 | 0 | 50 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 60 | 0 | 50 | 0 | 0.0 |
| `repair5g5_contextual_flow_shield_selector_disable` | 60 | 0 | 50 | 0 | 0.0 |
| `repair5g5_contextual_flow_shield_selector_force_additive_parity` | 60 | 0 | 48 | 2 | 0.002297870613999997 |
| `repair5g_dual_additive_parity` | 60 | 0 | 50 | 0 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 60 | 0 | 50 | 0 | 0.0 |
