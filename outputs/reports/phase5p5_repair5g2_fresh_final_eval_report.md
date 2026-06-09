# Phase5.5 Repair5G.2 Fresh Final Eval Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `full_expected_rows`: `True`
- `missing_rows_zero`: `True`
- `schema_errors_zero`: `True`
- `no_solver_crashes`: `True`
- `additive_parity_exact`: `True`
- `always_additive_defer_parity_exact`: `True`
- `laur_disable_parity_exact`: `True`
- `laur_force_additive_direct_parity_exact`: `True`
- `dual_additive_parity_exact`: `True`
- `dual_c_equiv_additive_parity_exact`: `True`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `final_ids_not_used_in_tuning`: `True`
- `protocol_gates_passed`: `True`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]`
- row_count: `2520` / `2520`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 120 | 0 | 120 | 0 | 0.0 |
| `laur_disable` | 120 | 0 | 120 | 0 | 0.0 |
| `laur_force_additive_direct` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 120 | 27 | 62 | 31 | -0.0010749925600083328 |
| `repair5f_candidate_additive_ltm` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 120 | 27 | 63 | 30 | -0.001414189259383326 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 120 | 65 | 43 | 12 | -0.01839701972659998 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 120 | 53 | 51 | 16 | -0.013749414518608331 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 120 | 64 | 43 | 13 | -0.020043939351749987 |
| `repair5g2_best_frozen_static_candidate` | 120 | 64 | 43 | 13 | -0.020043939351749987 |
| `repair5g2_c_equiv_best_frozen_baseline` | 120 | 31 | 62 | 27 | -0.0022770787914083196 |
| `repair5g2_frozen_static_or_selector` | 120 | 62 | 44 | 14 | -0.020112979571774988 |
| `repair5g2_g1_top_diagnostic_candidate` | 120 | 64 | 43 | 13 | -0.020043939351749987 |
| `repair5g2_random_candidate_diagnostic` | 120 | 52 | 55 | 13 | -0.01329058551464166 |
| `repair5g2_shuffled_flow_shield_diagnostic` | 120 | 63 | 43 | 14 | -0.019850973894158318 |
| `repair5g2_shuffled_goal_progress_diagnostic` | 120 | 60 | 44 | 16 | -0.01761917499324165 |
| `repair5g_dual_additive_parity` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 120 | 0 | 120 | 0 | 0.0 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 120 | 29 | 66 | 25 | -0.0003688872225583284 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 120 | 31 | 62 | 27 | -0.0022770787914083196 |
