# Phase4 LAU-LTM Pilot Batch Report

Date: 2026-05-28 14:23:17 
Status: failed

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty`
- platform: `Linux-5.15.0-171-generic-x86_64-with-glibc2.39`

## Scope

- mode: `phase4-full-repair5-expand5000`
- run_count: 1275
- maps: `['empty-16-16', 'empty-32-32', 'empty-48-48', 'maze-32-32-2', 'maze-32-32-4', 'random-32-32-10', 'random-32-32-20', 'random-64-64-10', 'random-64-64-20', 'room-32-32-4', 'room-64-64-8', 'warehouse-10-20-10-2-1', 'warehouse-20-40-10-2-1']`
- agent_counts: `[50, 100, 200, 400]`
- instances: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`

## Outputs

- checkpoint_jsonl: `artifacts/teacher/laur/full_repair5_expand5000/checkpoints/phase4_laur_checkpoints_full_repair5_expand5000.jsonl`
- trace_jsonl: `artifacts/teacher/laur/full_repair5_expand5000/traces/phase4_laur_trace_full_repair5_expand5000.jsonl.pipe`
- probe_output_jsonl: `artifacts/teacher/laur/full_repair5_expand5000/probes/phase4_laur_probe_full_repair5_expand5000.jsonl`
- dataset_jsonl: `artifacts/teacher/laur/full_repair5_expand5000/update_labels/phase4_laur_update_dataset_full_repair5_expand5000.jsonl`
- model_output_dir: `artifacts/models/laur_ltm/full_repair5_expand5000`
- batch_report_md: `outputs/reports/phase4_laur_ltm_full_repair5_expand5000_batch_report.md`
- batch_summary_json: `outputs/reports/phase4_laur_ltm_full_repair5_expand5000_batch_summary.json`
- log_dir: `outputs/logs/phase4_laur_full_repair5_expand5000`
- compressed_trace_zst: `artifacts/teacher/laur/full_repair5_expand5000/traces/phase4_laur_trace_full_repair5_expand5000.jsonl.zst`

## Dataset

