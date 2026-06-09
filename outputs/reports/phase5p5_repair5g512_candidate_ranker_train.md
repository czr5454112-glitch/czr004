# Phase5.5 Repair5G.5.12 Candidate Ranker Training

- decision: `candidate_ranker_training_passed_continue_eval`
- model_type: `ridge_delta_plus_linear_probability_risk`
- train_rows: `420`
- dev_rows: `420`
- feature_count: `42`
- forbidden_feature_count: `0`
- delta_train_mse: `0.002963890069205765`
- risk_train_mse: `0.11980567548328895`
- thresholds: `{'predicted_delta_threshold': -0.01, 'harmful_risk_threshold': 0.075, 'confidence_margin_threshold': 0.0}`
- train_policy_metrics: `{'contexts': 30.0, 'mean_delta_vs_static': -0.010635243922333334, 'mean_delta_vs_additive': -0.09677244113233333, 'harmful_vs_static_rate': 0.03333333333333333, 'coverage': 0.3, 'fallback_rate': 0.7}`
- best_single_train_candidate: `repair5g59_slow_decay_high_shield`
- train_only_majority_candidate: `repair5g59_slow_decay_high_shield`
- gates: `{'train_rows_gt_0': True, 'dev_rows_gt_0': True, 'feature_count_gt_0': True, 'forbidden_feature_count_eq_0': True, 'finite_delta_targets_gt_0': True, 'seed_based_split': True}`

The training script fits a deterministic ridge regression for predicted delta and a ridge linear-probability risk head for harmful-vs-static risk. It also trains true random-feature and shuffled-label controls for the grouped dev evaluation. No runtime policy is validated or exported.
