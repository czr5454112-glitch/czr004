# Phase5.5 Repair5G.5.18 Adapter Grammar

- decision: `adapter_grammar_passed_continue_probe_batches`
- selected_g518_candidate_count: `30`
- smoke_candidate_count: `57`
- probe_rows: `57`
- invalid_names_rejected: `True`
- old_known_equivalent_fingerprints_exact: `True`
- gates: `{'source_contains_g518_parser': True, 'selected_candidates_static_parse': True, 'smoke_probe_ran': True, 'checkpoint_rows_gt_0': True, 'all_selected_g518_candidates_recognized': True, 'invalid_names_rejected': True, 'old_known_equivalent_fingerprints_exact': True, 'external_lacam2_solver_untouched': True, 'max_workers_eq_1': True}`

## Old Equivalent Checks

- `repair5g59_block_heavy_flow_guard` -> `repair5g518_grid_c1p00_b1p50_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_c_only_f_disabled` -> `repair5g518_grid_c1p25_b1p25_f0p00_w0p75_dc0p95_df1p00_beta0p00_max0p00_c1` exact=`True`
- `repair5g59_commit_heavy_flow_guard` -> `repair5g518_grid_c1p50_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_fast_decay_low_shield` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p90_df1p00_beta0p20_max0p50_c0` exact=`True`
- `repair5g59_flow_decay` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df0p95_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_high_beta_cap_safe` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df1p00_beta0p60_max0p75_c0` exact=`True`
- `repair5g59_light_cong_light_flow` -> `repair5g518_grid_c1p00_b1p00_f0p75_w0p75_dc0p98_df1p00_beta0p25_max0p50_c0` exact=`True`
- `repair5g59_low_beta_high_cap` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df1p00_beta0p20_max1p25_c0` exact=`True`
- `repair5g59_slow_decay_high_shield` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p98_df1p00_beta0p50_max1p00_c0` exact=`True`
- `repair5g59_static_abstain_candidate` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_static_flow_shield` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_wait_aggressive` -> `repair5g518_grid_c1p25_b1p25_f1p00_w1p00_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`
- `repair5g59_wait_conservative` -> `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0` exact=`True`

This check exercises only project-owned adapter recognition for bounded UpdateParams names. Unrecognized invalid names fall back to additive inside the diagnostic probe and are explicitly marked `candidate_recognized=false`.
