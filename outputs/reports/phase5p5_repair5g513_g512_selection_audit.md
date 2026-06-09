# Phase5.5 Repair5G.5.13 G5.12 Selection Audit

- decision: `g512_selection_audit_completed`
- dev_contexts: `30`
- selected_candidate_distribution: `{'repair5g59_slow_decay_high_shield': 6, 'repair5g59_static_flow_shield': 24}`
- selected_nonstatic_candidate_distribution: `{'repair5g59_slow_decay_high_shield': 6}`
- oracle_capture_count: `5`
- oracle_capture_rate: `0.16666666666666666`
- regret_to_oracle_mean: `0.027511037073000004`
- missed_helpful_contexts: `20`
- harmful_selected_contexts: `1`
- broad_multi_candidate_selector: `False`
- mostly_safe_gated_slow_decay_high_shield: `True`
- runtime_claim_allowed: `false`

This audit is context grouped. G5.12 selects a candidate in a dev context only after scoring all 14 candidates, otherwise it falls back to static flow-shield. The output table lists oracle captures, regret to oracle, missed helpful fallbacks, and harmful selected contexts for each dev context.
