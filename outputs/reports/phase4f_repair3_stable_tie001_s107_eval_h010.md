# Phase4F LAU-LTM Offline Evaluation Report

Date: 2026-05-27 10:39:42
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `6a36212`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `artifacts\teacher\laur\full_repair3_stable_targets\update_labels\phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- model: `artifacts\models\laur_ltm\full_repair3_stable_tie001_mlp_s107\laur_mlp_v1_weights.json`
- probes: `artifacts\teacher\laur\full_repair1\probes\phase4_laur_probe_full_repair1.jsonl`

## Outputs

- summary_csv: `outputs\tables\phase4f_repair3_stable_tie001_s107_eval_h010.csv`

## Metrics

### all

- sample_count: `2985`
- rule_top1_accuracy: `0.4827470686767169`
- rule_top3_accuracy: `0.8244556113902848`
- non_neutral_rule_top1_accuracy: `0.4022177419354839`
- harmful_update_precision: `0.5064194008559201`
- harmful_update_recall: `0.9950946040644709`
- harmful_update_f1: `0.6712361143937603`
- safety_auroc: `0.7805404301599539`
- predicted_rule_validation_mean_delta_ratio: `0.02455257240561877`
- neutral_additive_rate: `0.423785594639866`

### train

- sample_count: `2526`
- rule_top1_accuracy: `0.4992082343626287`
- rule_top3_accuracy: `0.834916864608076`
- non_neutral_rule_top1_accuracy: `0.42105263157894735`
- harmful_update_precision: `0.5271578947368422`
- harmful_update_recall: `0.9984051036682615`
- harmful_update_f1: `0.6899972444199504`
- safety_auroc: `0.7855936474978183`
- predicted_rule_validation_mean_delta_ratio: `0.029238107964325855`
- neutral_additive_rate: `0.41330166270783847`

### validation

- sample_count: `459`
- rule_top1_accuracy: `0.39215686274509803`
- rule_top3_accuracy: `0.7668845315904139`
- non_neutral_rule_top1_accuracy: `0.2935153583617747`
- harmful_update_precision: `0.3916083916083916`
- harmful_update_recall: `0.9710982658959537`
- harmful_update_f1: `0.5581395348837209`
- safety_auroc: `0.7274950483042969`
- predicted_rule_validation_mean_delta_ratio: `-0.001233185374978262`
- neutral_additive_rate: `0.48148148148148145`

## Gate

- eval_script_runs_end_to_end: `True`
- schema_validation_passes: `True`
- model_export_file_exists: `True`
- validation_metrics_computed: `True`
- summary_csv_written: `True`
- passed: `True`

## Caveat

This offline eval checks exported-model inference and label metrics only. It is not a runtime performance claim; learned-update benefit still requires paired solver comparisons.
