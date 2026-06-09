# Phase5.5 Repair5G.5.14 Rich Context Features

- decision: `existing_checkpoint_rich_features_recovered_continue_v4_matrix`
- artifact_search_decision: `existing_rich_checkpoint_artifacts_found_parse_without_solver`
- target_contexts: `60`
- rich_contexts: `60`
- missing_rich_contexts: `0`
- rich_feature_count: `19`
- source_complete: `True`
- feature_source_distribution: `{'existing_checkpoint': 60}`
- local_solver_probe_run: `false`
- runtime_claim_allowed: `false`

The parser expands only the allowed pre-choice `feature_names` / `feature_values` fields from existing checkpoint JSONL rows. It does not use trace event identities, vertex IDs, probe outcomes, oracle scores, final solver outcomes, actions, priorities, restarts, h-values, or candidate deletion features.
