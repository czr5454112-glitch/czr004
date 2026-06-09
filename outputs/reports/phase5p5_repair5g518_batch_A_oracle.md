# Phase5.5 Repair5G.5.18 Batch A Oracle

- decision: `g518_batch_candidate_space_improved_continue_full_primary`
- integrity_decision: `g518_probe_batch_integrity_passed_continue_oracle`
- context_budget_pairs: `12`
- new_candidate_count: `12`
- new_candidate_win_count: `4`
- mean_new_oracle_gap_vs_old_oracle: `-0.00020502306599996524`
- harmful_false_positive_target_contexts_improved: `0`
- missed_helpful_oracle_gap_reduced_contexts: `0`
- static_boundary_context_budget_rows_no_worse: `0`
- additive_weak_context_budget_rows: `8`
- gate_reasons: `{'new_candidate_win_count_ge_2': True, 'mean_new_oracle_gap_vs_old_oracle_le_neg_0p002': False, 'harmful_false_positive_target_contexts_improved_ge_1': False, 'missed_helpful_oracle_gap_reduced_ge_3': False}`

## Top New Candidates

- `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0` (block_heavy): wins `2`, mean_delta `-0.0194627930029175`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0` (wait_conservative): wins `2`, mean_delta `-0.006214140094348`, dominated `False`
- `repair5g518_grid_c0p90_b1p65_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (block_heavy): wins `0`, mean_delta `-0.00251497626535`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p45_dc0p95_df1p00_beta0p30_max0p75_c0` (wait_conservative): wins `0`, mean_delta `-0.0015765032953108892`, dominated `False`
- `repair5g518_grid_c1p20_b1p55_f1p00_w0p70_dc0p95_df1p00_beta0p55_max0p75_c0` (high_beta): wins `0`, mean_delta `-0.0004886217315039994`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p90_df0p92_beta0p35_max0p75_c0` (flow_decay): wins `0`, mean_delta `0.0`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p92_df0p98_beta0p35_max0p75_c0` (flow_decay): wins `0`, mean_delta `0.0`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df0p88_beta0p35_max0p75_c0` (flow_decay): wins `0`, mean_delta `0.0`, dominated `False`

Negative `mean_new_oracle_gap_vs_old_oracle` means the expanded batch oracle improved over the old-14 oracle. No-gain batches are kept as evidence rather than hidden.
