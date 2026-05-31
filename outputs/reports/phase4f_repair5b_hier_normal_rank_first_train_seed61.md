# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-31 10:08:06

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl.zst`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5b_hier_normal_rank_first_seed61/laur_attention_native_hier_v5.pt`
- model_name: `LAU-HierEdgeTraceTransformer-v5`
- parameter_count: `433388`
- seed: `61`
- epochs: `180`

## Validation Metrics

- attention top1: `0.07453416149068323`
- attention top3: `0.6314699792960663`
- decision accuracy: `0.48031496062992124`
- harmful recall: `0.5994659546061415`
- harmful precision: `0.2816813048933501`
- mean selected delta: `0.0026858692806573585`
- selected-vs-additive delta: `0.0026858692806573585`
- selected rules: `{'additive_ltm': 579, 'block_heavy': 24, 'block_light': 17, 'commit_heavy': 69, 'decay_090': 22, 'decay_095': 9, 'wait_heavy': 26, 'wait_light': 16}`
- decisions: `{'defer_ltm': 579, 'use_nonadditive': 183}`

## Attention-Native Gate

- validation_top1: `0.07453416149068323` vs `0.35` -> fail
- validation_top3: `0.6314699792960663` vs `0.7` -> fail
- harmful_recall: `0.5994659546061415` vs `0.8` -> fail
- harmful_precision: `0.2816813048933501` vs `0.3` -> fail
- mean_selected_delta: `0.0026858692806573585` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.1935483870967742` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.667741935483871` vs `0.6` -> fail
- anti_escape_mean_delta: `0.013334381332515936` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.2795031055900621` vs `0.35` -> fail
- global_additive_or_defer_rate: `0.7598425196850394` vs `0.7` -> fail

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
