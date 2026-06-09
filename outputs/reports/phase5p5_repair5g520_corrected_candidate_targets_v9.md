# Phase5.5 Repair5G.5.20 Corrected Candidate Targets V9

- decision: `corrected_targets_v9_passed_continue_opportunity_features`
- target_rows: `1320`
- contexts: `60`
- candidate_rows_per_context_min: `22`
- candidate_rows_per_context_max: `22`
- new_opportunity_contexts: `16`
- new_opportunity_candidate_rows: `16`
- safe_new_candidate_positive_rows: `160`
- solution_quality_harmful_rows: `340`
- no_solution_or_nonfinite_rows: `483`
- runtime_claim_allowed: `false`

V9 preserves one row per context and candidate while separating solution-quality harm from no-solution or nonfinite risk. New-candidate opportunity labels are target columns, not runtime feature columns.
