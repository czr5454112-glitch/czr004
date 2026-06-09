# Phase5.5 Repair5G.5.18 Batch C Oracle

- decision: `g518_batch_candidate_space_improved_continue_full_primary`
- integrity_decision: `g518_probe_batch_integrity_passed_continue_oracle`
- context_budget_pairs: `12`
- new_candidate_count: `8`
- new_candidate_win_count: `2`
- mean_new_oracle_gap_vs_old_oracle: `-0.0013326499239999733`
- harmful_false_positive_target_contexts_improved: `1`
- missed_helpful_oracle_gap_reduced_contexts: `1`
- static_boundary_context_budget_rows_no_worse: `0`
- additive_weak_context_budget_rows: `8`
- gate_reasons: `{'new_candidate_win_count_ge_2': True, 'mean_new_oracle_gap_vs_old_oracle_le_neg_0p002': False, 'harmful_false_positive_target_contexts_improved_ge_1': True, 'missed_helpful_oracle_gap_reduced_ge_3': False}`

## Top New Candidates

- `repair5g518_grid_c1p20_b1p15_f1p00_w0p70_dc0p95_df1p00_beta0p55_max0p75_c0` (high_beta): wins `2`, mean_delta `-0.009021627875316001`, dominated `False`
- `repair5g518_grid_c1p20_b1p15_f1p00_w0p70_dc0p95_df1p00_beta0p60_max0p75_c0` (high_beta): wins `0`, mean_delta `-0.0027720174380839995`, dominated `False`
- `repair5g518_grid_c1p20_b1p35_f1p00_w0p70_dc0p95_df1p00_beta0p55_max0p75_c0` (high_beta): wins `0`, mean_delta `0.001390913321216`, dominated `False`
- `repair5g518_grid_c1p35_b1p35_f1p00_w0p80_dc0p95_df1p00_beta0p25_max0p75_c0` (static_boundary): wins `0`, mean_delta `0.0088116158259726`, dominated `False`
- `repair5g518_grid_c1p35_b1p15_f1p00_w0p80_dc0p95_df1p00_beta0p25_max0p90_c0` (static_boundary): wins `0`, mean_delta `0.012271456073737998`, dominated `True`
- `repair5g518_grid_c1p20_b1p15_f1p00_w0p80_dc0p95_df1p00_beta0p25_max0p75_c0` (static_boundary): wins `0`, mean_delta `0.028184095763057998`, dominated `True`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p60_dc0p95_df1p00_beta0p20_max1p00_c0` (low_beta_high_cap): wins `0`, mean_delta `0.056587644222`, dominated `True`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p60_dc0p95_df1p00_beta0p25_max1p00_c0` (low_beta_high_cap): wins `0`, mean_delta `0.12167739853377998`, dominated `True`

Negative `mean_new_oracle_gap_vs_old_oracle` means the expanded batch oracle improved over the old-14 oracle. No-gain batches are kept as evidence rather than hidden.
