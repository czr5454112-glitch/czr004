# Phase5.5 Repair5G Dual-Channel Dev Report

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
- instance_ids: `[26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]`
- row_count: `2280` / `2280`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 120 | 0 | 120 | 0 | 0.0 |
| `laur_disable` | 120 | 0 | 120 | 0 | 0.0 |
| `laur_force_additive_direct` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 120 | 33 | 67 | 20 | -0.0016039228914083343 |
| `repair5f_candidate_additive_ltm` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 120 | 25 | 68 | 27 | 0.000543819647899992 |
| `repair5g_dual_additive_parity` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5g_dual_balanced_decay` | 120 | 5 | 66 | 49 | 0.018833444063524992 |
| `repair5g_dual_block_wait_cong_flow025` | 120 | 2 | 69 | 49 | 0.018511684814274988 |
| `repair5g_dual_block_wait_cong_flow050` | 120 | 0 | 70 | 50 | 0.021779983580524985 |
| `repair5g_dual_c_only_best_f4_observed` | 120 | 17 | 61 | 42 | 0.007440336798399994 |
| `repair5g_dual_c_only_locked_f4` | 120 | 15 | 62 | 43 | 0.007675997201349986 |
| `repair5g_dual_flow_only_025` | 120 | 0 | 70 | 50 | 0.022428777828941655 |
| `repair5g_dual_flow_only_050` | 120 | 0 | 70 | 50 | 0.022428777828941655 |
| `repair5g_dual_goal_gated_wait_025` | 120 | 4 | 68 | 48 | 0.017697362382433326 |
| `repair5g_dual_goal_gated_wait_050` | 120 | 0 | 70 | 50 | 0.022428777828941655 |
| `repair5g_random_dual_candidate_diagnostic` | 120 | 5 | 69 | 46 | 0.019861634269858323 |
| `repair5g_shuffled_goal_progress_diagnostic` | 120 | 13 | 62 | 45 | 0.010474970962683326 |
