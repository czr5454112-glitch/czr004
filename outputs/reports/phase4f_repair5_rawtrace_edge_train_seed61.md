# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 23:35:33

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `160`

## Validation Metrics

- attention top1: `0.24573378839590443`
- attention top3: `0.6552901023890785`
- decision accuracy: `0.6056644880174292`
- harmful recall: `0.14645308924485126`
- harmful precision: `0.2397003745318352`
- mean selected delta: `0.012440622753516211`
- selected-vs-additive delta: `0.012440622753516211`
- selected rules: `{'additive_ltm': 155, 'block_heavy': 57, 'block_light': 22, 'commit_heavy': 116, 'decay_090': 2, 'decay_095': 12, 'wait_heavy': 7, 'wait_light': 88}`
- decisions: `{'defer_ltm': 155, 'use_nonadditive': 304}`

## Attention-Native Gate

- validation_top1: `0.24573378839590443` vs `0.35` -> fail
- validation_top3: `0.6552901023890785` vs `0.7` -> fail
- harmful_recall: `0.14645308924485126` vs `0.8` -> fail
- harmful_precision: `0.2397003745318352` vs `0.3` -> fail
- mean_selected_delta: `0.012440622753516211` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.5351351351351351` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.21621621621621623` vs `0.6` -> pass
- anti_escape_mean_delta: `0.06283511793527741` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.7098976109215017` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.33769063180827885` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
