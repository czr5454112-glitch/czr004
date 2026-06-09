# Phase5.5 Repair5G.5.16 Pessimistic Safety-Bound Ranker Training

- decision: `pessimistic_safety_bound_ranker_training_passed_continue_eval`
- train_rows: `420`
- feature_count: `138`
- forbidden_feature_count: `0`
- delta_abs_residual_quantiles: `{'0.0': 1.1940154044786256e-05, '0.8': 0.0321118658045374, '0.9': 0.04578648641957287, '0.95': 0.05939118339133311}`
- risk_upper_residual_quantiles: `{'0.0': 0.0, '0.8': 0.2058531824669647, '0.9': 0.507053198197353, '0.95': 0.6337675103493409}`
- gates: `{'train_rows_gt_0': True, 'dev_rows_gt_0': True, 'feature_count_gt_0': True, 'forbidden_feature_count_eq_0': True, 'train_contexts_gt_0': True, 'models_include_required_variants': True}`
- runtime_export_allowed: `false`

## Train Policy Summaries

- `ultra_safe_bound`: mean_delta=0.0, harmful=0.0, coverage=0.0, fp=0, missed=26
- `balanced_bound`: mean_delta=0.0, harmful=0.0, coverage=0.0, fp=0, missed=26
- `opportunity_diagnostic_not_for_promotion`: mean_delta=0.0, harmful=0.0, coverage=0.0, fp=0, missed=26
- `no_error_bank_feature_ablation`: mean_delta=0.0, harmful=0.0, coverage=0.0, fp=0, missed=26
- `no_pessimistic_bound_ablation`: mean_delta=-0.010078259728, harmful=0.0, coverage=0.26666666666666666, fp=0, missed=18
