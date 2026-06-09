# Repair5G.5.25 Trace Provenance and Blocker

- schema_version: `phase5p5_repair5g525_trace_provenance_and_blocker_summary_v1`
- decision: `old_raw_sha_mismatch_requires_fresh_g525_trace_probe`
- available_from_g524_raw_checkpoint: `['agents', 'blocked_events', 'committed_nonprogress_events', 'committed_progress_events', 'feature_names', 'feature_names[]', 'feature_values', 'feature_values[]', 'iteration', 'map', 'method', 'node_budget', 'scen', 'schema_version', 'seed', 'time_remaining_sec', 'trace_events', 'trace_events[]', 'trace_events[].agent_id', 'trace_events[].at_goal', 'trace_events[].from_id', 'trace_events[].kind', 'trace_events[].to_id', 'traffic_before_edges', 'traffic_before_edges[]', 'traffic_before_flow_nonzero_edges', 'traffic_before_full_sparse_edges', 'traffic_before_full_sparse_edges[]', 'traffic_before_hash', 'traffic_before_hash_full', 'traffic_before_nonzero_edges', 'wait_nonprogress_edges', 'wait_progress_edges']`
- critical_fields_missing: `['blocked_reason_and_competing_neighbor_rank']`
- blocked_reason_and_competing_neighbor_rank_matters: `It separates useful blocked progress edges from candidate-induced failure and rank-margin risk before applying UpdateParams.`
- raw_sha_mismatch_cause: `unknown`
- mismatch_explanations_considered: `['append_or_resume_after_manifest', 'regenerated_logs', 'line_ending_difference', 'different_local_file_path', 'unknown']`
- self_consistent_committed_tables: `{'context_budget_rows': 120, 'candidate_budget_rows': 5280, 'pairwise_budget_rows': 113520, 'feature_count': 73, 'forbidden_feature_count': 0}`
- do_not_mine_old_raw_for_new_model_features: `True`
- fresh_g525_trace_probe_required: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`
