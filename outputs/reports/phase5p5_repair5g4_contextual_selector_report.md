# Phase5.5 Repair5G.4 Contextual Selector Report

Offline learning-bridge diagnostic only. No runtime learned selector is integrated here.

## Gates

- `learned_selector_uses_no_forbidden_features`: `True`
- `learned_selector_not_map_agent_lookup_only`: `True`
- `learned_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010`: `True`
- `learned_selector_bootstrap_probability_mean_delta_lt_0_ge_0p99`: `True`
- `learned_selector_success_worse_than_ltm_groups_eq_0`: `True`
- `learned_selector_beats_static_or_matches_within_0p001`: `True`
- `learned_selector_beats_shuffled_label_diagnostic`: `True`
- `learned_selector_beats_random_feature_diagnostic`: `True`
- `runtime_integration_feasible`: `False`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `learning_bridge_dev_gates_passed`: `True`

## Best Selector

- name: `decision_stump_selector`
- metrics: `{'rows': 120, 'better': 67, 'equal': 6, 'worse': 8, 'mean_delta_ratio_vs_ltm': -0.025178461936543203, 'median_delta_ratio_vs_ltm': -0.02222222221999992, 'bootstrap': {'mean': -0.025178461936543203, 'ci_low': -0.031791537150864184, 'ci_high': -0.018782733122716035, 'prob_mean_lt_0': 1.0, 'samples': 2000}, 'ratio_worse_than_ltm_groups': 0, 'success_worse_than_ltm_groups': 0}`
