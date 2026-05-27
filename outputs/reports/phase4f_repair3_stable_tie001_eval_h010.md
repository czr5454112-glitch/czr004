# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-27 10:38:14
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `6a36212`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts\teacher\laur\full_repair3_stable_targets\update_labels\phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- model: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp\laur_mlp_v1_weights.json`
- probes: `artifacts\teacher\laur\full_repair1\probes\phase4_laur_probe_full_repair1.jsonl`

## Outputs

- summary_csv: `outputs\tables\phase4f_repair3_stable_tie001_eval_h010.csv`

## Metrics

### all

- sample_count: `2985`
- rule_top1_accuracy: `0.47738693467336685`
- rule_top3_accuracy: `0.8321608040201005`
- non_neutral_rule_top1_accuracy: `0.38961693548387094`
- harmful_update_precision: `0.5084501977705861`
- harmful_update_recall: `0.9908899789768746`
- harmful_update_f1: `0.6720532319391633`
- safety_auroc: `0.7809843716406404`
- predicted_rule_validation_mean_delta_ratio: `0.02464643390567516`
- neutral_additive_rate: `0.42546063651591287`

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.4932699920823436`
- rule_top3_accuracy: `0.8436262866191607`
- non_neutral_rule_top1_accuracy: `0.407451212300414`
- harmful_update_precision: `0.5291878172588832`
- harmful_update_recall: `0.9976076555023924`
- harmful_update_f1: `0.6915422885572139`
- safety_auroc: `0.7865484537530217`
- predicted_rule_validation_mean_delta_ratio: `0.02764748543357856`
- neutral_additive_rate: `0.41963578780680916`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.3899782135076253`
- rule_top3_accuracy: `0.7690631808278867`
- non_neutral_rule_top1_accuracy: `0.28668941979522183`
- harmful_update_precision: `0.3908872901678657`
- harmful_update_recall: `0.9421965317919075`
- harmful_update_f1: `0.5525423728813559`
- safety_auroc: `0.7252920489914709`
- predicted_rule_validation_mean_delta_ratio: `0.008130843144272305`
- neutral_additive_rate: `0.45751633986928103`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and label metrics only. It is not a runtime performance claim; learned-update benefit still requires paired solver comparisons.
