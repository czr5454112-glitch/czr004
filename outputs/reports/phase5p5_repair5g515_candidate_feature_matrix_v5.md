# Phase5.5 Repair5G.5.15 Candidate Feature Matrix V5

- decision: `v5_interaction_feature_matrix_passed_continue_ranker`
- candidate_rows: `840`
- contexts: `60`
- candidates: `14`
- feature_count: `134`
- rich_interaction_feature_count: `13`
- within_context_centered_feature_count: `13`
- train_only_zscore_feature_count: `30`
- log1p_count_feature_count: `9`
- capped_ratio_feature_count: `8`
- ranking_feature_count: `69`
- context_only_gate_feature_count: `65`
- candidate_varying_interaction_feature_count: `39`
- forbidden_feature_count: `0`
- gates: `{'rows_eq_840': True, 'contexts_eq_60': True, 'candidates_eq_14': True, 'rich_interaction_feature_count_gt_0': True, 'within_context_centered_feature_count_gt_0': True, 'forbidden_feature_count_eq_0': True, 'observed_ids_only': True, 'ids_166_205_untouched': True, 'grouped_14_candidate_rows_per_context': True}`
- runtime_claim_allowed: `false`

V5 keeps the G5.14 rows fixed and adds only runtime-safe rich trace by candidate-parameter interaction features, log/capped rich transforms, train-only z-score features, and within-context centered interaction features. No outcome, oracle, score, target, action, priority, restart, h-value, or candidate-deletion feature is added.
