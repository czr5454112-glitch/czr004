# Phase4F LAU-LTM Train Smoke Report

Date: 2026-05-26 14:57:52
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `e648089`
- dirty: `tracked-dirty`

## Inputs

- dataset: `artifacts/teacher/laur/pilot/update_labels/phase4_laur_update_dataset_pilot.jsonl`
- samples: 320
- feature_count: 36
- rules: `['additive_ltm', 'commit_heavy', 'block_heavy', 'block_light', 'wait_light', 'wait_heavy', 'decay_095', 'decay_090', 'neutral_additive']`
- validation_source: `validation`

## Outputs

- output_dir: `artifacts/models/laur_ltm/pilot`
- weights: `artifacts/models/laur_ltm/pilot/laur_mlp_v1_weights.json`
- feature_stats: `artifacts/models/laur_ltm/pilot/laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts/models/laur_ltm/pilot/laur_mlp_v1_rules.json`

## Training

- epochs: 300
- hidden_dim: 64
- final_loss: 0.066576

## Metrics

### train

- sample_count: `240`
- rule_top1_accuracy: `1.0`
- rule_top3_accuracy: `1.0`
- non_neutral_rule_top1_accuracy: `1.0`
- harmful_update_precision: `1.0`
- harmful_update_recall: `1.0`
- harmful_update_f1: `1.0`
- safety_auroc: `1.0`
- predicted_best_rule_mean_delta_ratio_proxy: `0.024696161650952675`
- neutral_additive_rate: `0.2`

### validation

- sample_count: `80`
- rule_top1_accuracy: `0.1375`
- rule_top3_accuracy: `0.4875`
- non_neutral_rule_top1_accuracy: `0.15517241379310345`
- harmful_update_precision: `0.4`
- harmful_update_recall: `0.07142857142857142`
- harmful_update_f1: `0.12121212121212122`
- safety_auroc: `0.3873626373626374`
- predicted_best_rule_mean_delta_ratio_proxy: `0.0024322686550648748`
- neutral_additive_rate: `0.1125`

### test

- map-holdout test performance: `not_available_in_smoke_dataset`

## Gate

- train_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- phase4f_smoke_passed: `True`
- passed: `True`

## Caveat

This smoke run proves the Phase4F training/export path only. The current local dataset has four train-split samples, so validation falls back to all-row smoke reuse and must not be used as a learned-update performance claim.
