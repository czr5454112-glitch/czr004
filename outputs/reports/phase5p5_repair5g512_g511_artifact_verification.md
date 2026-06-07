# Phase5.5 Repair5G.5.12 G5.11 Artifact Verification

- decision: `g511_artifacts_verified_continue_g512`
- results_rows: `3360`
- candidate_count: `14`
- contexts: `60`
- primary_rows: `1680`
- primary_contexts: `60`
- duplicate_context_candidate_budget_rows: `0`
- missing: `[]`
- parse_errors: `{}`
- gates: `{'full_lattice_results_exist': True, 'candidate_lattice_exists': True, 'oracle_by_context_exists': True, 'confidence_targets_v5_exists': True, 'summary_json_files_parse': True, 'contexts_eq_60': True, 'candidate_count_eq_14': True, 'full_rows_3360_or_documented_equivalent': True, 'primary_1000_2000_rows_available': True, 'primary_1000_2000_contexts_eq_60': True, 'observed_ids_only': True, 'ids_166_205_untouched': True, 'duplicate_context_candidate_budget_rows_eq_0': True}`

The verifier only checks tracked G5.11 artifacts and the observed-ID boundary. It does not run the solver and keeps runtime, Phase5.5, Phase6, and AAAI claims closed.
