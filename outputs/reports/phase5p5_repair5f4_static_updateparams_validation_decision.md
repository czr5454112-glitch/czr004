# Phase5.5 Repair5F.4 Validation Decision

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- mandatory_gates_passed: `False`

F4-A does not pass all required diagnostic gates. Do not promote and do not claim Phase5.5 or Phase6 evidence.

Failed gates: `['main_static_better_gt_worse', 'main_static_mean_delta_ratio_vs_ltm_lt_0', 'main_static_bootstrap_ci_upper_le_0', 'main_static_ratio_worse_than_ltm_groups_le_1', 'main_static_beats_deterministic_random_candidate_diagnostic']`

Analyze the worst groups and component ablations before changing selector design.
