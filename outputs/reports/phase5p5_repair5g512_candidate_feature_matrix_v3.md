# Phase5.5 Repair5G.5.12 Candidate Feature Matrix v3

- decision: `feature_v3_passed_continue_candidate_ranker`
- perf_safe_candidate_rows: `840`
- contexts: `60`
- candidates: `14`
- split_counts: `{'dev': 420, 'train': 420}`
- feature_count: `42`
- forbidden_feature_count: `0`
- candidate_param_features_present: `True`
- interaction_features_present: `True`
- feature_signal_limited: `true`
- missing_runtime_context_features_reported: `true`
- gates: `{'perf_safe_candidate_rows_ge_840': True, 'forbidden_feature_count_eq_0': True, 'candidate_param_features_present': True, 'interaction_features_present': True, 'train_dev_split_seed_based': True, 'grouped_context_ids_preserved': True}`

Performance-safe features are restricted to map/agent/iteration metadata, trace-event count, candidate parameters, candidate family flags, and interactions between available context counts and candidate parameters. Score, delta, oracle, regret, rank, label, target, probe, solution, action, priority, restart, h-value, and candidate-deletion fields are excluded from `feature_*` columns.
