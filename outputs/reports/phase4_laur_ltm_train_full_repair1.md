# Phase4F LAU-LTM Train Report

Date: 2026-05-27 08:39:38 
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl`
- samples: 2985
- feature_count: 24
- rules: `['additive_ltm', 'commit_heavy', 'block_heavy', 'block_light', 'wait_light', 'wait_heavy', 'decay_095', 'decay_090', 'neutral_additive']`
- validation_source: `validation`

## Outputs

- output_dir: `artifacts/models/laur_ltm/full_repair1`
- weights: `artifacts/models/laur_ltm/full_repair1/laur_mlp_v1_weights.json`
- feature_stats: `artifacts/models/laur_ltm/full_repair1/laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts/models/laur_ltm/full_repair1/laur_mlp_v1_rules.json`

## Training

- epochs: 600
- hidden_dim: 64
- drop_features: `['blocked_count', 'blocked_per_agent', 'density', 'free_cells', 'local_degree_mean_topk', 'map_height', 'map_width', 'mean_topk_raw_before', 'new_nonzero_edges_count', 'nonzero_edges_before', 'obstacle_ratio', 'topk_blocked_edge_concentration']`
- soft_label_temperature: `0.005`
- soft_label_hard_mix: `0.7`
- final_loss: 1.978680

## Metrics

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.42794932699920823`
- rule_top3_accuracy: `0.7672209026128266`
- non_neutral_rule_top1_accuracy: `0.40929994890137966`
- harmful_update_precision: `0.5308117297067574`
- harmful_update_recall: `0.9960127591706539`
- harmful_update_f1: `0.6925422789021347`
- safety_auroc: `0.7881853540368933`
- predicted_best_rule_mean_delta_ratio_proxy: `0.03485088421070784`
- neutral_additive_rate: `0.25257323832145684`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.30718954248366015`
- rule_top3_accuracy: `0.6427015250544662`
- non_neutral_rule_top1_accuracy: `0.28690807799442897`
- harmful_update_precision: `0.40145985401459855`
- harmful_update_recall: `0.953757225433526`
- harmful_update_f1: `0.5650684931506849`
- safety_auroc: `0.7299810016573023`
- predicted_best_rule_mean_delta_ratio_proxy: `0.015340658592361521`
- neutral_additive_rate: `0.2701525054466231`

### test

- map-holdout test performance: `not_available`

## Gate

- train_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- phase4f_smoke_passed: `True`
- passed: `True`

## Caveat

This report evaluates checkpoint-level update-rule prediction on collected probe labels. It is offline evidence only; runtime benefit still requires paired solver comparisons before making a learned-update performance claim.
