# Phase5.5 Repair5G.5.13 Bootstrap Uncertainty

- decision: `bootstrap_uncertainty_reported`
- dev_contexts: `30`
- bootstrap_samples: `2000`
- g512_mean_delta_vs_static_interval: `{'row_type': 'policy_interval', 'policy': 'g512_ranker', 'rhs_policy': '', 'metric': 'mean_delta_vs_static', 'estimate': -0.010423295036333333, 'ci_low_p025': -0.021546915625858334, 'ci_high_p975': -0.001935500437, 'bootstrap_samples': 2000}`
- g512_harmful_vs_static_rate_interval: `{'row_type': 'policy_interval', 'policy': 'g512_ranker', 'rhs_policy': '', 'metric': 'harmful_vs_static_rate', 'estimate': 0.03333333333333333, 'ci_low_p025': 0.0, 'ci_high_p975': 0.1, 'bootstrap_samples': 2000}`
- g512_coverage_interval: `{'row_type': 'policy_interval', 'policy': 'g512_ranker', 'rhs_policy': '', 'metric': 'coverage', 'estimate': 0.2, 'ci_low_p025': 0.06666666666666667, 'ci_high_p975': 0.3333333333333333, 'bootstrap_samples': 2000}`
- g512_regret_to_oracle_interval: `{'row_type': 'policy_interval', 'policy': 'g512_ranker', 'rhs_policy': '', 'metric': 'regret_to_oracle', 'estimate': 0.027511037073000004, 'ci_low_p025': 0.016980973490691664, 'ci_high_p975': 0.03943483652210832, 'bootstrap_samples': 2000}`
- difference_vs_safe_slow_decay_train_gate: `{'row_type': 'policy_difference_interval', 'policy': 'g512_ranker', 'rhs_policy': 'safe_slow_decay_train_gate', 'metric': 'difference_vs_control_mean_delta_vs_static', 'estimate': -0.0024592683676666668, 'ci_low_p025': -0.007377805103000001, 'ci_high_p975': 0.0, 'bootstrap_samples': 2000}`
- difference_vs_safe_train_only_map_agent_gate: `{'row_type': 'policy_difference_interval', 'policy': 'g512_ranker', 'rhs_policy': 'safe_train_only_map_agent_gate', 'metric': 'difference_vs_control_mean_delta_vs_static', 'estimate': 0.003307332936999998, 'ci_low_p025': -0.007216383100458336, 'ci_high_p975': 0.014461535744075004, 'bootstrap_samples': 2000}`
- runtime_claim_allowed: `false`

Intervals are nonparametric bootstraps over dev contexts. Negative differences in mean delta mean the G5.12 ranker is better than the control; positive differences mean the control has lower selected-vs-static delta on the sampled contexts.
