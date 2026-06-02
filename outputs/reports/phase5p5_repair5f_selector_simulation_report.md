# Phase5.5 Repair5F Selector Simulation

This is a table-level final-holdout simulation. It does not export a runtime artifact.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- final_holdout_used_for_tuning: `false`

## Selector Metrics

- rows: `30`
- better: `6`
- equal: `19`
- worse: `5`
- mean_delta_ratio_vs_ltm: `-0.0027415721339999993`
- ratio_worse_than_ltm_groups: `1`
- success_worse_than_ltm_groups: `0`
- selected_nonadditive_cases: `30`
- additive_fallback_rate: `0.0`

## Pass Gates

- support_final_leakage_false: `True`
- selector_better_gt_worse: `True`
- selector_mean_delta_lt_0: `True`
- selector_ratio_worse_groups_le_1: `True`
- selector_success_worse_groups_eq_0: `True`
- selector_beats_random_candidate_diagnostic: `True`
- selector_beats_shuffled_utility_diagnostic: `True`
- selector_improves_over_e5_real_selector: `True`
- selector_does_not_collapse_to_additive: `True`

Overall table simulation passed: `True`

## Comparator Means

| method | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|
| `always_additive_defer` | 0 | 30 | 0 | 0.0 |
| `repair5e5_crossfold_utility_reranker` | 4 | 22 | 4 | -0.0009245170596666741 |
| `repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic` | 7 | 20 | 3 | -0.0039024738501666654 |
| `repair5f_bounded_updateparam_selector_random_candidate_diagnostic` | 6 | 18 | 6 | 0.001419514395033339 |
| `repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic` | 4 | 19 | 7 | 0.0009148892173333441 |
| `repair5f_candidate_additive_ltm` | 0 | 30 | 0 | 0.0 |
| `repair5f_candidate_lattice_oracle_static_proxy` | 17 | 13 | 0 | -0.018311948514033324 |

## Runtime Recommendation

The table-level selector simulation passes the F2 gates. A follow-up runtime export can be planned, but no runtime artifact is exported by this script.
