# Phase5.5 Repair5G.4 Time Iteration Stress Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `selected_3s_negative`: `True`
- `selected_5s_not_reversed`: `True`
- `selected_10s_not_reversed`: `True`
- `selected_8_iterations_not_broad_harm`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `stress_protocol_passed`: `True`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145]`
- `time_limit_sec`: `[1.0, 3.0, 5.0, 10.0]`
- `ltm_max_iterations`: `[2, 4, 8]`
- `row_count`: `25920`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 1440 | 6 | 1314 | 0 | -7.568507284090931e-05 |
| `laur_disable` | 1440 | 9 | 1309 | 2 | -0.00012489991306818203 |
| `laur_force_additive_direct` | 1440 | 6 | 1310 | 4 | -9.628693209249464e-05 |
| `repair5f_candidate_additive_ltm` | 1440 | 8 | 1311 | 1 | -8.358930771969711e-05 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 1440 | 709 | 443 | 168 | -0.014892081142097195 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 1440 | 446 | 667 | 207 | -0.0061228894775852945 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 1440 | 679 | 472 | 169 | -0.014045606718108505 |
| `repair5g2_best_frozen_static_candidate` | 1440 | 679 | 472 | 169 | -0.014045606718108505 |
| `repair5g2_c_equiv_best_frozen_baseline` | 1440 | 215 | 889 | 216 | 0.00026937202398939444 |
| `repair5g2_frozen_static_or_selector` | 1440 | 613 | 598 | 109 | -0.01332257944519135 |
| `repair5g2_g1_top_diagnostic_candidate` | 1440 | 679 | 472 | 169 | -0.014045606718108505 |
| `repair5g4_random_flow_shield_diagnostic_seed0` | 1440 | 631 | 510 | 179 | -0.01236480159777677 |
| `repair5g4_shuffled_flow_shield_diagnostic_seed0` | 1440 | 681 | 475 | 164 | -0.014373199195279214 |
| `repair5g_dual_additive_parity` | 1440 | 10 | 1305 | 5 | -0.0001302778111523883 |
| `repair5g_dual_c_equiv_additive` | 1440 | 3 | 1298 | 19 | 8.836908328246013e-05 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 1440 | 228 | 879 | 213 | 1.1111330695981388e-05 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 1440 | 215 | 889 | 216 | 0.00026937202398939444 |

## Interpretation

1s may be noisy; 3s should reproduce sign; 5s/10s should not reverse sign; 8 iterations should not introduce broad harm.
