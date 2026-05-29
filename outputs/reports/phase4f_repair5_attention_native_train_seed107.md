# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 21:31:53

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_seed107/laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- parameter_count: `172170`
- seed: `107`
- epochs: `160`

## Validation Metrics

- attention top1: `0.22866894197952217`
- attention top3: `0.6552901023890785`
- decision accuracy: `0.6034858387799564`
- harmful recall: `0.22654462242562928`
- harmful precision: `0.2531969309462916`
- mean selected delta: `0.01375384603052623`
- selected-vs-additive delta: `0.01375384603052623`
- selected rules: `{'additive_ltm': 194, 'block_heavy': 46, 'block_light': 62, 'commit_heavy': 88, 'decay_090': 2, 'decay_095': 11, 'wait_heavy': 11, 'wait_light': 45}`
- decisions: `{'defer_ltm': 194, 'use_nonadditive': 265}`

## Attention-Native Gate

- validation_top1: `0.22866894197952217` vs `0.35` -> fail
- validation_top3: `0.6552901023890785` vs `0.7` -> fail
- harmful_recall: `0.22654462242562928` vs `0.8` -> fail
- harmful_precision: `0.2531969309462916` vs `0.3` -> fail
- mean_selected_delta: `0.01375384603052623` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.4648648648648649` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.2594594594594595` vs `0.6` -> pass
- anti_escape_mean_delta: `0.05224879271854443` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6416382252559727` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.4226579520697168` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
