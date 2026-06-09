# Phase5.5 Repair5G.5.1 Runtime Hook Sanity Report

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `runtime_rows_full`: `True`
- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `semantic_parity_mismatch_count`: `0`
- `selector_logs_present`: `True`
- `selector_update_log_rows`: `754`
- `allowed_feature_policy_passed`: `True`
- `forbidden_feature_policy_passed`: `True`
- `unexpected_runtime_features`: `[]`
- `forbidden_runtime_features`: `[]`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `force_additive_policy_compliant`: `False`
- `disable_policy_compliant`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `aaai_ready`: `False`
- `always_static_matches_or_policy_equivalent`: `False`
- `always_static_max_regret_vs_static`: `0.16188178529000008`
- `always_map_agent_matches_or_policy_equivalent`: `False`
- `always_map_agent_max_regret_vs_map_agent`: `0.15150784077000012`
- `always_additive_matches_additive_under_parity_policy`: `True`
- `bad_g5_stump_classified_failed_or_weak`: `True`
- `runtime_hook_sanity_passed`: `False`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[136, 137, 138, 139, 140, 141, 142, 143, 144, 145]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `780`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 60 | 1 | 54 | 0 | 0.0 |
| `laur_disable` | 60 | 1 | 51 | 3 | 0.0 |
| `laur_force_additive_direct` | 60 | 1 | 51 | 3 | 0.0 |
| `repair5f_candidate_additive_ltm` | 60 | 1 | 53 | 1 | 0.0 |
| `repair5g2_best_frozen_static_candidate` | 60 | 30 | 12 | 14 | -0.015455739176862769 |
| `repair5g2_frozen_static_or_selector` | 60 | 30 | 13 | 14 | -0.015290301806923094 |
| `repair5g51_runtime_always_additive_selector` | 60 | 3 | 49 | 5 | 0.0008985943775999994 |
| `repair5g51_runtime_always_map_agent_selector` | 60 | 28 | 11 | 18 | -0.006100098907200024 |
| `repair5g51_runtime_always_static_flow_shield` | 60 | 27 | 13 | 15 | -0.006495710798846173 |
| `repair5g51_runtime_bad_g5_stump` | 60 | 10 | 25 | 23 | 0.00703853401067308 |
| `repair5g_dual_additive_parity` | 60 | 1 | 50 | 4 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 60 | 3 | 52 | 2 | 0.0 |
