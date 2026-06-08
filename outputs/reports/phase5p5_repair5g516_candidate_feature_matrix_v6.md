# Phase5.5 Repair5G.5.16 Candidate Feature Matrix V6

- decision: `v6_error_bank_feature_matrix_passed_continue_ranker`
- rows: `840`
- contexts: `60`
- candidate_rows_per_context_min: `14`
- candidate_rows_per_context_max: `14`
- feature_count: `138`
- error_bank_feature_columns: `['feature_error_bank_harmful_fp_context', 'feature_error_bank_missed_helpful_context', 'feature_error_bank_static_boundary_context', 'feature_error_bank_high_uncertainty_context']`
- forbidden_feature_count: `0`
- gates: `{'rows_ge_840': True, 'forbidden_feature_count_eq_0': True, 'context_grouping_sane': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`

V6 is table-only because the targeted probe did not run. It adds error-bank annotations for harmful false positives, missed helpful fallbacks, static-boundary contexts, and high-uncertainty contexts. No oracle/probe/outcome fields are added as `feature_*` columns.
