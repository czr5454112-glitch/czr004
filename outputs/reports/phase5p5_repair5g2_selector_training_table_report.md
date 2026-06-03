# Phase5.5 Repair5G.2 Selector Training Table

Selector context rows for development-only G2 tuning. This does not permit Phase5.5 or Phase6.

## Boundary

- final_ids_used: `false`
- candidate_outcomes_in_context_features: `false`
- seed/scen retained only as join metadata
- phase5p5_allowed: `false`
- phase6_allowed: `false`

## Rows

- context_rows: `270`
- support_rows: `150`
- dev_rows: `120`
- final_id_rows: `0`

## Allowed Decision Features

- `agents`
- `map_width`
- `map_height`
- `obstacle_ratio`
- `free_cells`
- `density`
- `ltm_iterations`
- `returned_solutions_count_so_far`
- `committed_count`
- `blocked_count`
- `wait_event_count`
- `progress_committed_count`
- `nonprogress_committed_count`
- `blocked_per_committed`
- `wait_per_committed`
- `blocked_per_agent`
- `committed_per_agent`
- `progress_ratio`
- `c_update_count`
- `f_update_count`
- `c_nonzero_edges`
- `f_nonzero_edges`
- `c_flow_update_ratio`
- `cost_min`
- `cost_max`
- `cost_span`
- `cost_bounds_respected`
- `best_ratio_before`
- `has_incumbent_before`
- `improved_last_iteration`
