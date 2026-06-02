# Phase5.5 Repair5F Selector Training Table

This is diagnostic-only selector context construction. It does not permit Phase5.5 or Phase6.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- final_holdout_outcomes_in_contexts: `false`

## Outputs

- train_contexts: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f_selector_train_contexts.csv`
- holdout_contexts: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f_selector_holdout_contexts.csv`
- train rows: `120`
- holdout rows: `30`

## Feature Policy

- Selection features are numeric case/runtime features only.
- `seed` and `scen` are retained only as join metadata, not decision features.
- `map_family` is retained only for diagnostics and group reporting.
- Holdout candidate outcomes and holdout best-candidate fields are excluded.

Allowed decision features:

- `agents`
- `map_width`
- `map_height`
- `obstacle_ratio`
- `free_cells`
- `density`
- `iteration`
- `time_remaining_sec`
- `max_iterations`
- `has_solution_before`
- `best_ratio_before`
- `improved_last_iteration`
- `returned_solutions_count_so_far`
- `committed_count`
- `blocked_count`
- `wait_event_count`
- `goal_wait_ignored_count`
- `blocked_per_committed`
- `wait_per_committed`
- `blocked_per_agent`
- `committed_per_agent`
- `nonzero_edges_before`
- `max_raw_before`
- `mean_topk_raw_before`
- `max_weight_before`
- `topk_raw_delta_mean`
- `topk_raw_delta_max`
- `new_nonzero_edges_count`
- `topk_blocked_edge_concentration`
- `entropy_edge_usage`
- `local_degree_mean_topk`
- `current_additive_max_normalized_weight`
- `weight_entropy`
- `saturated_edge_count`

Forbidden leakage fields:

- `instance_id`
- `seed`
- `scen`
- `candidate outcome columns from holdout`
- `holdout best candidate`
- `holdout ratio_delta_vs_ltm`
- `holdout success_delta`
- `final solver outcome not available before choosing`
