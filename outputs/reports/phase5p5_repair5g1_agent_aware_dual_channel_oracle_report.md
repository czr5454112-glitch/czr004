# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Oracle Report

This is development/diagnostic-only evidence. It does not permit Phase5.5 or Phase6.

## Gates

- dual_c_equiv_closed: `True`
- cost_bounds_respected: `True`
- dual_channel_oracle_better_gt_worse: `True`
- dual_channel_oracle_mean_delta_ratio_vs_ltm_lt_0: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`

## Oracle

- method: `repair5g1_agent_aware_dual_channel_oracle_static_proxy`
- rows: `120`
- better: `82`
- equal: `38`
- worse: `0`
- mean_delta_ratio_vs_ltm: `-0.033505006472296615`
- bootstrap_ci: `{'mean': -0.033505006472296615, 'ci_low': -0.038997441793415265, 'ci_high': -0.028073538158008476, 'prob_mean_lt_0': 1.0, 'samples': 2000}`

## Components

| component | candidates | best mean delta | mean of means | total better | total worse |
|---|---:|---:|---:|---:|---:|
| agent_progress_f | 60 | -0.0013597823116982802 | 0.0021751928750689516 | 1696 | 2047 |
| c_equiv | 7 | -0.0027456139927826157 | -0.0012935747716888472 | 177 | 153 |
| diagnostic | 1 | 0.001719045029763145 | 0.001719045029763145 | 29 | 37 |
| flow_shield | 36 | -0.014306860332393171 | -0.004100773448490892 | 1561 | 940 |
| global_f_small_lambda | 16 | 0.00037429227568964855 | 0.002039355432359794 | 446 | 555 |
| wait_gated | 12 | 0.0008808565518793092 | 0.00239738585142675 | 313 | 423 |

## Candidate Ranking

| rank | method | component | better | equal | worse | mean delta ratio vs LTM |
|---:|---|---|---:|---:|---:|---:|
| 1 | `repair5g1_agent_aware_dual_channel_oracle_static_proxy` |  | 82 | 38 | 0 | -0.033505006472296615 |
| 2 | `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | flow_shield | 67 | 37 | 16 | -0.014306860332393171 |
| 3 | `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | flow_shield | 64 | 35 | 21 | -0.013736227771605257 |
| 4 | `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | flow_shield | 63 | 40 | 17 | -0.013149905779432201 |
| 5 | `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | flow_shield | 61 | 40 | 19 | -0.012989982687452996 |
| 6 | `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p75` | flow_shield | 57 | 42 | 21 | -0.010387837632398303 |
| 7 | `repair5g_shuffled_goal_progress_diagnostic` |  | 51 | 49 | 20 | -0.009592052687144071 |
| 8 | `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p5` | flow_shield | 52 | 46 | 22 | -0.008704894452051727 |
| 9 | `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p75` | flow_shield | 50 | 44 | 26 | -0.007929312204278265 |
| 10 | `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p5` | flow_shield | 49 | 46 | 25 | -0.007922400645637168 |
| 11 | `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p5` | flow_shield | 52 | 53 | 15 | -0.0077079518753898416 |
| 12 | `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5` | flow_shield | 43 | 53 | 24 | -0.007072366789991304 |
| 13 | `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p5` | flow_shield | 48 | 48 | 24 | -0.00613575942311966 |
| 14 | `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p5` | flow_shield | 49 | 51 | 20 | -0.005907960302170944 |
| 15 | `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p75` | flow_shield | 43 | 45 | 32 | -0.0051169978255263295 |
| 16 | `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | flow_shield | 52 | 46 | 22 | -0.004920278463801723 |
| 17 | `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p5` | flow_shield | 45 | 51 | 24 | -0.0045738271352069 |
| 18 | `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p75` | flow_shield | 43 | 49 | 28 | -0.004360946869547013 |
| 19 | `repair5g_dual_c_equiv_c100_b125_w075_d100` | c_equiv | 31 | 65 | 24 | -0.0027456139927826157 |
| 20 | `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p75` | flow_shield | 48 | 46 | 26 | -0.0026863721548017307 |
| 21 | `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p5` | flow_shield | 41 | 49 | 30 | -0.0026021448838879422 |
| 22 | `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p75` | flow_shield | 40 | 54 | 26 | -0.0023870650825689715 |
| 23 | `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p5` | flow_shield | 40 | 55 | 25 | -0.0023666628169059884 |
| 24 | `repair5g_dual_c_equiv_c125_b125_w075_d095` | c_equiv | 36 | 62 | 22 | -0.002227996893353449 |
| 25 | `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p25` | flow_shield | 34 | 57 | 29 | -0.0021444721513304435 |
