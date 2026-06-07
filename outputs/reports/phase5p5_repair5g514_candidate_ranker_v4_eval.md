# Phase5.5 Repair5G.5.14 Candidate Ranker V4 Eval

- decision: `rich_trace_features_insufficient_continue_probe_or_lattice`
- dev_contexts: `30`
- primary_policy: `{'row_type': 'policy_summary', 'policy': 'v4_ranker', 'contexts': 30, 'mean_delta_vs_static': -0.010721312411, 'mean_delta_vs_additive': -0.10014120805633332, 'harmful_vs_static_rate': 0.06666666666666667, 'coverage': 0.26666666666666666, 'fallback_rate': 0.7333333333333334, 'regret_to_oracle': 0.027213019698333337, 'risk_adjusted_utility_lambda_0p05': -0.007387979077666666, 'risk_adjusted_utility_lambda_0p1': -0.004054645744333333, 'risk_adjusted_utility_lambda_0p2': 0.0026120209223333343}`
- gates: `{'mean_delta_vs_static_lt_0': True, 'mean_delta_vs_additive_lt_0': True, 'harmful_vs_static_rate_le_0p05': False, 'risk_adjusted_improves_over_v3_g512': False, 'risk_adjusted_beats_safe_slow_decay_train_gate': True, 'risk_adjusted_beats_safe_train_only_map_agent_gate': True, 'beats_candidate_param_only_ranker': True, 'beats_no_rich_feature_ablation': True, 'beats_true_random_feature_model': True, 'beats_true_shuffled_label_model': True, 'forbidden_feature_count_eq_0': True, 'no_ids_166_205': True, 'runtime_claim_allowed_false': True}`
- risk_lambdas: `[0.05, 0.1, 0.2]`
- bootstrap_confidence_intervals: `reported`
- runtime_claim_allowed: `false`

## Policy Summaries

- `v4_ranker`: mean_delta_vs_static=-0.010721, harmful_rate=0.067, coverage=0.267, rau_0.10=-0.004055
- `v3_g512_ranker_reproduced`: mean_delta_vs_static=-0.010423, harmful_rate=0.033, coverage=0.200, rau_0.10=-0.007090
- `static_flow_shield`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `additive_ltm`: mean_delta_vs_static=0.089420, harmful_rate=0.933, coverage=1.000, rau_0.10=0.182753
- `slow_decay_high_shield_fixed`: mean_delta_vs_static=-0.008032, harmful_rate=0.433, coverage=1.000, rau_0.10=0.035301
- `safe_slow_decay_train_gate`: mean_delta_vs_static=-0.007964, harmful_rate=0.033, coverage=0.167, rau_0.10=-0.004631
- `safe_train_only_map_agent_gate`: mean_delta_vs_static=-0.013731, harmful_rate=0.233, coverage=0.667, rau_0.10=0.009603
- `map_agent_only_gate`: mean_delta_vs_static=-0.013731, harmful_rate=0.233, coverage=0.667, rau_0.10=0.009603
- `candidate_param_only_ranker`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `candidate_only_mean_delta_prior`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `no_rich_feature_ablation`: mean_delta_vs_static=-0.010423, harmful_rate=0.033, coverage=0.200, rau_0.10=-0.007090
- `rich_only_ranker`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `rich_shuffled_within_train_split_control`: mean_delta_vs_static=-0.011102, harmful_rate=0.067, coverage=0.267, rau_0.10=-0.004435
- `true_random_feature_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `true_shuffled_label_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, rau_0.10=0.000000
- `random_candidate`: mean_delta_vs_static=0.020152, harmful_rate=0.467, coverage=0.967, rau_0.10=0.066818
- `oracle_upper_bound`: mean_delta_vs_static=-0.037934, harmful_rate=0.000, coverage=1.000, rau_0.10=-0.037934

All policies are evaluated as grouped context decisions over the 14 candidate UpdateLTM parameter rows. The v4 success decision is only available if risk-adjusted utility improves over the reproduced G5.12/G5.13 ranker and beats the safe train-only hard controls while keeping harmful rate at or below 0.05.
