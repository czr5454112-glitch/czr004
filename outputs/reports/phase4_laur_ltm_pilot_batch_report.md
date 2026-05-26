# Phase4 LAU-LTM Pilot Batch Report

Date: 2026-05-26 14:57:56
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `e648089`
- dirty: `tracked-dirty`
- platform: `Linux-5.15.0-171-generic-x86_64-with-glibc2.39`

## Scope

- mode: `pilot`
- run_count: 80
- maps: `['empty-32-32', 'empty-48-48', 'maze-32-32-4', 'random-32-32-20', 'random-64-64-20', 'room-64-64-8', 'warehouse-10-20-10-2-1', 'warehouse-10-20-10-2-2']`
- agent_counts: `[50, 100]`
- instances: `[1, 2, 3, 4, 5]`

## Outputs

- checkpoint_jsonl: `artifacts/teacher/laur/pilot/checkpoints/phase4_laur_checkpoints_pilot.jsonl`
- trace_jsonl: `artifacts/teacher/laur/pilot/traces/phase4_laur_trace_pilot.jsonl`
- probe_output_jsonl: `artifacts/teacher/laur/pilot/probes/phase4_laur_probe_pilot.jsonl`
- dataset_jsonl: `artifacts/teacher/laur/pilot/update_labels/phase4_laur_update_dataset_pilot.jsonl`
- model_output_dir: `artifacts/models/laur_ltm/pilot`
- batch_report_md: `outputs/reports/phase4_laur_ltm_pilot_batch_report.md`
- batch_summary_json: `outputs/reports/phase4_laur_ltm_pilot_batch_summary.json`
- log_dir: `outputs/logs/phase4_laur_pilot`

## Dataset

- rows: 320
- non_neutral_checkpoints: 250
- harmful_update_count: 100
- label_distribution: `{'block_heavy': 65, 'block_light': 21, 'commit_heavy': 63, 'decay_090': 23, 'decay_095': 13, 'neutral_additive': 70, 'wait_heavy': 38, 'wait_light': 27}`

## Gate

- batch_script_completed: `True`
- record_completed: `True`
- probe_completed: `True`
- dataset_completed: `True`
- train_completed: `True`
- eval_completed: `True`
- validation_non_neutral_checkpoints: `58`
- pilot_validation_non_neutral_gate: `True`
- passed: `True`

## Notes

Pilot/full evidence requires held-out validation rows and enough non-neutral checkpoints. Smoke success alone is not a Phase5 learned-runtime claim.
