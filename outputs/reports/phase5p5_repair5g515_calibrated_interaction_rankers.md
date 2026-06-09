# Phase5.5 Repair5G.5.15 Calibrated Interaction Ranker Evaluation

- decision: `interaction_ranker_no_better_than_v4_continue_feature_design`
- primary_policy_name: `pairwise_context_ranker`
- primary_policy: `{'row_type': 'policy_summary', 'policy': 'pairwise_context_ranker', 'contexts': 60, 'mean_delta_vs_static': -0.009366233488, 'mean_delta_vs_additive': -0.0971447799156667, 'harmful_vs_static_rate': 0.03333333333333333, 'coverage': 0.23333333333333334, 'fallback_rate': 0.7666666666666666, 'regret_to_oracle': 0.0257312020885, 'risk_adjusted_utility_lambda_0p05': -0.007699566821333333, 'risk_adjusted_utility_lambda_0p1': -0.006032900154666666, 'risk_adjusted_utility_lambda_0p10': -0.006032900154666666, 'risk_adjusted_utility_lambda_0p2': -0.0026995668213333325, 'risk_adjusted_utility_lambda_0p20': -0.0026995668213333325}`
- oof_contexts: `60`
- fixed_dev_contexts: `30`
- forbidden_feature_count: `0`
- gates: `{'harmful_vs_static_rate_le_0p05': True, 'harmful_vs_static_rate_le_0p033': True, 'risk_adjusted_improves_over_v3_lambda_0p05': True, 'risk_adjusted_improves_over_v3_lambda_0p10': True, 'risk_adjusted_improves_over_v4_lambda_0p05': True, 'risk_adjusted_improves_over_v4_lambda_0p10': False, 'risk_adjusted_beats_safe_slow_decay_train_gate': True, 'risk_adjusted_beats_safe_train_only_map_agent_gate': True, 'beats_rich_interactions_shuffled_control': True, 'forbidden_feature_count_eq_0': True, 'no_ids_166_205': True, 'runtime_claim_allowed_false': True}`
- leave_one_seed_out_oof: `reported for seeds 146..155`
- fixed_151_155_dev: `reported as diagnostic`
- bootstrap_confidence_intervals: `reported`
- calibration_buckets: `reported`
- per_seed_and_map_agent_harmful_counts: `reported`
- runtime_claim_allowed: `false`

## OOF Policy Summaries

- `two_stage_safety_ranker`: mean_delta_vs_static=-0.004507, harmful_rate=0.033, coverage=0.133, rau_0.10=-0.001173
- `pairwise_context_ranker`: mean_delta_vs_static=-0.009366, harmful_rate=0.033, coverage=0.233, rau_0.10=-0.006033
- `v3_g512_ranker_reproduced`: mean_delta_vs_static=-0.007022, harmful_rate=0.017, coverage=0.150, rau_0.10=-0.005355
- `v4_g514_ranker_reproduced`: mean_delta_vs_static=-0.008232, harmful_rate=0.017, coverage=0.233, rau_0.10=-0.006565
- `no_rich_feature_ablation`: mean_delta_vs_static=-0.007022, harmful_rate=0.017, coverage=0.150, rau_0.10=-0.005355
- `no_rich_interaction_ablation`: mean_delta_vs_static=-0.007856, harmful_rate=0.017, coverage=0.217, rau_0.10=-0.006189
- `context_only_rich_ablation`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `rich_interactions_shuffled_within_train_split`: mean_delta_vs_static=-0.003878, harmful_rate=0.033, coverage=0.150, rau_0.10=-0.000545
- `candidate_param_only_ranker`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `map_agent_only_gate`: mean_delta_vs_static=0.000408, harmful_rate=0.033, coverage=0.033, rau_0.10=0.003741
- `safe_slow_decay_train_gate`: mean_delta_vs_static=0.000206, harmful_rate=0.017, coverage=0.017, rau_0.10=0.001872
- `safe_train_only_map_agent_gate`: mean_delta_vs_static=0.000408, harmful_rate=0.033, coverage=0.033, rau_0.10=0.003741
- `fixed_slow_decay_high_shield`: mean_delta_vs_static=-0.008626, harmful_rate=0.367, coverage=1.000, rau_0.10=0.028041
- `random_candidate`: mean_delta_vs_static=0.018244, harmful_rate=0.467, coverage=0.900, rau_0.10=0.064911
- `true_random_feature_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `true_shuffled_label_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `oracle_upper_bound`: mean_delta_vs_static=-0.035097, harmful_rate=0.000, coverage=1.000, rau_0.10=-0.035097

All learned thresholds are selected only on each fold-train split before evaluating the held-out seed. This remains a table-only offline diagnostic; no runtime policy is validated or exported.
