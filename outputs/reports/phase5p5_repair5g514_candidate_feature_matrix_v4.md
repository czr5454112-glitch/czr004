# Phase5.5 Repair5G.5.14 Candidate Feature Matrix V4

- decision: `candidate_feature_matrix_v4_created_continue_ranker`
- candidate_rows: `840`
- contexts: `60`
- candidates: `14`
- feature_count: `61`
- rich_feature_count: `19`
- rich_contexts: `60`
- forbidden_feature_count: `0`
- gates: `{'candidate_rows_ge_840': True, 'contexts_eq_60': True, 'candidates_eq_14': True, 'rich_feature_count_gt_0': True, 'rich_contexts_ge_60_if_source_complete': True, 'forbidden_feature_count_eq_0': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`
- runtime_claim_allowed: `false`

V4 is a strict join of G5.12 candidate rows with recovered rich context aggregates. No outcome, oracle, action, priority, restart, h-value, or candidate-deletion feature is added.
