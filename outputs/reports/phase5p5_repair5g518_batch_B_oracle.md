# Phase5.5 Repair5G.5.18 Batch B Oracle

- decision: `g518_batch_candidate_space_improved_continue_full_primary`
- integrity_decision: `g518_probe_batch_integrity_passed_continue_oracle`
- context_budget_pairs: `12`
- new_candidate_count: `10`
- new_candidate_win_count: `2`
- mean_new_oracle_gap_vs_old_oracle: `-0.002255253715999972`
- harmful_false_positive_target_contexts_improved: `1`
- missed_helpful_oracle_gap_reduced_contexts: `1`
- static_boundary_context_budget_rows_no_worse: `0`
- additive_weak_context_budget_rows: `8`
- gate_reasons: `{'new_candidate_win_count_ge_2': True, 'mean_new_oracle_gap_vs_old_oracle_le_neg_0p002': True, 'harmful_false_positive_target_contexts_improved_ge_1': True, 'missed_helpful_oracle_gap_reduced_ge_3': False}`

## Top New Candidates

- `repair5g518_grid_c1p20_b1p35_f1p00_w0p70_dc0p95_df1p00_beta0p60_max0p75_c0` (high_beta): wins `2`, mean_delta `0.004423527942459998`, dominated `False`
- `repair5g518_grid_c0p90_b1p40_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (block_heavy): wins `0`, mean_delta `-0.01707614496036`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p35_dc0p95_df1p00_beta0p30_max0p75_c0` (wait_conservative): wins `0`, mean_delta `-0.002734880774667778`, dominated `False`
- `repair5g518_grid_c0p90_b1p50_f1p00_w0p55_dc0p95_df1p00_beta0p35_max0p75_c0` (block_heavy): wins `0`, mean_delta `-0.0023160758098166668`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` (wait_conservative): wins `0`, mean_delta `-0.0016626281901622215`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p30_max0p75_c0` (wait_conservative): wins `0`, mean_delta `-0.0010033103992399997`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p88_df0p98_beta0p35_max0p75_c0` (flow_decay): wins `0`, mean_delta `0.0`, dominated `False`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p92_df0p88_beta0p35_max0p75_c0` (flow_decay): wins `0`, mean_delta `0.0`, dominated `False`

Negative `mean_new_oracle_gap_vs_old_oracle` means the expanded batch oracle improved over the old-14 oracle. No-gain batches are kept as evidence rather than hidden.
