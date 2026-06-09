# Phase5.5 Repair5G.5.2 UpdatePolicy Method Stats

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Gates

- `runtime_rows_full`: `True`
- `expected_rows_full`: `True`
- `missing_rows`: `0`
- `schema_errors`: `0`
- `solver_crash_count`: `0`
- `semantic_parity_mismatch_count`: `0`
- `selector_logs_present`: `True`
- `selector_update_log_rows`: `523`
- `allowed_feature_policy_passed`: `True`
- `forbidden_feature_policy_passed`: `True`
- `unexpected_runtime_features`: `[]`
- `forbidden_runtime_features`: `[]`
- `all_costs_finite`: `True`
- `cost_bounds_respected`: `True`
- `force_additive_policy_compliant`: `True`
- `disable_policy_compliant`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `aaai_ready`: `False`
- `runtime_always_static_exact_matches_static`: `False`
- `runtime_always_static_max_regret_vs_static`: `0.08146453089000016`
- `runtime_always_map_agent_exact_matches_map_agent`: `False`
- `runtime_always_map_agent_max_regret_vs_map_agent`: `0.06535141799999988`
- `selector_shadow_static_matches_static`: `False`
- `selected_params_hash_matches_expected`: `True`
- `fallback_reason_logged_for_all_fallbacks`: `True`
- `updatepolicy_equivalence_passed`: `False`

## Scope

- `maps`: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- `agent_counts`: `[50, 100]`
- `instance_ids`: `[146, 147, 148, 149, 150, 151, 152, 153, 154, 155]`
- `time_limit_sec`: `3.0`
- `ltm_max_iterations`: `4`
- `row_count`: `1080`

## Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 60 | 0 | 49 | 0 | 0.0 |
| `laur_disable` | 60 | 1 | 49 | 0 | 0.0 |
| `laur_force_additive_direct` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5g2_best_frozen_static_candidate` | 60 | 26 | 14 | 9 | -0.016159006723795923 |
| `repair5g2_frozen_static_or_selector` | 60 | 28 | 14 | 7 | -0.017933839279306123 |
| `repair5g51_runtime_always_static_flow_shield` | 60 | 25 | 14 | 10 | -0.00979251324767346 |
| `repair5g51_runtime_bad_g5_stump` | 60 | 9 | 22 | 18 | 0.009659311056734671 |
| `repair5g52_runtime_always_map_agent_exact` | 60 | 24 | 14 | 11 | -0.011012938574408163 |
| `repair5g52_runtime_always_static_exact` | 60 | 25 | 14 | 10 | -0.009864137592367338 |
| `repair5g52_runtime_disable_exact` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5g52_runtime_force_additive_exact` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5g52_runtime_selector_shadow_static` | 60 | 25 | 14 | 10 | -0.00979251324767346 |
| `repair5g5_contextual_flow_shield_selector_disable` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5g5_contextual_flow_shield_selector_force_additive_parity` | 60 | 0 | 48 | 1 | 0.0004106462426530584 |
| `repair5g_dual_additive_parity` | 60 | 0 | 49 | 0 | 0.0 |
| `repair5g_dual_c_equiv_additive` | 60 | 0 | 49 | 0 | 0.0 |
