# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-27 10:39:42
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `6a36212`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts\teacher\laur\full_repair3_stable_targets\update_labels\phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- model: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s103\laur_mlp_v1_weights.json`
- probes: `artifacts\teacher\laur\full_repair1\probes\phase4_laur_probe_full_repair1.jsonl`

## Outputs

- summary_csv: `outputs\tables\phase4f_repair3_stable_tie001_s103_eval_h010.csv`

## Metrics

### all

- sample_count: `2985`
- rule_top1_accuracy: `0.4911222780569514`
- rule_top3_accuracy: `0.8321608040201005`
- non_neutral_rule_top1_accuracy: `0.4092741935483871`
- harmful_update_precision: `0.504270462633452`
- harmful_update_recall: `0.9929922915206727`
- harmful_update_f1: `0.6688694831248526`
- safety_auroc: `0.7783319674748771`
- predicted_rule_validation_mean_delta_ratio: `0.024572441312171237`
- neutral_additive_rate: `0.4224455611390285`

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.5087094220110847`
- rule_top3_accuracy: `0.8463974663499604`
- non_neutral_rule_top1_accuracy: `0.43169722057953874`
- harmful_update_precision: `0.5241292488459924`
- harmful_update_recall: `0.9960127591706539`
- harmful_update_f1: `0.6868298047841628`
- safety_auroc: `0.7823938240398022`
- predicted_rule_validation_mean_delta_ratio: `0.029226806637671156`
- neutral_additive_rate: `0.4089469517022961`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.39433551198257083`
- rule_top3_accuracy: `0.7538126361655774`
- non_neutral_rule_top1_accuracy: `0.27986348122866894`
- harmful_update_precision: `0.39344262295081966`
- harmful_update_recall: `0.9710982658959537`
- harmful_update_f1: `0.5599999999999999`
- safety_auroc: `0.7345082663001739`
- predicted_rule_validation_mean_delta_ratio: `-0.0010417783222792458`
- neutral_additive_rate: `0.49673202614379086`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and label metrics only. It is not a runtime performance claim; learned-update benefit still requires paired solver comparisons.
