# Phase4 LAU-LTM Pilot Batch Report

Date: 2026-05-26 17:53:34
Status: failed

## Code State

- branch: `phase4-laur-ltm`
- commit: `9c395b1`
- dirty: `tracked-clean_untracked-present`
- platform: `Linux-5.15.0-171-generic-x86_64-with-glibc2.39`

## Scope

- mode: `phase4-full`
- run_count: 480
- maps: `['empty-32-32', 'empty-48-48', 'maze-32-32-4', 'random-32-32-20', 'random-64-64-20', 'room-64-64-8', 'warehouse-10-20-10-2-1', 'warehouse-10-20-10-2-2']`
- agent_counts: `[50, 100, 200, 400]`
- instances: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]`

## Outputs

- checkpoint_jsonl: `artifacts/teacher/laur/full/checkpoints/phase4_laur_checkpoints_full.jsonl`
- trace_jsonl: `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.pipe`
- probe_output_jsonl: `artifacts/teacher/laur/full/probes/phase4_laur_probe_full.jsonl`
- dataset_jsonl: `artifacts/teacher/laur/full/update_labels/phase4_laur_update_dataset_full.jsonl`
- model_output_dir: `artifacts/models/laur_ltm/full`
- batch_report_md: `outputs/reports/phase4_laur_ltm_full_batch_report.md`
- batch_summary_json: `outputs/reports/phase4_laur_ltm_full_batch_summary.json`
- log_dir: `outputs/logs/phase4_laur_full`
- compressed_trace_zst: `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst`

## Dataset

- rows: 1897
- non_neutral_checkpoints: 1484
- harmful_update_count: 782
- label_distribution: `{'block_heavy': 325, 'block_light': 163, 'commit_heavy': 316, 'decay_090': 98, 'decay_095': 87, 'neutral_additive': 413, 'wait_heavy': 213, 'wait_light': 282}`

## Gate

- batch_script_completed: `True`
- record_completed: `True`
- probe_completed: `True`
- dataset_completed: `True`
- train_completed: `True`
- eval_completed: `True`
- validation_non_neutral_checkpoints: `349`
- phase4f_validation_non_neutral_min: `50`
- phase4f_validation_non_neutral_gate: `True`
- phase4f_validation_rule_top1_accuracy: `0.1943231441048035`
- phase4f_validation_rule_top1_gate: `False`
- phase4f_validation_rule_top3_accuracy: `0.47161572052401746`
- phase4f_validation_rule_top3_gate: `False`
- phase4f_validation_harmful_update_recall: `0.5524861878453039`
- phase4f_harmful_update_recall_gate: `False`
- phase4f_validation_harmful_update_precision: `0.5952380952380952`
- phase4f_harmful_update_precision_gate: `True`
- phase4f_validation_predicted_rule_mean_delta_ratio: `0.0028657477581722716`
- phase4f_predicted_rule_mean_delta_gate: `True`
- phase4f_validation_neutral_additive_rate: `0.24017467248908297`
- phase4f_neutral_additive_documented: `True`
- phase4f_performance_gate_passed: `False`
- operational_gate_passed: `True`
- passed: `False`

## Notes

Pilot/full evidence requires held-out validation rows and enough non-neutral checkpoints. Smoke success alone is not a Phase5 learned-runtime claim.
