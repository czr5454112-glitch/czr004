# Phase5.5 Repair5G.3 Determinism Repeat Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `raw_control_parity_exact`: `False`
- `strict_control_parity_exact_for_non_timeout_equivalent_controls`: `True`
- `true_semantic_parity_mismatch_count`: `0`
- `true_semantic_parity_mismatch_count_zero`: `True`
- `solver_crash_count`: `0`
- `schema_errors`: `0`
- `selected_mean_delta_sign_stable`: `True`
- `selected_repeat_mean_delta_ratio_vs_ltm_lt_0_repeats`: `3`
- `selected_success_worse_than_ltm_groups`: `0`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `determinism_repeat_gates_passed`: `True`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[66, 67, 68, 69, 70, 71, 72, 73, 74, 75]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `3240`
- `expected_row_count`: `3240`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 180 | 1 | 153 | 3 | 0.0 |
| `laur_disable` | 180 | 1 | 151 | 4 | -7.311746894736752e-05 |
| `laur_force_additive_direct` | 180 | 2 | 150 | 6 | 0.0 |
| `repair5f_candidate_additive_ltm` | 180 | 4 | 150 | 5 | -1.2655641788080491e-05 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 180 | 88 | 42 | 30 | -0.014982447495117639 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 180 | 63 | 60 | 33 | -0.005966646111862743 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 180 | 80 | 46 | 32 | -0.016482058666188314 |
| `repair5g2_best_frozen_static_candidate` | 180 | 80 | 46 | 32 | -0.016482058666188314 |
| `repair5g2_c_equiv_best_frozen_baseline` | 180 | 21 | 81 | 55 | 0.0035723500317086133 |
| `repair5g2_frozen_static_or_selector` | 180 | 96 | 43 | 21 | -0.016835551253026142 |
| `repair5g2_g1_top_diagnostic_candidate` | 180 | 80 | 46 | 32 | -0.016482058666188314 |
| `repair5g2_random_candidate_diagnostic` | 180 | 55 | 54 | 48 | -0.005161063960258278 |
| `repair5g2_shuffled_flow_shield_diagnostic` | 180 | 78 | 47 | 32 | -0.014125029254681816 |
| `repair5g_dual_additive_parity` | 180 | 0 | 152 | 4 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 180 | 5 | 152 | 3 | -7.263957699346315e-05 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 180 | 26 | 73 | 57 | 0.004090503313646665 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 180 | 21 | 81 | 55 | 0.0035723500317086133 |
