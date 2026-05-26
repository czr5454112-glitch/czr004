# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-26 17:53:34
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `9c395b1`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts/teacher/laur/full/update_labels/phase4_laur_update_dataset_full.jsonl`
- model: `artifacts/models/laur_ltm/full/laur_mlp_v1_weights.json`
- probes: `artifacts/teacher/laur/full/probes/phase4_laur_probe_full.jsonl`

## Outputs

- summary_csv: `outputs/tables/phase4_laur_ltm_offline_eval_full.csv`

## Metrics

### all

- sample_count: `1897`
- rule_top1_accuracy: `0.6136004217185029`
- rule_top3_accuracy: `0.8355297838692672`
- non_neutral_rule_top1_accuracy: `0.605121293800539`
- harmful_update_precision: `0.7201051248357424`
- harmful_update_recall: `0.7007672634271099`
- harmful_update_f1: `0.7103046014257939`
- safety_auroc: `0.8344362506164485`
- predicted_rule_validation_mean_delta_ratio: `0.022119483254420803`
- neutral_additive_rate: `0.22614654717975752`

### train

- sample_count: `1439`
- rule_top1_accuracy: `0.7470465601111883`
- rule_top3_accuracy: `0.95135510771369`
- non_neutral_rule_top1_accuracy: `0.73215859030837`
- harmful_update_precision: `0.7554806070826307`
- harmful_update_recall: `0.7454242928452579`
- harmful_update_f1: `0.7504187604690117`
- safety_auroc: `0.8779897466037114`
- predicted_rule_validation_mean_delta_ratio: `0.02824749635885571`
- neutral_additive_rate: `0.221681723419041`

### validation

- sample_count: `458`
- rule_top1_accuracy: `0.1943231441048035`
- rule_top3_accuracy: `0.47161572052401746`
- non_neutral_rule_top1_accuracy: `0.19197707736389685`
- harmful_update_precision: `0.5952380952380952`
- harmful_update_recall: `0.5524861878453039`
- harmful_update_f1: `0.5730659025787965`
- safety_auroc: `0.7090172926182261`
- predicted_rule_validation_mean_delta_ratio: `0.0028657477581722716`
- neutral_additive_rate: `0.24017467248908297`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and label metrics only. It is not a runtime performance claim; learned-update benefit still requires paired solver comparisons.
