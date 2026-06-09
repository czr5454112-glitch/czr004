# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-26 13:29:10
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `ddaefa2`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl`
- model: `artifacts\models\laur_ltm\smoke\laur_mlp_v1_weights.json`
- probes: `artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl`

## Outputs

- summary_csv: `outputs\tables\phase4_laur_ltm_offline_eval.csv`

## Metrics

### all

- sample_count: `4`
- rule_top1_accuracy: `1.0`
- rule_top3_accuracy: `1.0`
- non_neutral_rule_top1_accuracy: `1.0`
- harmful_update_precision: `1.0`
- harmful_update_recall: `1.0`
- harmful_update_f1: `1.0`
- safety_auroc: `1.0`
- predicted_rule_validation_mean_delta_ratio: `0.0211141060197675`
- neutral_additive_rate: `0.0`

### train

- sample_count: `4`
- rule_top1_accuracy: `1.0`
- rule_top3_accuracy: `1.0`
- non_neutral_rule_top1_accuracy: `1.0`
- harmful_update_precision: `1.0`
- harmful_update_recall: `1.0`
- harmful_update_f1: `1.0`
- safety_auroc: `1.0`
- predicted_rule_validation_mean_delta_ratio: `0.0211141060197675`
- neutral_additive_rate: `0.0`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and metrics only. The smoke dataset is too small for a learned-update performance claim.
