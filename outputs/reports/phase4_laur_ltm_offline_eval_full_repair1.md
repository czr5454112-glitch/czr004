# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-27 08:39:42 
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl`
- model: `artifacts/models/laur_ltm/full_repair1/laur_mlp_v1_weights.json`
- probes: `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`

## Outputs

- summary_csv: `outputs/tables/phase4_laur_ltm_offline_eval_full_repair1.csv`

## Metrics

### all

- sample_count: `2985`
- rule_top1_accuracy: `0.40938023450586264`
- rule_top3_accuracy: `0.7480737018425461`
- non_neutral_rule_top1_accuracy: `0.3903281519861831`
- harmful_update_precision: `0.5115774240231549`
- harmful_update_recall: `0.9908899789768746`
- harmful_update_f1: `0.6747792889525173`
- safety_auroc: `0.7833372165094056`
- predicted_rule_validation_mean_delta_ratio: `0.03145251246145307`
- neutral_additive_rate: `0.2552763819095477`

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.42794932699920823`
- rule_top3_accuracy: `0.7672209026128266`
- non_neutral_rule_top1_accuracy: `0.40929994890137966`
- harmful_update_precision: `0.5308117297067574`
- harmful_update_recall: `0.9960127591706539`
- harmful_update_f1: `0.6925422789021347`
- safety_auroc: `0.7881853540368933`
- predicted_rule_validation_mean_delta_ratio: `0.035171056485156525`
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
- predicted_rule_validation_mean_delta_ratio: `0.01098836822643145`
- neutral_additive_rate: `0.2701525054466231`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and label metrics only. It is not a runtime performance claim; learned-update benefit still requires paired solver comparisons.
