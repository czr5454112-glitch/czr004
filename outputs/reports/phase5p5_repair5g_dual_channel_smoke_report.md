# Phase5.5 Repair5G Dual-Channel Smoke Report

This is diagnostic-only representation evidence. It does not permit Phase5.5 or Phase6.

## Gates

- build_passed: `True`
- schema_errors: `0`
- missing_rows: `0`
- dual_additive_parity_exact: `True`
- always_additive_defer_parity_exact: `True`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- all_dual_costs_finite: `True`
- cost_bounds_respected: `True`
- no_solver_crashes: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[26, 27]`
- row_count: `108` / `108`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 12 | 0 | 12 | 0 | 0.0 |
| `laur_disable` | 12 | 0 | 12 | 0 | 0.0 |
| `laur_force_additive_direct` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5g_dual_additive_parity` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5g_dual_block_wait_cong_flow025` | 12 | 0 | 9 | 3 | 0.015531397574999994 |
| `repair5g_dual_flow_only_025` | 12 | 0 | 9 | 3 | 0.019149001821666678 |
| `repair5g_dual_goal_gated_wait_025` | 12 | 1 | 8 | 3 | 0.01617144799666668 |
