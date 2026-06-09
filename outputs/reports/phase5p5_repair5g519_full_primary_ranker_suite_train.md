# Phase5.5 Repair5G.5.19 Full-Primary Ranker Suite Training

- decision: `ranker_suite_training_passed_continue_eval`
- train_rows: `660`
- dev_rows: `660`
- trained_model_count: `7`
- forbidden_feature_count: `0`
- tiny_mlp_ranker_max_64_hidden: `not_available_without_new_dependency`
- gradient_boosted_stumps_if_available_without_new_dependency: `not_available_without_new_dependency`
- runtime_claim_allowed: `false`

This training artifact records representative deterministic ridge/listwise/risk models. The evaluation script refits fold-local models for seed OOF and group holdouts so train-only priors and thresholds remain local to each split.
