# Phase5.5 Repair5G.2 Support Probe Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `full_expected_rows`: `True`
- `missing_rows_zero`: `True`
- `schema_errors_zero`: `True`
- `no_solver_crashes`: `True`
- `additive_parity_exact`: `False`
- `always_additive_defer_parity_exact`: `False`
- `laur_disable_parity_exact`: `False`
- `laur_force_additive_direct_parity_exact`: `False`
- `dual_additive_parity_exact`: `False`
- `dual_c_equiv_additive_parity_exact`: `False`
- `dual_c_equiv_locked_matches_scalar`: `False`
- `dual_c_equiv_best_f4_static_matches_scalar`: `False`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `support_ids_only_1_25`: `True`
- `protocol_gates_passed`: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
- row_count: `9000` / `9000`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 150 | 6 | 141 | 1 | 0.00030605698542253597 |
| `laur_disable` | 150 | 7 | 136 | 5 | 0.0002981308523913052 |
| `laur_force_additive_direct` | 150 | 6 | 134 | 7 | 0.0003025151296323538 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 150 | 40 | 71 | 37 | 1.6836685478576515e-05 |
| `repair5f_candidate_additive_ltm` | 150 | 6 | 137 | 4 | 0.00029598602611510875 |
| `repair5f_static_c100_b100_w075_d090` | 150 | 40 | 76 | 33 | -0.0005690420406595729 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p75` | 150 | 39 | 78 | 31 | -0.0012846890406056246 |
| `repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p75` | 150 | 45 | 68 | 34 | -0.0025711690953357075 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p75` | 150 | 43 | 71 | 34 | -0.0002762986528226894 |
| `repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p75` | 150 | 44 | 73 | 31 | -0.002052056776866199 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75` | 150 | 45 | 71 | 31 | -0.00014994617286523876 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p75` | 150 | 41 | 71 | 35 | -0.0026280318851654594 |
| `repair5g1_random_static_diagnostic` | 150 | 41 | 73 | 32 | -0.0025418910952127597 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p25` | 150 | 55 | 68 | 24 | -0.0048755544885248185 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p5` | 150 | 52 | 68 | 27 | -0.0029690314769428485 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p05_max0p75` | 150 | 52 | 68 | 27 | -0.0029690314769428485 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p25` | 150 | 56 | 72 | 20 | -0.0049471558021418425 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p5` | 150 | 60 | 61 | 28 | -0.0067460846194326235 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p1_max0p75` | 150 | 61 | 57 | 30 | -0.006749017596214282 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p25` | 150 | 54 | 62 | 32 | -0.003237901054992859 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p5` | 150 | 65 | 56 | 27 | -0.00863692933782608 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p2_max0p75` | 150 | 77 | 49 | 22 | -0.013519009546617016 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p25` | 150 | 55 | 65 | 28 | -0.005320046772892081 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p5` | 150 | 70 | 59 | 19 | -0.00990995358390844 |
| `repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75` | 150 | 81 | 46 | 20 | -0.017827223994999995 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p25` | 150 | 50 | 72 | 25 | -0.004098155769253519 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p5` | 150 | 48 | 71 | 28 | -0.001515877488723401 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p05_max0p75` | 150 | 48 | 71 | 28 | -0.001515877488723401 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p25` | 150 | 54 | 68 | 26 | -0.006841195413751776 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p5` | 150 | 61 | 65 | 23 | -0.006669832194808511 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p1_max0p75` | 150 | 62 | 63 | 22 | -0.007946352592246473 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p25` | 150 | 56 | 68 | 25 | -0.00372962195327464 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p5` | 150 | 65 | 65 | 19 | -0.010708966397690135 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p2_max0p75` | 150 | 76 | 49 | 24 | -0.013985886479113474 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p25` | 150 | 51 | 70 | 27 | -0.004501930246338025 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p5` | 150 | 71 | 60 | 16 | -0.010163484017673753 |
| `repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75` | 150 | 86 | 43 | 19 | -0.016762164801661966 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p25` | 150 | 43 | 72 | 32 | -0.00360515495706383 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p5` | 150 | 52 | 66 | 28 | -0.0058806940304857 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p05_max0p75` | 150 | 53 | 67 | 27 | -0.005838986980624098 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p25` | 150 | 55 | 70 | 22 | -0.006302904985697184 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5` | 150 | 57 | 61 | 29 | -0.008510910319807137 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p75` | 150 | 60 | 57 | 29 | -0.00846950278663571 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p25` | 150 | 56 | 63 | 29 | -0.0052834336506099285 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5` | 150 | 74 | 56 | 18 | -0.012404121359649993 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75` | 150 | 79 | 47 | 22 | -0.015032607396028557 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p25` | 150 | 52 | 67 | 29 | -0.005141131922414285 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p5` | 150 | 70 | 55 | 22 | -0.0100750208051357 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75` | 150 | 88 | 41 | 19 | -0.019722668544262405 |
| `repair5g2_random_candidate_diagnostic` | 150 | 54 | 63 | 30 | -0.005229342665735709 |
| `repair5g2_shuffled_flow_shield_diagnostic` | 150 | 79 | 51 | 19 | -0.012939638660435713 |
| `repair5g2_shuffled_goal_progress_diagnostic` | 150 | 76 | 54 | 19 | -0.012461178586673758 |
| `repair5g_dual_additive_parity` | 150 | 7 | 134 | 7 | 0.0004893022714492767 |
| `repair5g_dual_c_equiv_additive` | 150 | 7 | 133 | 8 | 0.0014319704335766428 |
| `repair5g_dual_c_equiv_c100_b100_w075_d090` | 150 | 38 | 74 | 35 | 8.117629393525359e-05 |
| `repair5g_dual_c_equiv_c100_b100_w075_d095` | 150 | 34 | 79 | 34 | -0.0005833508552340434 |
| `repair5g_dual_c_equiv_c100_b100_w075_d100` | 150 | 42 | 76 | 30 | -0.0014167751446142773 |
| `repair5g_dual_c_equiv_c100_b125_w075_d100` | 150 | 37 | 76 | 34 | -1.3029253249998866e-05 |
| `repair5g_dual_c_equiv_c125_b125_w075_d095` | 150 | 39 | 71 | 37 | 1.6836685478576515e-05 |
