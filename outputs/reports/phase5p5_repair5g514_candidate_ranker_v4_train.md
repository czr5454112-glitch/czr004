# Phase5.5 Repair5G.5.14 Candidate Ranker V4 Training

- decision: `candidate_ranker_v4_training_passed_continue_eval`
- model_type: `ridge_delta_plus_linear_probability_risk_v4`
- train_rows: `420`
- dev_rows: `420`
- feature_count: `61`
- rich_feature_count: `19`
- forbidden_feature_count: `0`
- thresholds: `{'predicted_delta_threshold': -0.005, 'harmful_risk_threshold': 0.075, 'confidence_margin_threshold': 0.0}`
- train_policy_metrics: `{'contexts': 30.0, 'mean_delta_vs_static': -0.013789553559, 'mean_delta_vs_additive': -0.09992675076899998, 'harmful_vs_static_rate': 0.03333333333333333, 'coverage': 0.43333333333333335, 'fallback_rate': 0.5666666666666667}`
- gates: `{'train_rows_gt_0': True, 'dev_rows_gt_0': True, 'feature_count_gt_0': True, 'rich_feature_count_gt_0': True, 'forbidden_feature_count_eq_0': True, 'finite_delta_targets_gt_0': True, 'seed_based_split': True}`
- runtime_claim_allowed: `false`

The v4 model is still an offline grouped-decision diagnostic. It scores candidate UpdateLTM parameter rows and uses static flow-shield fallback when its predicted improvement/risk gate does not pass.
