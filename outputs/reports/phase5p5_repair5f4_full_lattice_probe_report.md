# Phase5.5 Repair5F Candidate Probe

This is diagnostic-only bounded UpdateParams evidence. It does not permit Phase5.5 or Phase6.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instance_ids: `[26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]`
- candidate_count: `47`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`

## Raw Coverage

- expected_raw_probe_rows: `5880`
- raw_rows_before_dedupe: `5880`
- raw_rows_after_dedupe: `5880`
- duplicate_raw_rows_dropped: `0`
- missing_raw_probe_rows: `0`

## Gates

- force_additive_parity_exact: `False`
- exact_additive_candidate_parity_exact: `False`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- support_validation_overlap_count: `0`
- f2f3_holdout_validation_overlap_count: `0`
- support_eval_leakage: `False`
- support_final_overlap_count: `0`
- support_final_overlap_ids: `[]`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- solver_semantic_changes: `False`
- safety_gates_passed: `False`
- final_holdout_ids_covered: `False`
- full_raw_probe_coverage: `True`
- full_f1_scope_evaluated: `False`
- candidate_lattice_oracle_gate_passed: `False`
- candidate_lattice_oracle_metric_gate_passed: `False`
- candidate_lattice_oracle_better_gt_worse: `True`
- candidate_lattice_oracle_mean_delta_le_m003: `True`
- candidate_lattice_oracle_ratio_worse_groups_le_1: `True`
- candidate_lattice_oracle_success_worse_groups_eq_0: `True`

## Paired Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| always_additive_defer | 120 | 1 | 116 | 1 | -0.0006178560394871787 |
| repair5f_bounded_updateparam_selector_random_candidate_diagnostic | 120 | 30 | 64 | 24 | -0.0012279542748290715 |
| repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic | 120 | 22 | 66 | 31 | 0.000991081857249996 |
| repair5f_candidate_lattice_oracle_static_proxy | 120 | 69 | 51 | 0 | -0.0176832772359661 |

## Interpretation

The lattice oracle is a headroom diagnostic over bounded UpdateParams candidates. A selector/runtime claim remains deferred until full held-out evidence beats random and shuffled diagnostics.
