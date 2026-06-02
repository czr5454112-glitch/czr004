# Phase5.5 Repair5F.3 Runtime Export Evaluation

This is diagnostic-only runtime evidence. Phase5.5 and Phase6 remain forbidden.

## Runtime Scope

- maps: `['maze-32-32-4', 'random-32-32-20', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[21, 22, 23, 24, 25]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`

## Method Summary

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 30 | 0 | 30 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 30 | 0 | 30 | 0 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 30 | 6 | 19 | 5 | -0.0027415721339999993 |
| `repair5f_bounded_updateparam_selector_runtime` | 30 | 6 | 19 | 5 | -0.0027415721339999993 |
| `repair5f_bounded_updateparam_selector_force_additive_parity` | 30 | 0 | 30 | 0 | 0.0 |
| `repair5f_runtime_random_candidate_diagnostic` | 30 | 6 | 18 | 6 | 0.001419514395033339 |
| `repair5f_runtime_shuffled_utility_diagnostic` | 30 | 4 | 19 | 7 | 0.0009148892173333441 |
| `repair5e5_crossfold_utility_reranker` | 30 | 4 | 22 | 4 | -0.0009245170596666741 |
| `repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic` | 30 | 7 | 20 | 3 | -0.0039024738501666654 |
| `laur_disable` | 30 | 0 | 30 | 0 | 0.0 |
| `laur_force_additive_direct` | 30 | 0 | 30 | 0 | 0.0 |

## Gates

- force_additive_parity_exact: `True`
- exact_additive_candidate_parity_exact: `True`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- support_final_leakage_false: `True`
- runtime_selector_better_gt_worse: `True`
- runtime_selector_mean_delta_lt_0: `True`
- runtime_selector_ratio_worse_groups_le_1: `True`
- runtime_selector_success_worse_groups_eq_0: `True`
- runtime_selector_beats_random_diagnostic: `True`
- runtime_selector_beats_shuffled_utility_diagnostic: `True`
- runtime_selector_improves_over_e5_real_selector: `True`
- runtime_selector_does_not_collapse_to_additive_parity: `True`
- phase5p5_allowed_false: `True`
- phase6_allowed_false: `True`

## Static-Candidate Ablation

- selector_static_runtime_metrics_equal: `True`
- selector_static_candidate_policy_equal_on_eligible_updates: `True`
- interpretation: `support_trained_static_bounded_updateparams`

If the selector and static candidate are equal, the result must be reported as a support-trained static bounded UpdateParams replacement, not context-adaptive selection.
