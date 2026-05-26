# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-26 14:57:55
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `e648089`
- dirty: `tracked-dirty`

## Inputs

- dataset: `artifacts/teacher/laur/pilot/update_labels/phase4_laur_update_dataset_pilot.jsonl`
- model: `artifacts/models/laur_ltm/pilot/laur_mlp_v1_weights.json`
- probes: `artifacts/teacher/laur/pilot/probes/phase4_laur_probe_pilot.jsonl`

## Outputs

- summary_csv: `outputs/tables/phase4_laur_ltm_offline_eval_pilot.csv`

## Metrics

### all

- sample_count: `320`
- rule_top1_accuracy: `0.784375`
- rule_top3_accuracy: `0.871875`
- non_neutral_rule_top1_accuracy: `0.804`
- harmful_update_precision: `0.961038961038961`
- harmful_update_recall: `0.74`
- harmful_update_f1: `0.8361581920903954`
- safety_auroc: `0.7908636363636363`
- predicted_rule_validation_mean_delta_ratio: `0.018798308294264394`
- neutral_additive_rate: `0.178125`

### train

- sample_count: `240`
- rule_top1_accuracy: `1.0`
- rule_top3_accuracy: `1.0`
- non_neutral_rule_top1_accuracy: `1.0`
- harmful_update_precision: `1.0`
- harmful_update_recall: `1.0`
- harmful_update_f1: `1.0`
- safety_auroc: `1.0`
- predicted_rule_validation_mean_delta_ratio: `0.024378808616423792`
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
- predicted_rule_validation_mean_delta_ratio: `0.0020568073277862`
- neutral_additive_rate: `0.1125`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and metrics only. The smoke dataset is too small for a learned-update performance claim.
