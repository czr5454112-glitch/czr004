# Phase5.5 Repair5G Dual-Channel Oracle Report

This is development/diagnostic-only evidence on IDs 26..45. It does not permit Phase5.5 or Phase6.

## Gates

- dual_additive_parity_exact: `True`
- cost_bounds_respected: `True`
- dual_channel_oracle_better_gt_worse: `False`
- dual_channel_oracle_mean_delta_ratio_vs_ltm_lt_0: `False`
- phase5p5_allowed: `False`
- phase6_allowed: `False`

## Oracle

- method: `repair5g_dual_channel_oracle_static_proxy`
- rows: `120`
- better: `29`
- equal: `55`
- worse: `36`
- mean_delta_ratio_vs_ltm: `0.001879629688233328`
- bootstrap_ci: `{'mean': 0.001879629688233328, 'ci_low': -0.00205080619791666, 'ci_high': 0.006099029348233336, 'samples': 2000}`

## Candidate Ranking

| rank | method | better | equal | worse | mean delta ratio vs LTM |
|---:|---|---:|---:|---:|---:|
| 1 | `repair5g_dual_channel_oracle_static_proxy` | 29 | 55 | 36 | 0.001879629688233328 |
| 2 | `repair5g_dual_c_only_best_f4_observed` | 17 | 61 | 42 | 0.007440336798399994 |
| 3 | `repair5g_dual_c_only_locked_f4` | 15 | 62 | 43 | 0.007675997201349986 |
| 4 | `repair5g_shuffled_goal_progress_diagnostic` | 13 | 62 | 45 | 0.010474970962683326 |
| 5 | `repair5g_dual_goal_gated_wait_025` | 4 | 68 | 48 | 0.017697362382433326 |
| 6 | `repair5g_dual_block_wait_cong_flow025` | 2 | 69 | 49 | 0.018511684814274988 |
| 7 | `repair5g_dual_balanced_decay` | 5 | 66 | 49 | 0.018833444063524992 |
| 8 | `repair5g_random_dual_candidate_diagnostic` | 5 | 69 | 46 | 0.019861634269858323 |
| 9 | `repair5g_dual_block_wait_cong_flow050` | 0 | 70 | 50 | 0.021779983580524985 |
| 10 | `repair5g_dual_flow_only_025` | 0 | 70 | 50 | 0.022428777828941655 |
| 11 | `repair5g_dual_flow_only_050` | 0 | 70 | 50 | 0.022428777828941655 |
| 12 | `repair5g_dual_goal_gated_wait_050` | 0 | 70 | 50 | 0.022428777828941655 |

## Components

| component | candidates | best mean delta | mean of means | total better | total worse |
|---|---:|---:|---:|---:|---:|
| c_only | 2 | 0.007440336798399994 | 0.00755816699987499 | 32 | 85 |
| c_plus_f | 2 | 0.018511684814274988 | 0.020145834197399987 | 2 | 99 |
| c_plus_f_decay | 1 | 0.018833444063524992 | 0.018833444063524992 | 5 | 49 |
| f_only | 2 | 0.022428777828941655 | 0.022428777828941655 | 0 | 100 |
| goal_gated_wait | 2 | 0.017697362382433326 | 0.02006307010568749 | 4 | 98 |
