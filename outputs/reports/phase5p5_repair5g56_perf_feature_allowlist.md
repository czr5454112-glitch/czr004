# Phase5.5 Repair5G.5.6 Performance Feature Allowlist

- feature_rows: `239`
- perf_safe_features: `["agents", "best_ratio_before", "blocked_count", "blocked_per_agent", "blocked_per_committed", "c_flow_update_ratio", "c_nonzero_edges", "c_update_count", "committed_count", "committed_per_agent", "density", "f_nonzero_edges", "f_update_count", "free_cells", "has_incumbent_before", "improved_last_iteration", "ltm_iterations", "map_height", "map_width", "nonprogress_committed_count", "obstacle_ratio", "progress_committed_count", "progress_ratio", "returned_solutions_count_so_far", "wait_event_count", "wait_per_committed"]`
- audit_only_features: `["cost_bounds_respected", "cost_max", "cost_min", "cost_span"]`
- forbidden_feature_columns: `[]`
- perf_feature_allowlist_passed: `True`

Cost-audit features are audit-only and cannot support later runtime-performance claims.
