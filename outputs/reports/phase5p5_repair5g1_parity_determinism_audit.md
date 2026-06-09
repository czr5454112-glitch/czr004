# Phase5.5 Repair5G.1 Parity and Determinism Audit

This audit determines whether G2 may proceed to selector development. It does not permit Phase5.5 or Phase6.

## Verdict

- true_semantic_mismatch: `False`
- proceed_to_g2_selector_protocol: `True`
- classification_counts: `{'time_budget_sensitivity': 58}`
- phase5p5_allowed: `false`
- phase6_allowed: `false`

## Smoke Gates

- `additive_parity_exact`: `True`
- `laur_disable_parity_exact`: `True`
- `laur_force_additive_direct_parity_exact`: `True`
- `dual_additive_parity_exact`: `True`
- `dual_c_equiv_additive_parity_exact`: `True`
- `dual_c_equiv_locked_matches_scalar`: `True`
- `dual_c_equiv_best_f4_static_matches_scalar`: `True`
- `critical_smoke_gates_passed`: `True`

## Bulk Dev Gates

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

## Interpretation

Sequential G1 smoke parity is exact. Bulk dev discrepancies are classified as time-budget sensitivity or missing/reporting issues rather than semantic mismatches, so G2 may proceed with a fresh frozen protocol.

## G1 Headroom Check

- `oracle_better`: `82`
- `oracle_equal`: `38`
- `oracle_worse`: `0`
- `oracle_mean_delta_ratio_vs_ltm`: `-0.033505006472296615`
- `oracle_bootstrap_ci`: `{'ci_high': -0.028073538158008476, 'ci_low': -0.038997441793415265, 'mean': -0.033505006472296615, 'prob_mean_lt_0': 1.0, 'samples': 2000}`
- `flow_shield_component_present`: `True`
