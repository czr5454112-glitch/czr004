# Repair5G.5.26 Logging Patch V2 Static Verification

- schema_version: `phase5p5_repair5g526_logging_patch_v2_static_summary_v1`
- decision: `logging_patch_v2_noop_verified_continue_full_coverage_probe`
- requested_v2_audit_keys: `['exact_priority_block_subreason', 'all_failed_candidate_reasons_when_pibt_returns_false', 'failed_candidate_rank_histogram_when_pibt_returns_false', 'same_checkpoint_counterfactual_edge_label_manifest_or_proxy_status']`
- audit_key_status: `[{'audit_key': 'exact_priority_block_subreason', 'present_in_project_owned_logging': False, 'status': 'explicitly_unavailable_exact_v2_audit_not_in_current_logging', 'model_use': 'not_used_as_feature_when_exact_unavailable', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}, {'audit_key': 'all_failed_candidate_reasons_when_pibt_returns_false', 'present_in_project_owned_logging': False, 'status': 'explicitly_unavailable_exact_v2_audit_not_in_current_logging', 'model_use': 'not_used_as_feature_when_exact_unavailable', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}, {'audit_key': 'failed_candidate_rank_histogram_when_pibt_returns_false', 'present_in_project_owned_logging': False, 'status': 'explicitly_unavailable_exact_v2_audit_not_in_current_logging', 'model_use': 'not_used_as_feature_when_exact_unavailable', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}, {'audit_key': 'same_checkpoint_counterfactual_edge_label_manifest_or_proxy_status', 'present_in_project_owned_logging': False, 'status': 'explicitly_unavailable_exact_v2_audit_not_in_current_logging', 'model_use': 'not_used_as_feature_when_exact_unavailable', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}]`
- no_cpp_edit_needed: `True`
- exact_failed_candidate_audit_unavailable: `True`
- failed_candidate_audit_feature_status: `aggregate_proxy_only_until_exact_v2_audit_exists`
- logging_patch_hash: `1af7c0753448071f2761ef9ab7c83b883326de50e78825626582da559eef02a4`
- external_lacam2_solver_status: ``
- gates: `{'project_owned_logging_files_touched_only': True, 'external_lacam2_untouched': True, 'candidate_parser_fingerprints_unchanged': True, 'old14_g518_g522_candidate_fingerprints_unchanged': True, 'trace_event_sequence_preserved_for_committed_and_blocked_events': True, 'legacy_g525_trace_fields_unchanged': True, 'new_audit_keys_present_or_explicitly_unavailable': True}`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`
