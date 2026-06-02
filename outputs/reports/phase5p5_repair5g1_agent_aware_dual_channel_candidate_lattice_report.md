# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Candidate Lattice

This is diagnostic-only. It does not permit Phase5.5 or Phase6.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`
- action_prediction_enabled: `false`

## Summary

- candidate_count: `133`
- components: `{'agent_progress_f': 60, 'c_equiv': 7, 'diagnostic': 1, 'flow_shield': 36, 'global_f_small_lambda': 16, 'parity': 1, 'wait_gated': 12}`

## Candidates

| candidate_id | runtime_method | component | mode | lambda_flow | beta | max_shield | min_cost | notes |
|---|---|---|---|---:|---:|---:|---:|---|
| dcltm_additive_parity | repair5g_dual_additive_parity | parity | none | 0 | 0 | 0 | 0.25 | Legacy exact additive LTM parity control. |
| dcltm_c_equiv_additive | repair5g_dual_c_equiv_additive | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `additive`. |
| dcltm_c_equiv_c100_b100_w075_d090 | repair5g_dual_c_equiv_c100_b100_w075_d090 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c100_b100_w075_d090`. |
| dcltm_c_equiv_c125_b125_w075_d095 | repair5g_dual_c_equiv_c125_b125_w075_d095 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c125_b125_w075_d095`. |
| dcltm_c_equiv_c100_b125_w075_d100 | repair5g_dual_c_equiv_c100_b125_w075_d100 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c100_b125_w075_d100`. |
| dcltm_c_equiv_c100_b100_w075_d095 | repair5g_dual_c_equiv_c100_b100_w075_d095 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c100_b100_w075_d095`. |
| dcltm_c_equiv_c100_b100_w100_d090 | repair5g_dual_c_equiv_c100_b100_w100_d090 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c100_b100_w100_d090`. |
| dcltm_c_equiv_c100_b100_w075_d100 | repair5g_dual_c_equiv_c100_b100_w075_d100 | c_equiv | none | 0 | 0 | 0 | 0.25 | Scalar-equivalent C-only dual channel for `c100_b100_w075_d100`. |
| global_additive_lf0p01_min0p75 | repair5g1_global_additive_lf0p01_min0p75 | global_f_small_lambda | none | 0.01 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_additive_lf0p025_min0p75 | repair5g1_global_additive_lf0p025_min0p75 | global_f_small_lambda | none | 0.025 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_additive_lf0p05_min0p75 | repair5g1_global_additive_lf0p05_min0p75 | global_f_small_lambda | none | 0.05 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_additive_lf0p1_min0p75 | repair5g1_global_additive_lf0p1_min0p75 | global_f_small_lambda | none | 0.1 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c125_b125_w075_d095_lf0p01_min0p75 | repair5g1_global_c125_b125_w075_d095_lf0p01_min0p75 | global_f_small_lambda | none | 0.01 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c125_b125_w075_d095_lf0p025_min0p75 | repair5g1_global_c125_b125_w075_d095_lf0p025_min0p75 | global_f_small_lambda | none | 0.025 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c125_b125_w075_d095_lf0p05_min0p75 | repair5g1_global_c125_b125_w075_d095_lf0p05_min0p75 | global_f_small_lambda | none | 0.05 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c125_b125_w075_d095_lf0p1_min0p75 | repair5g1_global_c125_b125_w075_d095_lf0p1_min0p75 | global_f_small_lambda | none | 0.1 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b125_w075_d100_lf0p01_min0p75 | repair5g1_global_c100_b125_w075_d100_lf0p01_min0p75 | global_f_small_lambda | none | 0.01 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b125_w075_d100_lf0p025_min0p75 | repair5g1_global_c100_b125_w075_d100_lf0p025_min0p75 | global_f_small_lambda | none | 0.025 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b125_w075_d100_lf0p05_min0p75 | repair5g1_global_c100_b125_w075_d100_lf0p05_min0p75 | global_f_small_lambda | none | 0.05 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b125_w075_d100_lf0p1_min0p75 | repair5g1_global_c100_b125_w075_d100_lf0p1_min0p75 | global_f_small_lambda | none | 0.1 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b100_w075_d095_lf0p01_min0p75 | repair5g1_global_c100_b100_w075_d095_lf0p01_min0p75 | global_f_small_lambda | none | 0.01 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b100_w075_d095_lf0p025_min0p75 | repair5g1_global_c100_b100_w075_d095_lf0p025_min0p75 | global_f_small_lambda | none | 0.025 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b100_w075_d095_lf0p05_min0p75 | repair5g1_global_c100_b100_w075_d095_lf0p05_min0p75 | global_f_small_lambda | none | 0.05 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| global_c100_b100_w075_d095_lf0p1_min0p75 | repair5g1_global_c100_b100_w075_d095_lf0p1_min0p75 | global_f_small_lambda | none | 0.1 | 0 | 0 | 0.75 | G0-style global F small-lambda control. |
| agent_additive_lf0p01_min0p5 | repair5g1_agent_additive_lf0p01_min0p5 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p01_min0p75 | repair5g1_agent_additive_lf0p01_min0p75 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p01_min1 | repair5g1_agent_additive_lf0p01_min1 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p025_min0p5 | repair5g1_agent_additive_lf0p025_min0p5 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p025_min0p75 | repair5g1_agent_additive_lf0p025_min0p75 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p025_min1 | repair5g1_agent_additive_lf0p025_min1 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p05_min0p5 | repair5g1_agent_additive_lf0p05_min0p5 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p05_min0p75 | repair5g1_agent_additive_lf0p05_min0p75 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p05_min1 | repair5g1_agent_additive_lf0p05_min1 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p1_min0p5 | repair5g1_agent_additive_lf0p1_min0p5 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p1_min0p75 | repair5g1_agent_additive_lf0p1_min0p75 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p1_min1 | repair5g1_agent_additive_lf0p1_min1 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p2_min0p5 | repair5g1_agent_additive_lf0p2_min0p5 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p2_min0p75 | repair5g1_agent_additive_lf0p2_min0p75 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_additive_lf0p2_min1 | repair5g1_agent_additive_lf0p2_min1 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p01_min0p5 | repair5g1_agent_c125_b125_w075_d095_lf0p01_min0p5 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p01_min0p75 | repair5g1_agent_c125_b125_w075_d095_lf0p01_min0p75 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p01_min1 | repair5g1_agent_c125_b125_w075_d095_lf0p01_min1 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p025_min0p5 | repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p5 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p025_min0p75 | repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p025_min1 | repair5g1_agent_c125_b125_w075_d095_lf0p025_min1 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p05_min0p5 | repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p5 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p05_min0p75 | repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p75 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p05_min1 | repair5g1_agent_c125_b125_w075_d095_lf0p05_min1 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p1_min0p5 | repair5g1_agent_c125_b125_w075_d095_lf0p1_min0p5 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p1_min0p75 | repair5g1_agent_c125_b125_w075_d095_lf0p1_min0p75 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p1_min1 | repair5g1_agent_c125_b125_w075_d095_lf0p1_min1 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p2_min0p5 | repair5g1_agent_c125_b125_w075_d095_lf0p2_min0p5 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p2_min0p75 | repair5g1_agent_c125_b125_w075_d095_lf0p2_min0p75 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c125_b125_w075_d095_lf0p2_min1 | repair5g1_agent_c125_b125_w075_d095_lf0p2_min1 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p01_min0p5 | repair5g1_agent_c100_b125_w075_d100_lf0p01_min0p5 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p01_min0p75 | repair5g1_agent_c100_b125_w075_d100_lf0p01_min0p75 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p01_min1 | repair5g1_agent_c100_b125_w075_d100_lf0p01_min1 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p025_min0p5 | repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p5 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p025_min0p75 | repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p75 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p025_min1 | repair5g1_agent_c100_b125_w075_d100_lf0p025_min1 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p05_min0p5 | repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p5 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p05_min0p75 | repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p75 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p05_min1 | repair5g1_agent_c100_b125_w075_d100_lf0p05_min1 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p1_min0p5 | repair5g1_agent_c100_b125_w075_d100_lf0p1_min0p5 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p1_min0p75 | repair5g1_agent_c100_b125_w075_d100_lf0p1_min0p75 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p1_min1 | repair5g1_agent_c100_b125_w075_d100_lf0p1_min1 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p2_min0p5 | repair5g1_agent_c100_b125_w075_d100_lf0p2_min0p5 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p2_min0p75 | repair5g1_agent_c100_b125_w075_d100_lf0p2_min0p75 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b125_w075_d100_lf0p2_min1 | repair5g1_agent_c100_b125_w075_d100_lf0p2_min1 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p01_min0p5 | repair5g1_agent_c100_b100_w075_d095_lf0p01_min0p5 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p01_min0p75 | repair5g1_agent_c100_b100_w075_d095_lf0p01_min0p75 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p01_min1 | repair5g1_agent_c100_b100_w075_d095_lf0p01_min1 | agent_progress_f | agent_progress | 0.01 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p025_min0p5 | repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p5 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p025_min0p75 | repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p75 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p025_min1 | repair5g1_agent_c100_b100_w075_d095_lf0p025_min1 | agent_progress_f | agent_progress | 0.025 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p05_min0p5 | repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p5 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p05_min0p75 | repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p75 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p05_min1 | repair5g1_agent_c100_b100_w075_d095_lf0p05_min1 | agent_progress_f | agent_progress | 0.05 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p1_min0p5 | repair5g1_agent_c100_b100_w075_d095_lf0p1_min0p5 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p1_min0p75 | repair5g1_agent_c100_b100_w075_d095_lf0p1_min0p75 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p1_min1 | repair5g1_agent_c100_b100_w075_d095_lf0p1_min1 | agent_progress_f | agent_progress | 0.1 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p2_min0p5 | repair5g1_agent_c100_b100_w075_d095_lf0p2_min0p5 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.5 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p2_min0p75 | repair5g1_agent_c100_b100_w075_d095_lf0p2_min0p75 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 0.75 | Agent-aware F discount projected by current-agent goal progress. |
| agent_c100_b100_w075_d095_lf0p2_min1 | repair5g1_agent_c100_b100_w075_d095_lf0p2_min1 | agent_progress_f | agent_progress | 0.2 | 0 | 0 | 1 | Agent-aware F discount projected by current-agent goal progress. |
| shield_c125_b125_w075_d095_beta0p05_max0p25 | repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p25 | flow_shield | flow_shield | 0 | 0.05 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p05_max0p5 | repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p5 | flow_shield | flow_shield | 0 | 0.05 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p05_max0p75 | repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p75 | flow_shield | flow_shield | 0 | 0.05 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p1_max0p25 | repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p25 | flow_shield | flow_shield | 0 | 0.1 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p1_max0p5 | repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5 | flow_shield | flow_shield | 0 | 0.1 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p1_max0p75 | repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p75 | flow_shield | flow_shield | 0 | 0.1 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p2_max0p25 | repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p25 | flow_shield | flow_shield | 0 | 0.2 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p2_max0p5 | repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5 | flow_shield | flow_shield | 0 | 0.2 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p2_max0p75 | repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75 | flow_shield | flow_shield | 0 | 0.2 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p35_max0p25 | repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p25 | flow_shield | flow_shield | 0 | 0.35 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p35_max0p5 | repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p5 | flow_shield | flow_shield | 0 | 0.35 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c125_b125_w075_d095_beta0p35_max0p75 | repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75 | flow_shield | flow_shield | 0 | 0.35 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p05_max0p25 | repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p25 | flow_shield | flow_shield | 0 | 0.05 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p05_max0p5 | repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p5 | flow_shield | flow_shield | 0 | 0.05 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p05_max0p75 | repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p75 | flow_shield | flow_shield | 0 | 0.05 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p1_max0p25 | repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p25 | flow_shield | flow_shield | 0 | 0.1 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p1_max0p5 | repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p5 | flow_shield | flow_shield | 0 | 0.1 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p1_max0p75 | repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p75 | flow_shield | flow_shield | 0 | 0.1 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p2_max0p25 | repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p25 | flow_shield | flow_shield | 0 | 0.2 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p2_max0p5 | repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p5 | flow_shield | flow_shield | 0 | 0.2 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p2_max0p75 | repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p75 | flow_shield | flow_shield | 0 | 0.2 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p35_max0p25 | repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p25 | flow_shield | flow_shield | 0 | 0.35 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p35_max0p5 | repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p5 | flow_shield | flow_shield | 0 | 0.35 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b125_w075_d100_beta0p35_max0p75 | repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75 | flow_shield | flow_shield | 0 | 0.35 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p05_max0p25 | repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p25 | flow_shield | flow_shield | 0 | 0.05 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p05_max0p5 | repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p5 | flow_shield | flow_shield | 0 | 0.05 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p05_max0p75 | repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p75 | flow_shield | flow_shield | 0 | 0.05 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p1_max0p25 | repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p25 | flow_shield | flow_shield | 0 | 0.1 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p1_max0p5 | repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p5 | flow_shield | flow_shield | 0 | 0.1 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p1_max0p75 | repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p75 | flow_shield | flow_shield | 0 | 0.1 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p2_max0p25 | repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p25 | flow_shield | flow_shield | 0 | 0.2 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p2_max0p5 | repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p5 | flow_shield | flow_shield | 0 | 0.2 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p2_max0p75 | repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p75 | flow_shield | flow_shield | 0 | 0.2 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p35_max0p25 | repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p25 | flow_shield | flow_shield | 0 | 0.35 | 0.25 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p35_max0p5 | repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p5 | flow_shield | flow_shield | 0 | 0.35 | 0.5 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| shield_c100_b100_w075_d095_beta0p35_max0p75 | repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75 | flow_shield | flow_shield | 0 | 0.35 | 0.75 | 1 | Flow-shield C penalty reducer on current-agent progress edges only. |
| wait_additive_wp0p25_wn1 | repair5g1_wait_additive_wp0p25_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_additive_wp0p5_wn1 | repair5g1_wait_additive_wp0p5_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_additive_wp0p75_wn1p25 | repair5g1_wait_additive_wp0p75_wn1p25 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c125_b125_w075_d095_wp0p25_wn1 | repair5g1_wait_c125_b125_w075_d095_wp0p25_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c125_b125_w075_d095_wp0p5_wn1 | repair5g1_wait_c125_b125_w075_d095_wp0p5_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c125_b125_w075_d095_wp0p75_wn1p25 | repair5g1_wait_c125_b125_w075_d095_wp0p75_wn1p25 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b125_w075_d100_wp0p25_wn1 | repair5g1_wait_c100_b125_w075_d100_wp0p25_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b125_w075_d100_wp0p5_wn1 | repair5g1_wait_c100_b125_w075_d100_wp0p5_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b125_w075_d100_wp0p75_wn1p25 | repair5g1_wait_c100_b125_w075_d100_wp0p75_wn1p25 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b100_w075_d095_wp0p25_wn1 | repair5g1_wait_c100_b100_w075_d095_wp0p25_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b100_w075_d095_wp0p5_wn1 | repair5g1_wait_c100_b100_w075_d095_wp0p5_wn1 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| wait_c100_b100_w075_d095_wp0p75_wn1p25 | repair5g1_wait_c100_b100_w075_d095_wp0p75_wn1p25 | wait_gated | none | 0 | 0 | 0 | 0.25 | Wait-gated C-only control with reduced progress-exit wait spillover. |
| random_static_diagnostic | repair5g1_random_static_diagnostic | diagnostic | agent_progress | 0.025 | 0 | 0 | 0.75 | Deterministic random diagnostic candidate; never promotable. |
