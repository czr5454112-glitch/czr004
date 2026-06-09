# Phase5.5 Repair5G Dual-Channel Candidate Lattice

This is a diagnostic-only representation lattice for goal-aware dual-channel LTM.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`
- action_prediction_enabled: `false`

## Summary

- candidate_count: `10`
- components: `{'c_only': 2, 'c_plus_f': 2, 'c_plus_f_decay': 1, 'f_only': 2, 'goal_gated_wait': 2, 'parity': 1}`

## Candidates

| candidate_id | runtime_method | component | dual | lambda_cong | lambda_flow | rho_cong | rho_flow | notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| dcltm_additive_parity | repair5g_dual_additive_parity | parity | False | 1 | 0 | 1 | 1 | Exact additive LTM parity control; routes through legacy UpdateLTM semantics. |
| dcltm_c_only_locked_f4 | repair5g_dual_c_only_locked_f4 | c_only | True | 1 | 0 | 0.9 | 1 | C-only diagnostic matching the failed locked Repair5F static rule. |
| dcltm_c_only_best_f4_observed | repair5g_dual_c_only_best_f4_observed | c_only | True | 1 | 0 | 0.95 | 1 | C-only diagnostic matching the best observed F4 static candidate; not promotable. |
| dcltm_flow_only_025 | repair5g_dual_flow_only_025 | f_only | True | 0 | 0.25 | 1 | 1 | Flow-only committed goal-progress guidance with lambda_flow=0.25. |
| dcltm_flow_only_050 | repair5g_dual_flow_only_050 | f_only | True | 0 | 0.5 | 1 | 1 | Flow-only committed goal-progress guidance with lambda_flow=0.50. |
| dcltm_block_wait_cong_flow025 | repair5g_dual_block_wait_cong_flow025 | c_plus_f | True | 1 | 0.25 | 1 | 1 | Blocked/wait congestion plus committed goal-progress flow, lambda_flow=0.25. |
| dcltm_block_wait_cong_flow050 | repair5g_dual_block_wait_cong_flow050 | c_plus_f | True | 1 | 0.5 | 1 | 1 | Blocked/wait congestion plus committed goal-progress flow, lambda_flow=0.50. |
| dcltm_goal_gated_wait_025 | repair5g_dual_goal_gated_wait_025 | goal_gated_wait | True | 1 | 0.25 | 1 | 1 | Goal-gated wait: weakly penalize progress exits, strongly penalize non-progress exits. |
| dcltm_goal_gated_wait_050 | repair5g_dual_goal_gated_wait_050 | goal_gated_wait | True | 1 | 0.5 | 1 | 1 | Goal-gated wait with stronger flow discount. |
| dcltm_balanced_decay | repair5g_dual_balanced_decay | c_plus_f_decay | True | 1 | 0.25 | 0.95 | 0.95 | Balanced C/F decay at 0.95 with lambda_flow=0.25. |
