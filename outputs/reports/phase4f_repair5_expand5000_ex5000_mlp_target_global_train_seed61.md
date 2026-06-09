# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-28 22:24:31

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_ex5000_mlp_target_global_seed61/laur_attention_native_expand5000_ex5000_mlp_target_global_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `420458`
- seed: `61`
- epochs: `200`

## Validation Metrics

- attention top1: `0.21325051759834368`
- attention top3: `0.6625258799171843`
- decision accuracy: `0.5879265091863517`
- harmful recall: `0.6769025367156208`
- harmful precision: `0.3202779532533165`
- mean selected delta: `0.006214684332570314`
- selected-vs-additive delta: `0.006214684332570314`
- selected rules: `{'additive_ltm': 329, 'block_heavy': 82, 'block_light': 6, 'commit_heavy': 162, 'decay_090': 45, 'decay_095': 3, 'wait_heavy': 8, 'wait_light': 127}`
- decisions: `{'defer_ltm': 329, 'use_nonadditive': 433}`

## Attention-Native Gate

- validation_top1: `0.21325051759834368` vs `0.35` -> fail
- validation_top3: `0.6625258799171843` vs `0.7` -> fail
- harmful_recall: `0.6769025367156208` vs `0.8` -> fail
- harmful_precision: `0.3202779532533165` vs `0.3` -> pass
- mean_selected_delta: `0.006214684332570314` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.38064516129032255` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.3741935483870968` vs `0.6` -> pass
- anti_escape_mean_delta: `0.026818417316147942` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6231884057971014` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.431758530183727` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
