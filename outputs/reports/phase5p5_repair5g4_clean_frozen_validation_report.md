# Phase5.5 Repair5G.4 Clean Frozen Validation Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `strict_additive_parity_exact`: `False`
- `strict_laur_disable_parity_exact`: `False`
- `strict_laur_force_additive_direct_parity_exact`: `False`
- `strict_dual_additive_parity_exact`: `False`
- `strict_dual_c_equiv_additive_parity_exact`: `False`
- `true_semantic_parity_mismatch_count`: `0`
- `strict_mismatches_all_policy_classified`: `True`
- `parity_policy_compliant`: `True`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `no_ids_le_125_used_as_g4_clean_validation`: `True`
- `best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010`: `True`
- `best_flow_shield_bootstrap_probability_mean_delta_lt_0_ge_0p99`: `True`
- `best_flow_shield_ratio_worse_than_ltm_groups_eq_0`: `True`
- `best_flow_shield_success_worse_than_ltm_groups_eq_0`: `True`
- `best_c_equiv_at_least_0p006_worse_than_best_flow`: `True`
- `best_scalar_at_least_0p006_worse_than_best_flow`: `True`
- `flow_shield_family_beats_random_median`: `True`
- `flow_shield_family_beats_shuffled_goal_progress_median`: `True`
- `selector_vs_static_classification`: `selector_beats_static`
- `selected_mean_delta_ratio_vs_ltm`: `-0.01862021635864017`
- `selected_bootstrap_probability_mean_delta_lt_0`: `1.0`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `protocol_gates_passed`: `True`
- `representation_gates_passed`: `True`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165]`
- `row_count`: `5520`
- `expected_row_count`: `5520`
- `missing_rows`: `0`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 240 | 0 | 239 | 0 | 0.0 |
| `laur_disable` | 240 | 0 | 238 | 1 | 0.0 |
| `laur_force_additive_direct` | 240 | 0 | 237 | 2 | 0.0 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 240 | 54 | 132 | 54 | 1.9386608310920164e-05 |
| `repair5f_candidate_additive_ltm` | 240 | 0 | 237 | 2 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 240 | 56 | 129 | 55 | 0.0005339901798577423 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | 240 | 119 | 78 | 43 | -0.01740697971160084 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 240 | 129 | 73 | 38 | -0.017841402696689077 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | 240 | 117 | 77 | 46 | -0.012831045359684871 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 240 | 123 | 78 | 39 | -0.016410173082962193 |
| `repair5g2_best_frozen_static_candidate` | 240 | 123 | 78 | 39 | -0.016410173082962193 |
| `repair5g2_c_equiv_best_frozen_baseline` | 240 | 52 | 129 | 59 | -0.0004763340012899129 |
| `repair5g2_frozen_static_or_selector` | 240 | 124 | 89 | 27 | -0.01862021635864017 |
| `repair5g2_g1_top_diagnostic_candidate` | 240 | 123 | 78 | 39 | -0.016410173082962193 |
| `repair5g4_random_flow_shield_diagnostic_seed0` | 240 | 122 | 77 | 41 | -0.01563740779221009 |
| `repair5g4_random_flow_shield_diagnostic_seed1` | 240 | 119 | 81 | 40 | -0.01565005014586555 |
| `repair5g4_shuffled_flow_shield_diagnostic_seed0` | 240 | 117 | 81 | 42 | -0.016062811026100843 |
| `repair5g4_shuffled_goal_progress_diagnostic_seed0` | 240 | 114 | 89 | 37 | -0.015481350629920171 |
| `repair5g_dual_additive_parity` | 240 | 1 | 236 | 3 | 0.00016960799759493646 |
| `repair5g_dual_c_equiv_additive` | 240 | 1 | 239 | 0 | 0.0 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 240 | 56 | 124 | 60 | 0.00039514939941772504 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 240 | 52 | 129 | 59 | -0.0004763340012899129 |
