# Phase5.5 Repair5F.4 Full-Lattice Oracle Diagnosis

Diagnostic-only full bounded UpdateParams lattice analysis on F4 fresh IDs 26..45.

## Boundary

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- f4_outcomes_used_for_retuning: `false`

## F4 Full-Lattice Oracle

- rows: `120`
- better / equal / worse: `67 / 53 / 0`
- mean_delta_ratio_vs_ltm: `-0.017388555948699997`
- ratio_worse_than_ltm_groups: `0`
- success_worse_than_ltm_groups: `0`
- selected_candidate_distribution: `{'additive_ltm': 50, 'c050_b100_w100_d100': 5, 'c075_b075_w100_d100': 4, 'c075_b075_w125_d095': 5, 'c075_b100_w100_d090': 2, 'c075_b100_w100_d095': 1, 'c075_b100_w100_d100': 1, 'c075_b100_w125_d100': 1, 'c075_b125_w100_d100': 1, 'c075_b125_w125_d095': 4, 'c100_b050_w100_d100': 3, 'c100_b075_w075_d100': 1, 'c100_b075_w100_d090': 2, 'c100_b075_w100_d095': 1, 'c100_b075_w100_d100': 3, 'c100_b100_w050_d100': 1, 'c100_b100_w075_d090': 2, 'c100_b100_w075_d095': 2, 'c100_b100_w100_d090': 1, 'c100_b100_w100_d095': 1, 'c100_b100_w125_d090': 1, 'c100_b100_w125_d095': 3, 'c100_b100_w125_d100': 3, 'c100_b125_w075_d100': 3, 'c100_b125_w100_d100': 1, 'c125_b075_w100_d090': 3, 'c125_b075_w100_d100': 1, 'c125_b075_w125_d095': 1, 'c125_b100_w075_d100': 1, 'c125_b100_w100_d090': 2, 'c125_b100_w100_d095': 1, 'c125_b100_w100_d100': 1, 'c125_b100_w125_d100': 1, 'c125_b125_w075_d095': 2, 'c125_b125_w100_d100': 3, 'c150_b100_w100_d100': 2}`

## Static Diagnostics

- best_single_static_candidate: `c125_b125_w075_d095`
- best_static_mean_delta_ratio_vs_ltm: `-0.0028050352278249997`
- best_static better/equal/worse: `35 / 64 / 21`
- locked_candidate_ranking: `27`
- leave_one_group_static_mean_delta_ratio_vs_ltm: `-0.0024372178218000046`
- maximin_group_mean_static_candidate: `c125_b125_w075_d095`

## Group-Adaptive Oracle

- better / equal / worse: `32 / 69 / 19`
- mean_delta_ratio_vs_ltm: `-0.004211779807733345`
- ratio_worse_than_ltm_groups: `0`

## Support-vs-F4 Transfer

- common_candidate_count: `47`
- pearson_mean_delta: `0.09744265590792357`
- spearman_rank_correlation: `0.18987049028677153`
- locked_candidate_support_rank: `1`
- locked_candidate_f4_rank: `27`
- support_overranked_locked_candidate: `True`

## Failure Classification

- no_headroom: `False`
- static_overfit: `True`
- group_heterogeneity: `True`
- noisy_time_budget_sensitive_effects: `True`
- selector_objective_mismatch: `True`
- best_static_weak: `False`
- leave_one_group_robust_static_weak: `False`

## Decision

- decision: `plan_new_static_candidate_protocol_with_untouched_final_validation`
- rationale: A static candidate appears robust on F4, but that is diagnostic-only because F4 outcomes observed it. Any static claim requires a new support/validation protocol and a fresh final holdout. Support-to-F4 transfer is poor or overranked the locked rule, so the selector objective also needs diagnosis.
