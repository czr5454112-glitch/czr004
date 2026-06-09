# Phase4F LAU-LTM Train Report

Date: 2026-05-27 10:37:06
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

- output_dir: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp`
- weights: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp\laur_mlp_v1_weights.json`
- feature_stats: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp\laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp\laur_mlp_v1_rules.json`

## Training

- epochs: 600
- hidden_dim: 64
- drop_features: `['blocked_count', 'blocked_per_agent', 'density', 'free_cells', 'local_degree_mean_topk', 'map_height', 'map_width', 'mean_topk_raw_before', 'new_nonzero_edges_count', 'nonzero_edges_before', 'obstacle_ratio', 'topk_blocked_edge_concentration']`
- soft_label_temperature: `0.005`
- soft_label_hard_mix: `0.7`
- final_loss: 1.900595

## Metrics

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.4932699920823436`
- rule_top3_accuracy: `0.8436262866191607`
- non_neutral_rule_top1_accuracy: `0.407451212300414`
- harmful_update_precision: `0.7099533437013997`
- harmful_update_recall: `0.7280701754385965`
- harmful_update_f1: `0.7188976377952757`
- safety_auroc: `0.7865490806776805`
- predicted_best_rule_mean_delta_ratio_proxy: `0.030343334061652082`
- neutral_additive_rate: `0.41963578780680916`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.3899782135076253`
- rule_top3_accuracy: `0.7690631808278867`
- non_neutral_rule_top1_accuracy: `0.28668941979522183`
- harmful_update_precision: `0.5974842767295597`
- harmful_update_recall: `0.5491329479768786`
- harmful_update_f1: `0.572289156626506`
- safety_auroc: `0.7252920489914709`
- predicted_best_rule_mean_delta_ratio_proxy: `0.008146046187875275`
- neutral_additive_rate: `0.45751633986928103`

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
