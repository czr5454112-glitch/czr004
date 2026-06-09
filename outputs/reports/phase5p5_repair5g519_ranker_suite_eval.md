# Phase5.5 Repair5G.5.19 Ranker Suite Evaluation

- decision: `ranker_ignores_new_candidates_continue_candidate_policy_design`
- best_policy: `no_new_candidate_ablation`
- best_mean_delta_vs_static: `-0.000462512171`
- best_mean_delta_vs_additive: `-0.100924657693`
- best_harmful_vs_static_rate: `0.333333333333`
- best_new_candidate_selection_count: `0`
- best_new_candidate_helpful_selection_count: `0`
- best_new_candidate_harmful_selection_count: `0`
- forbidden_feature_count: `0`
- runtime_claim_allowed: `false`

Hard gates: `{'mean_delta_vs_static_lt_0': True, 'mean_delta_vs_additive_lt_0': True, 'harmful_vs_static_rate_le_0p05': False, 'harmful_vs_static_rate_prefer_le_0p0333333333': False, 'rau_0p05_improves_over_reproduced': True, 'rau_0p10_improves_over_reproduced': True, 'beats_train_only_map_agent_prior_0p10': True, 'beats_best_single_train_candidate_0p10_or_reports_fixed_better': True, 'beats_old14_only_ranker_0p10': False, 'beats_no_new_candidate_ablation_0p10': False, 'selects_at_least_one_new_candidate_oof': False, 'new_candidate_selection_harmful_rate_le_0p05': True, 'new_candidate_selection_helpful_count_gt_0': False, 'oracle_new22_regret_lt_old14_only_regret': False, 'false_positive_count_le_static_baseline': True}`

Evaluation is grouped by context: every policy scores or chooses among the 22 candidate rows for a context and then emits one selected candidate or static fallback. Seed OOF, fixed train/dev, leave-one-map-agent, leave-one-map-family, bootstrap, calibration, per-group, and per-candidate summaries are written to the required CSV/JSON artifacts.
