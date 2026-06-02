# Phase5.5 Repair5F Selector Threshold Sweep

This sweep is trained/tuned only on support IDs. It does not permit Phase5.5 or Phase6.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- support_only_tuning: `true`
- final_holdout_used_for_tuning: `false`

## Best Support Spec

- selector_type: `group_balanced_utility`
- min_support_count: `10`
- min_effective_neighbors: `3`
- max_neighbor_distance: `999.0`
- min_predicted_margin: `0.001`
- max_candidate_worse_rate: `1.0`
- max_group_worse_rate: `1.0`
- non_additive_budget: `1.0`
- support_primary_passed: `True`
- better: `31`
- equal: `66`
- worse: `23`
- mean_delta_ratio_vs_ltm: `-0.0028752109667166794`
- selected_nonadditive_cases: `120`

## Selector Families

- `knn_utility`
- `radius_neighbor_abstain`
- `group_balanced_utility`
- `candidate_risk_capped`

## Feature Policy

The selected spec uses only the allowed numeric feature list from the training-context table. Seed, scenario name, instance identity, holdout outcomes, and holdout best-candidate columns are forbidden.
