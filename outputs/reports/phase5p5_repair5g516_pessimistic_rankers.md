# Phase5.5 Repair5G.5.16 Pessimistic Ranker Evaluation

- decision: `pessimistic_ranker_too_conservative_continue_lattice_or_data`
- primary_policy_name: `balanced_bound`
- primary_policy: `{'row_type': 'policy_summary', 'policy': 'balanced_bound', 'contexts': 60, 'mean_delta_vs_static': 0.0, 'mean_delta_vs_additive': -0.08777854642766672, 'harmful_vs_static_rate': 0.0, 'coverage': 0.0, 'fallback_rate': 1.0, 'regret_to_oracle': 0.03509743557649999, 'risk_adjusted_utility_lambda_0p05': 0.0, 'risk_adjusted_utility_lambda_0p1': 0.0, 'risk_adjusted_utility_lambda_0p10': 0.0, 'risk_adjusted_utility_lambda_0p2': 0.0, 'risk_adjusted_utility_lambda_0p20': 0.0, 'false_positive_count': 0, 'missed_helpful_count': 52, 'static_near_oracle_contexts': 8, 'static_near_oracle_nonstatic_selected': 0}`
- forbidden_feature_count: `0`
- gates: `{'harmful_vs_static_rate_le_0p033': True, 'rau_0p05_beats_g515_primary': False, 'rau_0p10_beats_g515_primary': False, 'rau_0p10_beats_reproduced_v4': False, 'beats_safe_slow_decay_train_gate': True, 'beats_safe_train_only_map_agent_gate': True, 'beats_rich_interactions_shuffled_control': False, 'false_positive_count_le_g515': True, 'missed_helpful_count_reduced_vs_g515': False, 'forbidden_feature_count_eq_0': True, 'no_ids_166_205': True, 'runtime_claim_allowed_false': True}`
- seed_oof_146_155: `reported`
- leave_one_map_agent_group_out: `reported`
- fixed_train_146_150_dev_151_155: `reported`
- original_bank_vs_targeted_bank: `not_applicable_no_targeted_probe`
- runtime_claim_allowed: `false`

## OOF Policy Summaries

- `ultra_safe_bound`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `balanced_bound`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `opportunity_diagnostic_not_for_promotion`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `no_error_bank_feature_ablation`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `no_pessimistic_bound_ablation`: mean_delta_vs_static=-0.002749, harmful_rate=0.033, coverage=0.150, rau_0.10=0.000585, fp=2, missed=43
- `static_flow_shield`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `additive_ltm`: mean_delta_vs_static=0.087779, harmful_rate=0.950, coverage=1.000, rau_0.10=0.182779, fp=57, missed=0
- `v3_g512_ranker_reproduced`: mean_delta_vs_static=-0.007022, harmful_rate=0.017, coverage=0.150, rau_0.10=-0.005355, fp=1, missed=43
- `v4_g514_ranker_reproduced`: mean_delta_vs_static=-0.008232, harmful_rate=0.017, coverage=0.233, rau_0.10=-0.006565, fp=1, missed=39
- `g515_pairwise_context_ranker`: mean_delta_vs_static=-0.009366, harmful_rate=0.033, coverage=0.233, rau_0.10=-0.006033, fp=2, missed=39
- `g515_two_stage_safety_ranker`: mean_delta_vs_static=-0.004507, harmful_rate=0.033, coverage=0.133, rau_0.10=-0.001173, fp=2, missed=45
- `safe_slow_decay_train_gate`: mean_delta_vs_static=0.000206, harmful_rate=0.017, coverage=0.017, rau_0.10=0.001872, fp=1, missed=51
- `safe_train_only_map_agent_gate`: mean_delta_vs_static=0.000408, harmful_rate=0.033, coverage=0.033, rau_0.10=0.003741, fp=2, missed=51
- `map_agent_only_gate`: mean_delta_vs_static=0.000408, harmful_rate=0.033, coverage=0.033, rau_0.10=0.003741, fp=2, missed=51
- `fixed_slow_decay_high_shield`: mean_delta_vs_static=-0.008626, harmful_rate=0.367, coverage=1.000, rau_0.10=0.028041, fp=22, missed=0
- `candidate_param_only_ranker`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `rich_interactions_shuffled_control`: mean_delta_vs_static=-0.003878, harmful_rate=0.033, coverage=0.150, rau_0.10=-0.000545, fp=2, missed=44
- `random_feature_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `shuffled_label_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000, fp=0, missed=52
- `oracle_upper_bound`: mean_delta_vs_static=-0.035097, harmful_rate=0.000, coverage=1.000, rau_0.10=-0.035097, fp=0, missed=0
