# Phase5.5 Repair5G.5.18 G5.17 Lattice Autopsy

- decision: `g517_lattice_autopsy_passed_continue_surrogate_proposal`
- rows: `960`
- context_budget_pairs: `40`
- old_candidate_count: `14`
- repair_candidate_count: `10`
- repair_candidate_oracle_win_count: `0`
- repair_candidates_dominated_by_nearest_old: `3`
- old_winner_family_distribution: `{'block_heavy': 8, 'commit_heavy': 2, 'flow_decay': 8, 'low_beta_high_cap': 6, 'unknown': 2, 'wait_aggressive': 6, 'wait_conservative': 8}`

## Strong Old Neighborhoods

- `repair5g59_block_heavy_flow_guard` (block_heavy): wins `8`, mean_delta `-0.0177919439054942`
- `repair5g59_wait_conservative` (wait_conservative): wins `8`, mean_delta `-0.017267816922737027`
- `repair5g59_wait_aggressive` (wait_aggressive): wins `6`, mean_delta `-0.017243149866495156`
- `repair5g59_low_beta_high_cap` (low_beta_high_cap): wins `6`, mean_delta `0.014456532991504003`
- `repair5g59_slow_decay_high_shield` (flow_decay): wins `6`, mean_delta `0.03260375163139082`
- `repair5g59_commit_heavy_flow_guard` (commit_heavy): wins `2`, mean_delta `-0.0038445118152627775`
- `repair5g59_flow_decay` (flow_decay): wins `2`, mean_delta `0.0`
- `repair5g59_high_beta_cap_safe` (high_beta): wins `0`, mean_delta `-0.011527788374638059`

## Parameter Direction Autopsy

- `lower_beta`: candidates `10`, oracle wins `0`, mean delta `0.04444650730035671`
- `lower_cap`: candidates `10`, oracle wins `0`, mean delta `0.04444650730035671`
- `faster_congestion_decay`: candidates `4`, oracle wins `0`, mean delta `0.03658922110764366`
- `faster_flow_decay`: candidates `2`, oracle wins `0`, mean delta `0.044338765531383925`
- `static_boundary_or_c_only`: candidates `2`, oracle wins `0`, mean delta `0.06513454945063486`

The G5.17 adapter/probe path is valid, but the conservative G5.16 repair candidates remain weak or dominated. G5.18 should expand around block-heavy, wait, high-beta, low-beta-high-cap, and flow-decay neighborhoods instead of only lowering beta/cap.
