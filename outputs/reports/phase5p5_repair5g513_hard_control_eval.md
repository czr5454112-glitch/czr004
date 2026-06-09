# Phase5.5 Repair5G.5.13 Hard-Control Eval

- decision: `candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features`
- dev_contexts: `30`
- primary_policy: `{'row_type': 'policy_summary', 'policy': 'g512_ranker', 'contexts': 30, 'mean_delta_vs_static': -0.010423295036333333, 'mean_delta_vs_additive': -0.09984319068166667, 'harmful_vs_static_rate': 0.03333333333333333, 'coverage': 0.2, 'fallback_rate': 0.8, 'regret_to_oracle': 0.027511037073000004}`
- gates: `{'mean_delta_vs_static_lt_0': True, 'mean_delta_vs_additive_lt_0': True, 'harmful_vs_static_rate_le_0p05': True, 'beats_safe_slow_decay_train_gate': True, 'beats_safe_train_only_map_agent_gate': False, 'beats_candidate_param_only_ranker': True, 'beats_candidate_only_mean_delta_prior': True, 'beats_map_agent_only_gate': False, 'beats_true_random_feature_model': True, 'beats_true_shuffled_label_model': True, 'forbidden_feature_count_eq_0': True, 'no_ids_166_205': True, 'runtime_claim_allowed_false': True}`
- safe_slow_decay_train_gate_choices: `{'maze-32-32-4|a100': 'repair5g59_static_flow_shield', 'maze-32-32-4|a50': 'repair5g59_static_flow_shield', 'random-32-32-20|a100': 'repair5g59_static_flow_shield', 'random-32-32-20|a50': 'repair5g59_slow_decay_high_shield', 'warehouse-10-20-10-2-1|a100': 'repair5g59_static_flow_shield', 'warehouse-10-20-10-2-1|a50': 'repair5g59_static_flow_shield'}`
- safe_train_only_map_agent_gate_choices: `{'maze-32-32-4|a100': 'repair5g59_wait_conservative', 'maze-32-32-4|a50': 'repair5g59_block_heavy_flow_guard', 'random-32-32-20|a100': 'repair5g59_static_flow_shield', 'random-32-32-20|a50': 'repair5g59_slow_decay_high_shield', 'warehouse-10-20-10-2-1|a100': 'repair5g59_low_beta_high_cap', 'warehouse-10-20-10-2-1|a50': 'repair5g59_static_flow_shield'}`
- runtime_claim_allowed: `false`

## Policy Summaries

- `g512_ranker`: mean_delta_vs_static=-0.010423, harmful_rate=0.033, coverage=0.200, regret_to_oracle=0.027511
- `static_flow_shield`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `additive_ltm`: mean_delta_vs_static=0.089420, harmful_rate=0.933, coverage=1.000, regret_to_oracle=0.127354
- `slow_decay_high_shield_fixed`: mean_delta_vs_static=-0.008032, harmful_rate=0.433, coverage=1.000, regret_to_oracle=0.029902
- `safe_slow_decay_train_gate`: mean_delta_vs_static=-0.007964, harmful_rate=0.033, coverage=0.167, regret_to_oracle=0.029970
- `safe_train_only_map_agent_gate`: mean_delta_vs_static=-0.013731, harmful_rate=0.233, coverage=0.667, regret_to_oracle=0.024204
- `candidate_param_only_ranker`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `candidate_only_mean_delta_prior`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `map_agent_only_gate`: mean_delta_vs_static=-0.013731, harmful_rate=0.233, coverage=0.667, regret_to_oracle=0.024204
- `no_map_family_feature_ablation`: mean_delta_vs_static=-0.004128, harmful_rate=0.133, coverage=0.333, regret_to_oracle=0.033807
- `no_agent_feature_ablation`: mean_delta_vs_static=-0.007964, harmful_rate=0.033, coverage=0.167, regret_to_oracle=0.029970
- `no_candidate_param_ablation`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `interaction_only_ablation`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `true_random_feature_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `true_shuffled_label_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000, regret_to_oracle=0.037934
- `random_candidate`: mean_delta_vs_static=0.020152, harmful_rate=0.467, coverage=0.967, regret_to_oracle=0.058086
- `oracle_upper_bound`: mean_delta_vs_static=-0.037934, harmful_rate=0.000, coverage=1.000, regret_to_oracle=0.000000

All learned and prior controls are evaluated as grouped context decisions: score or select over all 14 candidates, choose a candidate only when the policy gate passes, otherwise fall back to static flow-shield. If the G5.12 ranker does not beat train-only safe priors, the result is reported as a simple-prior signal reduction rather than hidden as a pass.
