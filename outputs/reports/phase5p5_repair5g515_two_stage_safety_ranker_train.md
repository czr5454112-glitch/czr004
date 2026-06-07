# Phase5.5 Repair5G.5.15 Two-Stage Safety Ranker Training

- decision: `two_stage_safety_ranker_training_passed_continue_eval`
- model_type: `two_stage_context_gate_plus_interaction_ridge_ranker`
- train_rows: `420`
- train_contexts: `30`
- gate_feature_count: `65`
- rank_feature_count: `69`
- thresholds: `{'gate_use_nonstatic_threshold': 0.35, 'gate_context_risk_threshold': 0.8, 'rank_predicted_delta_threshold': -0.005, 'rank_harmful_risk_threshold': 0.05, 'rank_confidence_margin_threshold': 0.0}`
- train_policy_metrics: `{'row_type': 'policy_summary', 'policy': 'two_stage_safety_ranker', 'contexts': 30, 'mean_delta_vs_static': -0.010282068693333334, 'mean_delta_vs_additive': -0.09641926590333333, 'harmful_vs_static_rate': 0.0, 'coverage': 0.23333333333333334, 'fallback_rate': 0.7666666666666666, 'regret_to_oracle': 0.02197847035033333, 'risk_adjusted_utility_lambda_0p05': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p1': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p10': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p2': -0.010282068693333334, 'risk_adjusted_utility_lambda_0p20': -0.010282068693333334}`
- forbidden_feature_count: `0`
- runtime_claim_allowed: `false`

The gate head uses context and rich aggregate features only. The rank head uses candidate-varying parameter and interaction features, so context-only rich features are not allowed to drive candidate ordering directly.
