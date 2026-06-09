# Phase5.5 Repair5G.5.15 Pairwise Context Ranker Training

- decision: `pairwise_context_ranker_training_passed_continue_eval`
- model_type: `pairwise_within_context_ridge_difference_ranker`
- train_rows: `420`
- pairwise_training_rows: `2730`
- feature_count: `69`
- thresholds: `{'predicted_delta_threshold': -0.005, 'harmful_risk_threshold': 0.05, 'confidence_margin_threshold': 0.0}`
- train_policy_metrics: `{'row_type': 'policy_summary', 'policy': 'pairwise_context_ranker', 'contexts': 30, 'mean_delta_vs_static': -0.010282068693333334, 'mean_delta_vs_additive': -0.09641926590333333, 'harmful_vs_static_rate': 0.0, 'coverage': 0.23333333333333334, 'fallback_rate': 0.7666666666666666, 'regret_to_oracle': 0.02197847035033333, 'risk_adjusted_utility_lambda_0p05': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p1': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p10': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p2': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p20': -0.010282068693333334}`
- forbidden_feature_count: `0`
- runtime_claim_allowed: `false`

The pairwise model trains on within-context candidate feature differences and then scores candidate rows with the learned linear utility. It remains an offline diagnostic and exports no runtime policy.
