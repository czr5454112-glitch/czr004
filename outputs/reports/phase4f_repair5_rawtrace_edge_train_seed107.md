# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 23:54:19

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_seed107/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `107`
- epochs: `160`

## Validation Metrics

- attention top1: `0.20477815699658702`
- attention top3: `0.5733788395904437`
- decision accuracy: `0.5816993464052288`
- harmful recall: `0.13958810068649885`
- harmful precision: `0.25738396624472576`
- mean selected delta: `0.015413693654996202`
- selected-vs-additive delta: `0.015413693654996202`
- selected rules: `{'additive_ltm': 174, 'block_heavy': 80, 'block_light': 15, 'commit_heavy': 76, 'decay_090': 33, 'decay_095': 12, 'wait_heavy': 24, 'wait_light': 45}`
- decisions: `{'defer_ltm': 174, 'use_nonadditive': 285}`

## Attention-Native Gate

- validation_top1: `0.20477815699658702` vs `0.35` -> fail
- validation_top3: `0.5733788395904437` vs `0.7` -> fail
- harmful_recall: `0.13958810068649885` vs `0.8` -> fail
- harmful_precision: `0.25738396624472576` vs `0.3` -> fail
- mean_selected_delta: `0.015413693654996202` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.43783783783783786` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.2756756756756757` vs `0.6` -> pass
- anti_escape_mean_delta: `0.04520045039782073` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.658703071672355` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.3790849673202614` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
