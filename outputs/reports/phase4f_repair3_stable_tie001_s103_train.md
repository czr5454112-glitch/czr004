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

- output_dir: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s103`
- weights: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s103\laur_mlp_v1_weights.json`
- feature_stats: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s103\laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s103\laur_mlp_v1_rules.json`

## Training

- epochs: 600
- hidden_dim: 64
- drop_features: `['blocked_count', 'blocked_per_agent', 'density', 'free_cells', 'local_degree_mean_topk', 'map_height', 'map_width', 'mean_topk_raw_before', 'new_nonzero_edges_count', 'nonzero_edges_before', 'obstacle_ratio', 'topk_blocked_edge_concentration']`
- soft_label_temperature: `0.005`
- soft_label_hard_mix: `0.7`
- final_loss: 1.889831

## Metrics

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.5087094220110847`
- rule_top3_accuracy: `0.8463974663499604`
- non_neutral_rule_top1_accuracy: `0.43169722057953874`
- harmful_update_precision: `0.7076438140267928`
- harmful_update_recall: `0.7161084529505582`
- harmful_update_f1: `0.7118509710661911`
- safety_auroc: `0.7823938240398022`
- predicted_best_rule_mean_delta_ratio_proxy: `0.03264571973364503`
- neutral_additive_rate: `0.4089469517022961`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.39433551198257083`
- rule_top3_accuracy: `0.7538126361655774`
- non_neutral_rule_top1_accuracy: `0.27986348122866894`
- harmful_update_precision: `0.5868263473053892`
- harmful_update_recall: `0.5664739884393064`
- harmful_update_f1: `0.5764705882352941`
- safety_auroc: `0.7345082663001739`
- predicted_best_rule_mean_delta_ratio_proxy: `0.009243162839598388`
- neutral_additive_rate: `0.49673202614379086`

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
