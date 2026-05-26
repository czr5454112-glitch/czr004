# Phase4E LAU-LTM Update Dataset Report

Date: 2026-05-26 12:52:14 
Status: passed

## Code State

- branch: `phase4-laur-ltm`
- commit: `9fdb1e9`
- dirty: `tracked-dirty`

## Inputs

- checkpoints: `artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl`
- traces: `artifacts\teacher\laur\traces\phase4_laur_trace_smoke.jsonl`
- probes: `artifacts\teacher\laur\probes\phase4_laur_probe_smoke.jsonl`

## Outputs

- dataset JSONL: `artifacts\teacher\laur\update_labels\phase4_laur_update_dataset_smoke.jsonl`
- summary CSV: `outputs\tables\phase4_laur_update_dataset_smoke_summary.csv`

## Dataset

- samples: 4
- feature_set: `aggregate_checkpoint_v1`
- feature_count: 36
- rule_vocab: `['additive_ltm', 'commit_heavy', 'block_heavy', 'block_light', 'wait_light', 'wait_heavy', 'decay_095', 'decay_090', 'neutral_additive']`
- label_distribution: `{'block_heavy': 1, 'commit_heavy': 1, 'decay_090': 1, 'wait_light': 1}`
- best_rule_histogram: `{'block_heavy': 1, 'commit_heavy': 1, 'decay_090': 1, 'wait_light': 1}`
- non_neutral_checkpoints: 4
- harmful_update_count: 2

## Gate

- dataset_schema_errors: 0
- split_errors: 0
- missing_label_count: 0
- dynamic_rule_vocab: True
- passed: True

## Caveat

This is a Phase4E smoke dataset from the existing Phase4D smoke probes. It validates construction and schema only; it is not large enough for a learned-update performance claim.
