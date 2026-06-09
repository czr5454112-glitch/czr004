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
- instance_ids: `[21, 22, 23, 24, 25]`
- candidate_count: `47`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`

## Raw Coverage

- expected_raw_probe_rows: `1530`
- raw_rows_before_dedupe: `1530`
- raw_rows_after_dedupe: `1530`
- duplicate_raw_rows_dropped: `0`
- missing_raw_probe_rows: `0`

## Gates

- force_additive_parity_exact: `True`
- exact_additive_candidate_parity_exact: `True`
- support_eval_leakage: `False`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- solver_semantic_changes: `False`
- safety_gates_passed: `True`
- final_holdout_ids_covered: `True`
- full_raw_probe_coverage: `True`
- full_f1_scope_evaluated: `True`
- candidate_lattice_oracle_gate_passed: `True`
- candidate_lattice_oracle_metric_gate_passed: `True`
- candidate_lattice_oracle_better_gt_worse: `True`
- candidate_lattice_oracle_mean_delta_le_m003: `True`
- candidate_lattice_oracle_ratio_worse_groups_le_1: `True`
- candidate_lattice_oracle_success_worse_groups_eq_0: `True`

## Paired Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| always_additive_defer | 30 | 0 | 30 | 0 | 0.0 |
| repair5e5_crossfold_utility_reranker | 30 | 4 | 22 | 4 | -0.0009245170596666741 |
| repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 30 | 7 | 20 | 3 | -0.0039024738501666654 |
| repair5f_bounded_updateparam_selector_random_candidate_diagnostic | 30 | 6 | 18 | 6 | 0.001419514395033339 |
| repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic | 30 | 4 | 19 | 7 | 0.0009148892173333441 |
| repair5f_candidate_lattice_oracle_static_proxy | 30 | 17 | 13 | 0 | -0.018311948514033324 |

## Interpretation

The force-additive and exact additive parity controls are now exact. The bounded
UpdateParams lattice oracle remains strong on the full final holdout and remains
stronger than Repair5F random/shuffled diagnostics. This closes the Repair5F.1
safety-parity gate for the oracle diagnostic, but it is not a selector/runtime
claim. `phase5p5_allowed=false` and `phase6_allowed=false` remain mandatory.
