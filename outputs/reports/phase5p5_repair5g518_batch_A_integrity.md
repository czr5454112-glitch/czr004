# Phase5.5 Repair5G.5.18 Batch A Probe Integrity

- decision: `g518_probe_batch_integrity_passed_continue_oracle`
- probe_rows: `312`
- expected_rows: `312`
- target_contexts: `6`
- old14_control_count: `14`
- new_candidate_count: `12`
- duplicate_context_candidate_budget_rows: `0`
- candidate_recognized_all: `True`
- gates: `{'probe_ran': True, 'rows_eq_expected': True, 'contexts_eq_planned': True, 'candidate_count_eq_planned': True, 'old14_controls_eq_14': True, 'new_candidates_lte_48': True, 'target_contexts_lte_24': True, 'budgets_eq_1000_2000': True, 'candidate_recognized_all': True, 'duplicate_context_candidate_budget_rows_eq_0': True, 'ids_166_205_untouched': True, 'observed_ids_only': True, 'external_lacam2_solver_untouched': True, 'max_workers_eq_1': True}`

The batch is local, sequential, and writes isolated G5.18 output paths. These rows are candidate-space diagnostics only.
