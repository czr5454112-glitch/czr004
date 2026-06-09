# Repair5G.5.25 Logging Patch Static Verification

- schema_version: `phase5p5_repair5g525_logging_patch_static_summary_v1`
- decision: `logging_patch_static_verified_continue_smoke`
- mapping: `{'vertex_conflict': 'occupied_next candidate already reserved', 'edge_swap': 'candidate would swap with an already planned agent', 'backtrack_or_inheritance': 'recursive PIBT priority inheritance failed', 'priority_block': 'reserved for future exact priority blocker logs', 'unknown': 'legacy/default blocked event without exact cause'}`
- logging_patch_hash: `1af7c0753448071f2761ef9ab7c83b883326de50e78825626582da559eef02a4`
- gates: `{'project_owned_logging_files_touched': True, 'required_tokens_present': True, 'trace_event_sequence_preserved': True, 'external_lacam2_solver_untouched': True, 'parser_fingerprints_written': True, 'logging_patch_hash_present': True}`
- external_lacam2_solver_status: ``
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`
