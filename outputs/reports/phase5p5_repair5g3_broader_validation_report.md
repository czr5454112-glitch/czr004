# Phase5.5 Repair5G.3 Broader Validation Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `additive_parity_exact`: `False`
- `laur_disable_parity_exact`: `False`
- `laur_force_additive_direct_parity_exact`: `False`
- `dual_additive_parity_exact`: `False`
- `dual_c_equiv_additive_parity_exact`: `False`
- `true_semantic_parity_mismatch_count`: `0`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `no_ids_le_65_used_as_g3_fresh_validation`: `True`
- `selected_better_gt_worse`: `True`
- `selected_mean_delta_ratio_vs_ltm_lt_neg_0p008`: `True`
- `selected_bootstrap_probability_mean_delta_lt_0_ge_0p99`: `True`
- `selected_ratio_worse_than_ltm_groups_le_1`: `True`
- `selected_success_worse_than_ltm_groups_eq_0`: `True`
- `best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010`: `True`
- `best_c_equiv_at_least_0p006_worse_than_best_flow`: `True`
- `best_scalar_at_least_0p006_worse_than_best_flow`: `True`
- `flow_shield_family_beats_random_median`: `True`
- `flow_shield_family_beats_shuffled_goal_progress_median`: `True`
- `selector_vs_static_classification`: `tied_within_0p001`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `protocol_gates_passed`: `False`
- `selected_gates_passed`: `True`
- `representation_gates_passed`: `True`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `6240`
- `expected_row_count`: `6240`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 240 | 5 | 220 | 2 | 0.0 |
| `laur_disable` | 240 | 2 | 207 | 15 | 2.5114810576923115e-05 |
| `laur_force_additive_direct` | 240 | 2 | 211 | 11 | 2.4640946226415135e-05 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 240 | 63 | 104 | 59 | -0.000803222976864483 |
| `repair5f_candidate_additive_ltm` | 240 | 5 | 215 | 7 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 240 | 51 | 109 | 62 | -0.0014563323262769946 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | 240 | 126 | 59 | 43 | -0.018082975595405656 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 240 | 129 | 58 | 37 | -0.018539173455766653 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 240 | 104 | 78 | 44 | -0.009962335813286378 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | 240 | 125 | 64 | 37 | -0.016561033390033016 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 240 | 127 | 62 | 34 | -0.02004726679608962 |
| `repair5g2_best_frozen_static_candidate` | 240 | 127 | 62 | 34 | -0.02004726679608962 |
| `repair5g2_c_equiv_best_frozen_baseline` | 240 | 53 | 102 | 73 | 0.0009849877360095744 |
| `repair5g2_frozen_static_or_selector` | 240 | 132 | 60 | 31 | -0.019665489611971558 |
| `repair5g2_g1_top_diagnostic_candidate` | 240 | 127 | 62 | 34 | -0.02004726679608962 |
| `repair5g3_random_flow_shield_diagnostic_seed0` | 240 | 121 | 66 | 39 | -0.015583180434725112 |
| `repair5g3_random_flow_shield_diagnostic_seed1` | 240 | 122 | 63 | 40 | -0.017050832780706154 |
| `repair5g3_random_flow_shield_diagnostic_seed2` | 240 | 127 | 60 | 38 | -0.018156599366614283 |
| `repair5g3_shuffled_flow_shield_diagnostic_seed0` | 240 | 127 | 67 | 33 | -0.017650294962611366 |
| `repair5g3_shuffled_flow_shield_diagnostic_seed1` | 240 | 127 | 60 | 39 | -0.017928787921823803 |
| `repair5g3_shuffled_goal_progress_diagnostic_seed0` | 240 | 123 | 71 | 34 | -0.017209582716687197 |
| `repair5g_dual_additive_parity` | 240 | 2 | 211 | 11 | 2.4640946226415135e-05 |
| `repair5g_dual_c_equiv_additive` | 240 | 1 | 209 | 13 | 0.00023959325464454955 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 240 | 61 | 102 | 63 | -0.0004213876429374977 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 240 | 53 | 102 | 73 | 0.0009849877360095744 |

## Interpretation

protocol_failed
