# Phase5.5 Repair5G.5.19 Candidate-Space Analysis

- decision: `candidate_space_analysis_completed_continue_feature_matrix_v8`
- new_candidate_win_count: `32`
- new_candidate_win_contexts: `16`
- old14_vs_new22_oracle_gap_mean: `-0.002209805308`
- additive_weak_context_budget_rows: `80`
- static_boundary_context_budget_rows: `4`
- harmful_false_positive_target_cases: `798`
- missed_helpful_cases: `38`
- best_new_by_mean_delta: `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0`
- best_new_by_oracle_wins: `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0`
- best_new_by_risk_adjusted: `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0`
- runtime_claim_allowed: `false`

## Top Candidates

- `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0` source=`g518_new` mean_delta=`-0.017102742108` oracle_wins=`3` harmful_rate=`0.516666666667`
- `repair5g59_block_heavy_flow_guard` source=`old14` mean_delta=`-0.012147644457` oracle_wins=`4` harmful_rate=`0.55`
- `repair5g518_grid_c1p20_b1p15_f1p00_w0p70_dc0p95_df1p00_beta0p55_max0p75_c0` source=`g518_new` mean_delta=`-0.010922706541` oracle_wins=`1` harmful_rate=`0.566666666667`
- `repair5g59_high_beta_cap_safe` source=`old14` mean_delta=`-0.009081672743` oracle_wins=`2` harmful_rate=`0.533333333333`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0` source=`g518_new` mean_delta=`-0.008971056177` oracle_wins=`4` harmful_rate=`0.55`
- `repair5g59_wait_conservative` source=`old14` mean_delta=`-0.008971056177` oracle_wins=`0` harmful_rate=`0.55`
- `repair5g518_grid_c0p90_b1p40_f1p00_w0p45_dc0p95_df1p00_beta0p35_max0p75_c0` source=`g518_new` mean_delta=`-0.008820056383` oracle_wins=`1` harmful_rate=`0.566666666667`
- `repair5g59_wait_aggressive` source=`old14` mean_delta=`-0.008685861192` oracle_wins=`2` harmful_rate=`0.583333333333`
- `repair5g518_grid_c1p25_b1p25_f1p00_w0p35_dc0p95_df1p00_beta0p30_max0p75_c0` source=`g518_new` mean_delta=`-0.00770182878` oracle_wins=`2` harmful_rate=`0.6`
- `repair5g518_grid_c1p20_b1p15_f1p00_w0p70_dc0p95_df1p00_beta0p60_max0p75_c0` source=`g518_new` mean_delta=`-0.007258037876` oracle_wins=`1` harmful_rate=`0.583333333333`

G5.18 candidate-space evidence survives reconstruction if new candidates win budget pairs and the new22 oracle remains below the old14 oracle. This report is still oracle/candidate-space evidence, not runtime policy evidence.
