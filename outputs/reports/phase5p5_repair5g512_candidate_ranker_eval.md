# Phase5.5 Repair5G.5.12 Candidate Ranker Eval

- decision: `candidate_ranker_passed_continue_static_abstention_safety_package`
- dev_contexts: `30`
- thresholds: `{'confidence_margin_threshold': 0.0, 'harmful_risk_threshold': 0.075, 'predicted_delta_threshold': -0.01}`
- primary_policy: `{'row_type': 'policy_summary', 'policy': 'g512_ranker', 'contexts': 30, 'mean_delta_vs_static': -0.010423295036333333, 'mean_delta_vs_additive': -0.09984319068166667, 'harmful_vs_static_rate': 0.03333333333333333, 'coverage': 0.19999999999999996, 'fallback_rate': 0.8}`
- gates: `{'mean_delta_vs_static_lt_0': True, 'mean_delta_vs_additive_lt_0': True, 'harmful_vs_static_rate_le_0p10': True, 'harmful_vs_static_rate_le_0p05': True, 'beats_true_random_feature_model': True, 'beats_true_shuffled_label_model': True, 'beats_train_only_map_agent_prior': True, 'beats_slow_decay_high_shield_fixed': True, 'beats_best_single_train_candidate': True, 'no_ids_166_205': True, 'runtime_claim_allowed_false': True}`
- coverage_risk_curve_reported: `true`
- calibration_reported: `true`
- runtime_claim_allowed: `false`

## Policy Summaries

- `g512_ranker`: mean_delta_vs_static=-0.010423, harmful_rate=0.033, coverage=0.200
- `static_flow_shield`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000
- `additive_ltm`: mean_delta_vs_static=0.089420, harmful_rate=0.933, coverage=1.000
- `slow_decay_high_shield_fixed`: mean_delta_vs_static=-0.008032, harmful_rate=0.433, coverage=1.000
- `best_single_train_candidate`: mean_delta_vs_static=-0.008032, harmful_rate=0.433, coverage=1.000
- `train_only_majority_candidate`: mean_delta_vs_static=-0.008032, harmful_rate=0.433, coverage=1.000
- `train_only_map_agent_prior`: mean_delta_vs_static=-0.004801, harmful_rate=0.533, coverage=1.000
- `random_candidate`: mean_delta_vs_static=0.020152, harmful_rate=0.467, coverage=0.967
- `oracle_upper_bound`: mean_delta_vs_static=-0.037934, harmful_rate=0.000, coverage=1.000
- `true_random_feature_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000
- `true_shuffled_label_model`: mean_delta_vs_static=0.000000, harmful_rate=0.000, coverage=0.000

Evaluation is grouped by context: all 14 candidates are scored, the policy either selects one candidate or falls back to static flow-shield, and the selected candidate is compared against static, additive, fixed-candidate, prior, random, shuffled-label, random-feature, and oracle baselines. This remains an offline diagnostic, not a learned runtime-policy validation.
