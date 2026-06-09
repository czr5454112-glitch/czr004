# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Smoke Report

This is diagnostic-only representation evidence. It does not permit Phase5.5 or Phase6.

## Gates

- build_passed: `True`
- schema_errors: `0`
- missing_rows: `0`
- no_solver_crashes: `True`
- all_costs_finite: `True`
- cost_bounds_respected: `True`
- additive_parity_exact: `True`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- dual_additive_parity_exact: `True`
- dual_c_equiv_additive_parity_exact: `True`
- dual_c_equiv_locked_matches_scalar: `True`
- dual_c_equiv_best_f4_static_matches_scalar: `True`
- critical_smoke_gates_passed: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- instance_ids: `[26, 27]`
- row_count: `156` / `156`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 12 | 0 | 12 | 0 | 0.0 |
| `laur_disable` | 12 | 0 | 12 | 0 | 0.0 |
| `laur_force_additive_direct` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5f4_best_static_c125_b125_w075_d095_diagnostic_only` | 12 | 3 | 8 | 1 | -0.004792740910000019 |
| `repair5f_candidate_additive_ltm` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5f_static_c100_b100_w075_d090` | 12 | 2 | 9 | 1 | -0.0031270715883333446 |
| `repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75` | 12 | 3 | 7 | 2 | -0.0022524498250000393 |
| `repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5` | 12 | 3 | 7 | 2 | -0.012368955305833337 |
| `repair5g_dual_additive_parity` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 12 | 0 | 12 | 0 | 0.0 |
| `repair5g_dual_c_equiv_c100_b100_w075_d090` | 12 | 2 | 9 | 1 | -0.0031270715883333446 |
| `repair5g_dual_c_equiv_c125_b125_w075_d095` | 12 | 3 | 8 | 1 | -0.004792740910000019 |
