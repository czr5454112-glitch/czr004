# Phase5.5 Repair5F Candidate Probe

This is diagnostic-only bounded UpdateParams evidence. It does not permit Phase5.5 or Phase6.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`

## Scope

- maps: `['random-32-32-20']`
- agent_counts: `[50]`
- instance_ids: `[21, 22, 23, 24, 25]`
- candidate_count: `47`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`

## Gates

- force_additive_parity_exact: `True`
- support_eval_leakage: `False`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- solver_semantic_changes: `False`
- final_holdout_ids_covered: `True`
- full_f1_scope_evaluated: `False`
- candidate_lattice_oracle_gate_passed: `False`
- candidate_lattice_oracle_better_gt_worse: `True`
- candidate_lattice_oracle_mean_delta_le_m003: `True`
- candidate_lattice_oracle_ratio_worse_groups_le_1: `True`
- candidate_lattice_oracle_success_worse_groups_eq_0: `True`

## Paired Method Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| always_additive_defer | 5 | 0 | 5 | 0 | 0.0 |
| repair5e5_crossfold_utility_reranker | 5 | 0 | 3 | 2 | 0.007638777474000014 |
| repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 0 | 3 | 2 | 0.004401304884000012 |
| repair5f_bounded_updateparam_selector_random_candidate_diagnostic | 5 | 0 | 3 | 2 | 0.007098641640000025 |
| repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic | 5 | 0 | 3 | 2 | 0.0036766672020000168 |
| repair5f_candidate_lattice_oracle_static_proxy | 5 | 3 | 2 | 0 | -0.007741062115999941 |

## Interpretation

The lattice oracle is a headroom diagnostic over bounded UpdateParams candidates. A selector/runtime claim remains deferred until full held-out evidence beats random and shuffled diagnostics.
