# Phase5.5 Repair5G.5.20 Opportunity-Gated Policy Evaluation

- decision: `opportunity_gated_policy_eval_completed`
- best_policy: `no_new_candidate_ablation`
- best_mean_solution_quality_delta_vs_static: `-0.000948564581`
- best_solution_quality_harmful_rate: `0.0`
- best_no_solution_rate: `0.383333333333`
- best_total_harmful_rate: `0.383333333333`
- best_new_candidate_selection_count: `0`
- best_new_candidate_helpful_selection_count: `0`
- best_new_candidate_harmful_selection_count: `0`
- best_new_candidate_opportunity_capture_rate: `0.0`
- forbidden_feature_count: `0`
- runtime_claim_allowed: `false`

Hard gates: `{'new_candidate_selection_count_gt_0': False, 'new_candidate_helpful_selection_count_gt_0': False, 'new_candidate_harmful_selection_count_le_0': True, 'solution_quality_harmful_rate_le_old14_no_new_baseline': True, 'rau_0p10_beats_old14_only': True, 'rau_0p10_beats_no_new_ablation': False, 'oracle_regret_vs_new22_improves_over_old14_only': True, 'calibration_buckets_reported': True, 'forbidden_feature_count_eq_0': True, 'runtime_claim_allowed_false': True}`

The evaluator uses corrected labels and reports solution-quality harm, no-solution risk, total harmful risk, new-candidate opportunity capture, oracle regret, calibration buckets, bootstrap confidence intervals, and map/family diagnostics separately.
