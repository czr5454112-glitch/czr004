# Phase4F Repair4 Stable-Attention Dataset Report

Date: 2026-05-27 15:06:57

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- checkpoints: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl`
- stable dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair3_stable_targets/update_labels/phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- probes: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- output: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`

## Audit

- samples: `2985`
- schema errors: `0`
- split leakage errors: `0`
- rule vocab count: `8`
- edge truncation rate: `0.0`
- trace truncation rate: `0.0`
- stable labels: `{'block_heavy': 519, 'block_light': 121, 'commit_heavy': 671, 'decay_090': 65, 'decay_095': 82, 'neutral_additive': 1001, 'wait_heavy': 120, 'wait_light': 406}`
- executable labels: `{'additive_ltm': 1001, 'block_heavy': 519, 'block_light': 121, 'commit_heavy': 671, 'decay_090': 65, 'decay_095': 82, 'wait_heavy': 120, 'wait_light': 406}`

## Boundary

This dataset exposes Repair3 stable targets for update-rule selection only. It does not use raw trace payloads, predict agent actions, or change LaCAM*/PIBT semantics.
