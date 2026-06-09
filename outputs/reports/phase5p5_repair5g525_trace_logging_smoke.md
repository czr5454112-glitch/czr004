# Repair5G.5.25 Trace Logging Smoke

- schema_version: `phase5p5_repair5g525_trace_logging_smoke_summary_v1`
- decision: `trace_logging_smoke_passed_continue_enriched_probe`
- contexts: `2`
- candidates: `5`
- probe_rows: `10`
- checkpoint_rows: `2`
- candidate_recognition: `{'rows': 10, 'recognized_rows': 10, 'fingerprint_rows': 10, 'candidate_recognized_all': True, 'updateparams_fingerprint_all': True}`
- required_trace_keys: `['blocked_reason_category', 'blocked_reason_vertex_conflict_count', 'blocked_reason_edge_swap_count', 'blocked_reason_priority_block_count', 'blocked_reason_backtrack_or_inheritance_count', 'blocked_reason_unknown_count', 'competing_neighbor_count', 'committed_neighbor_rank_by_base_distance', 'blocked_neighbor_rank_by_base_distance', 'wait_neighbor_rank_by_base_distance', 'goal_progress_neighbor_rank', 'rank_margin_top1_top2', 'rank_margin_committed_vs_best', 'rank_margin_blocked_vs_committed', 'pre_update_edge_c_channel_summary', 'pre_update_edge_f_channel_summary', 'pre_update_edge_cf_alignment_summary', 'local_decision_event_count', 'local_goal_progress_event_count', 'local_wait_nonprogress_event_count', 'local_blocked_progress_event_count']`
- gates: `{'probe_ran': True, 'contexts_le_2': True, 'budget_1000_only': True, 'selected_candidates_recognized': True, 'new_trace_keys_present': True, 'raw_log_sha256_verified': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`
- observed_ids_only: `True`
- ids_166_205_untouched: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`
