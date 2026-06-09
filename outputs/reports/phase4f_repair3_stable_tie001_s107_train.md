# Phase4F LAU-LTM Train Report

Date: 2026-05-27 10:39:19
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `6a36212`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts\teacher\laur\full_repair3_stable_targets\update_labels\phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- samples: 2985
- feature_count: 24
- rules: `['additive_ltm', 'commit_heavy', 'block_heavy', 'block_light', 'wait_light', 'wait_heavy', 'decay_095', 'decay_090', 'neutral_additive']`
- validation_source: `validation`

## Outputs

- output_dir: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s107`
- weights: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s107\laur_mlp_v1_weights.json`
- feature_stats: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s107\laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s107\laur_mlp_v1_rules.json`

## Training

- epochs: 600
- hidden_dim: 64
- drop_features: `['blocked_count', 'blocked_per_agent', 'density', 'free_cells', 'local_degree_mean_topk', 'map_height', 'map_width', 'mean_topk_raw_before', 'new_nonzero_edges_count', 'nonzero_edges_before', 'obstacle_ratio', 'topk_blocked_edge_concentration']`
- soft_label_temperature: `0.005`
- soft_label_hard_mix: `0.7`
- final_loss: 1.889658

## Metrics

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.4992082343626287`
- rule_top3_accuracy: `0.834916864608076`
- non_neutral_rule_top1_accuracy: `0.42105263157894735`
- harmful_update_precision: `0.7087227414330218`
- harmful_update_recall: `0.7256778309409888`
- harmful_update_f1: `0.7171000788022066`
- safety_auroc: `0.7855936474978183`
- predicted_best_rule_mean_delta_ratio_proxy: `0.031396942128792876`
- neutral_additive_rate: `0.41330166270783847`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.39215686274509803`
- rule_top3_accuracy: `0.7668845315904139`
- non_neutral_rule_top1_accuracy: `0.2935153583617747`
- harmful_update_precision: `0.5808383233532934`
- harmful_update_recall: `0.5606936416184971`
- harmful_update_f1: `0.5705882352941176`
- safety_auroc: `0.7274950483042969`
- predicted_best_rule_mean_delta_ratio_proxy: `0.00759093642479329`
- neutral_additive_rate: `0.48148148148148145`

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
