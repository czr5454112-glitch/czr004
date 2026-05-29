# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-28 08:42:57

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_pair_focal_m035_lh4_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `180`

## Validation Metrics

- attention top1: `0.18088737201365188`
- attention top3: `0.6621160409556314`
- decision accuracy: `0.55119825708061`
- harmful recall: `0.816933638443936`
- harmful precision: `0.281767955801105`
- mean selected delta: `0.005700274521320026`
- selected-vs-additive delta: `0.005700274521320026`
- selected rules: `{'additive_ltm': 216, 'block_heavy': 36, 'block_light': 5, 'commit_heavy': 97, 'decay_090': 24, 'decay_095': 39, 'wait_heavy': 26, 'wait_light': 16}`
- decisions: `{'defer_ltm': 216, 'use_nonadditive': 243}`

## Attention-Native Gate

- validation_top1: `0.18088737201365188` vs `0.35` -> fail
- validation_top3: `0.6621160409556314` vs `0.7` -> fail
- harmful_recall: `0.816933638443936` vs `0.8` -> pass
- harmful_precision: `0.281767955801105` vs `0.3` -> fail
- mean_selected_delta: `0.005700274521320026` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.2756756756756757` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.43243243243243246` vs `0.6` -> pass
- anti_escape_mean_delta: `0.013605305297136973` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5631399317406144` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.47058823529411764` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
