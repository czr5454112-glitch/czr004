# Phase5.5 Repair5G.5.15 V4 Context-Only Rich Feature Blocker

- decision: `v4_context_only_rich_feature_blocker_confirmed_continue_interactions`
- rich_feature_count: `19`
- context_only_rich_feature_count: `19`
- candidate_varying_feature_count: `30`
- candidate_varying_interaction_feature_count: `18`
- candidate_varying_rich_interaction_feature_count: `0`
- ranking_signal_blocker_confirmed: `True`
- runtime_claim_allowed: `false`

The recovered `feature_rich_*` values are constant across all 14 candidate rows inside the same context. A linear candidate scorer can use those context-only values to shift a nonstatic/fallback gate, but the same offset applies to every candidate in that context and therefore cannot provide candidate-ordering evidence by itself. G5.15 must add rich-context by candidate-parameter interaction features before using rich trace dynamics as ranking evidence.

## Rich Feature Inventory

- `feature_rich_committed_count`: constant_contexts `60/60`
- `feature_rich_blocked_count`: constant_contexts `60/60`
- `feature_rich_wait_event_count`: constant_contexts `60/60`
- `feature_rich_progress_committed_count`: constant_contexts `60/60`
- `feature_rich_nonprogress_committed_count`: constant_contexts `60/60`
- `feature_rich_blocked_per_committed`: constant_contexts `60/60`
- `feature_rich_wait_per_committed`: constant_contexts `60/60`
- `feature_rich_blocked_per_agent`: constant_contexts `60/60`
- `feature_rich_committed_per_agent`: constant_contexts `60/60`
- `feature_rich_progress_ratio`: constant_contexts `60/60`
- `feature_rich_c_update_count`: constant_contexts `60/60`
- `feature_rich_f_update_count`: constant_contexts `60/60`
- `feature_rich_c_nonzero_edges`: constant_contexts `60/60`
- `feature_rich_f_nonzero_edges`: constant_contexts `60/60`
- `feature_rich_c_flow_update_ratio`: constant_contexts `60/60`
- `feature_rich_cost_min`: constant_contexts `60/60`
- `feature_rich_cost_max`: constant_contexts `60/60`
- `feature_rich_cost_span`: constant_contexts `60/60`
- `feature_rich_cost_bounds_respected`: constant_contexts `60/60`
