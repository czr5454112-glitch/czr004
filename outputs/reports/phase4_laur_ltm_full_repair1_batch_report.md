# Phase4 LAU-LTM Pilot Batch Report

Date: 2026-05-27 08:39:42 
Status: failed

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-clean_untracked-present`
- platform: `Linux-5.15.0-171-generic-x86_64-with-glibc2.39`

## Scope

- mode: `phase4-full-repair1`
- run_count: 765
- maps: `['empty-16-16', 'empty-32-32', 'empty-48-48', 'maze-32-32-2', 'maze-32-32-4', 'random-32-32-10', 'random-32-32-20', 'random-64-64-10', 'random-64-64-20', 'room-32-32-4', 'room-64-64-8', 'warehouse-10-20-10-2-1', 'warehouse-20-40-10-2-1']`
- agent_counts: `[50, 100, 200, 400]`
- instances: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]`

## Outputs

- checkpoint_jsonl: `artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl`
- trace_jsonl: `artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.pipe`
- probe_output_jsonl: `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- dataset_jsonl: `artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl`
- model_output_dir: `artifacts/models/laur_ltm/full_repair1`
- batch_report_md: `outputs/reports/phase4_laur_ltm_full_repair1_batch_report.md`
- batch_summary_json: `outputs/reports/phase4_laur_ltm_full_repair1_batch_summary.json`
- log_dir: `outputs/logs/phase4_laur_full_repair1`
- compressed_trace_zst: `artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst`

## Dataset

- rows: 2985
- non_neutral_checkpoints: 2316
- harmful_update_count: 1427
- label_distribution: `{'block_heavy': 507, 'block_light': 252, 'commit_heavy': 449, 'decay_090': 164, 'decay_095': 178, 'neutral_additive': 669, 'wait_heavy': 282, 'wait_light': 484}`

## Gate

- batch_script_completed: `True`
- record_completed: `True`
- probe_completed: `True`
- dataset_completed: `True`
- train_completed: `True`
- eval_completed: `True`
- validation_non_neutral_checkpoints: `359`
- phase4f_validation_non_neutral_min: `50`
- phase4f_validation_non_neutral_gate: `True`
- phase4f_validation_rule_top1_accuracy: `0.30718954248366015`
- phase4f_validation_rule_top1_gate: `False`
- phase4f_validation_rule_top3_accuracy: `0.6427015250544662`
- phase4f_validation_rule_top3_gate: `False`
- phase4f_validation_harmful_update_recall: `0.953757225433526`
- phase4f_harmful_update_recall_gate: `True`
- phase4f_validation_harmful_update_precision: `0.40145985401459855`
- phase4f_harmful_update_precision_gate: `True`
- phase4f_validation_predicted_rule_mean_delta_ratio: `0.01098836822643145`
- phase4f_predicted_rule_mean_delta_gate: `True`
- phase4f_validation_neutral_additive_rate: `0.2701525054466231`
- phase4f_neutral_additive_documented: `True`
- phase4f_performance_gate_passed: `False`
- operational_gate_passed: `True`
- passed: `False`

## Notes

Pilot/full evidence requires held-out validation rows and enough non-neutral checkpoints. Smoke success alone is not a Phase5 learned-runtime claim.
