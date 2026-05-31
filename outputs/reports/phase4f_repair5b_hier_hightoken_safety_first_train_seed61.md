# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-31 11:20:55

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5b_hier_hightoken_safety_first_seed61/laur_attention_native_hier_v5.pt`
- model_name: `LAU-HierEdgeTraceTransformer-v5`
- parameter_count: `433388`
- seed: `61`
- epochs: `180`

## Validation Metrics

- attention top1: `0.14078674948240166`
- attention top3: `0.6666666666666666`
- decision accuracy: `0.5236220472440944`
- harmful recall: `0.6128170894526035`
- harmful precision: `0.24757281553398058`
- mean selected delta: `-0.0037863788579064537`
- selected-vs-additive delta: `-0.0037863788579064537`
- selected rules: `{'additive_ltm': 556, 'block_heavy': 40, 'block_light': 4, 'commit_heavy': 98, 'decay_090': 13, 'decay_095': 4, 'wait_heavy': 12, 'wait_light': 35}`
- decisions: `{'defer_ltm': 556, 'use_nonadditive': 206}`

## Attention-Native Gate

- validation_top1: `0.14078674948240166` vs `0.35` -> fail
- validation_top3: `0.6666666666666666` vs `0.7` -> fail
- harmful_recall: `0.6128170894526035` vs `0.8` -> fail
- harmful_precision: `0.24757281553398058` vs `0.3` -> fail
- mean_selected_delta: `-0.0037863788579064537` vs `> 0.0` -> fail
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.2645161290322581` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.6` vs `0.6` -> pass
- anti_escape_mean_delta: `0.0032037713929452096` vs `0.005` -> fail
- opportunity_nonadditive_selection_rate: `0.33747412008281574` vs `0.35` -> fail
- global_additive_or_defer_rate: `0.7296587926509186` vs `0.7` -> fail

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
