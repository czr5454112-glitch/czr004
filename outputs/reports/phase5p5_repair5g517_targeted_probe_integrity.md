# Phase5.5 Repair5G.5.17 Targeted Probe Integrity

- decision: `targeted_probe_integrity_passed_continue_oracle`
- probe_ran: `True`
- probe_rows: `960`
- expected_rows: `960`
- target_contexts: `20`
- measured_contexts: `20`
- candidate_count: `24`
- repair_candidate_count: `10`
- duplicate_context_candidate_budget_rows: `0`
- candidate_recognized_all: `True`
- ids_166_205_untouched: `True`
- observed_ids_only: `True`
- gates: `{'probe_ran': True, 'rows_eq_960': True, 'contexts_eq_target_count': True, 'candidates_eq_24': True, 'repair_candidates_eq_10': True, 'budgets_eq_1000_2000': True, 'candidate_recognized_all': True, 'repair_candidate_recognized_all': True, 'duplicate_context_candidate_budget_rows_eq_0': True, 'ids_166_205_untouched': True, 'observed_ids_only': True, 'max_workers_eq_1': True, 'external_lacam2_solver_untouched': True}`

The probe is local, sequential, and writes isolated G5.17 output paths. These rows are candidate-space diagnostics only; runtime-policy, Phase5.5, Phase6, and AAAI claims remain closed.
