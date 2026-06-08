# Repair5G.5.21 Avoidable Failure Semantics

- decision: `avoidable_failure_semantics_passed_continue_second_wave_pool`
- primary_pair_rows: `1320`
- budget_rows: `2640`
- static_solution_quality_harmful_count: `0`
- static_candidate_induced_no_solution_count: `0`
- candidate_induced_no_solution_primary_rows: `28`
- candidate_recovers_static_no_solution_primary_rows: `58`
- unavoidable_context_failure_primary_rows: `308`
- budget_sensitive_candidate_failure_rows: `45`
- gates: `{'target_contexts_eq_60': True, 'candidate_rows_per_context_eq_22': True, 'primary_pair_rows_eq_1320': True, 'budget_rows_eq_2640': True, 'static_solution_quality_harmful_count_eq_0': True, 'static_candidate_induced_no_solution_count_eq_0': True}`

Rows include both `budget` scopes and `primary_pair` scopes. Policy risk should prioritize candidate-induced failures and finite-pair solution-quality harm, not unavoidable context failure or candidate failure that matches static failure.
