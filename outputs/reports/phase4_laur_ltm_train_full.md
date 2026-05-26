# Phase4F LAU-LTM Train Report

Date: 2026-05-26 17:53:29
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `9c395b1`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts/teacher/laur/full/update_labels/phase4_laur_update_dataset_full.jsonl`
- samples: 1897
- feature_count: 36
- rules: `['additive_ltm', 'commit_heavy', 'block_heavy', 'block_light', 'wait_light', 'wait_heavy', 'decay_095', 'decay_090', 'neutral_additive']`
- validation_source: `validation`

## Outputs

- output_dir: `artifacts/models/laur_ltm/full`
- weights: `artifacts/models/laur_ltm/full/laur_mlp_v1_weights.json`
- feature_stats: `artifacts/models/laur_ltm/full/laur_mlp_v1_feature_stats.json`
- rules_json: `artifacts/models/laur_ltm/full/laur_mlp_v1_rules.json`

## Training

- epochs: 500
- hidden_dim: 96
- final_loss: 0.970195

## Metrics

### train

- sample_count: `1439`
- rule_top1_accuracy: `0.7470465601111883`
- rule_top3_accuracy: `0.95135510771369`
- non_neutral_rule_top1_accuracy: `0.73215859030837`
- harmful_update_precision: `0.7554806070826307`
- harmful_update_recall: `0.7454242928452579`
- harmful_update_f1: `0.7504187604690117`
- safety_auroc: `0.8779897466037114`
- predicted_best_rule_mean_delta_ratio_proxy: `0.027481654006307414`
- neutral_additive_rate: `0.221681723419041`

### validation

- sample_count: `458`
- rule_top1_accuracy: `0.1943231441048035`
- rule_top3_accuracy: `0.46943231441048033`
- non_neutral_rule_top1_accuracy: `0.19197707736389685`
- harmful_update_precision: `0.5952380952380952`
- harmful_update_recall: `0.5524861878453039`
- harmful_update_f1: `0.5730659025787965`
- safety_auroc: `0.708538604224425`
- predicted_best_rule_mean_delta_ratio_proxy: `0.011878893305275808`
- neutral_additive_rate: `0.24017467248908297`

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
