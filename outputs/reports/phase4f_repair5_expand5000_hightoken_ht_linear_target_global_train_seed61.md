# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-29 00:11:38

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_hightoken_ht_linear_target_global_seed61/laur_attention_native_hightoken_ht_linear_target_global_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `200`

## Validation Metrics

- attention top1: `0.17391304347826086`
- attention top3: `0.6687370600414079`
- decision accuracy: `0.5538057742782152`
- harmful recall: `0.8050734312416555`
- harmful precision: `0.30059820538384846`
- mean selected delta: `0.0028174332139860106`
- selected-vs-additive delta: `0.0028174332139860106`
- selected rules: `{'additive_ltm': 391, 'block_heavy': 19, 'block_light': 13, 'commit_heavy': 197, 'decay_090': 8, 'decay_095': 72, 'wait_heavy': 1, 'wait_light': 61}`
- decisions: `{'defer_ltm': 391, 'use_nonadditive': 371}`

## Attention-Native Gate

- validation_top1: `0.17391304347826086` vs `0.35` -> fail
- validation_top3: `0.6687370600414079` vs `0.7` -> fail
- harmful_recall: `0.8050734312416555` vs `0.8` -> pass
- harmful_precision: `0.30059820538384846` vs `0.3` -> pass
- mean_selected_delta: `0.0028174332139860106` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.29354838709677417` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.46774193548387094` vs `0.6` -> pass
- anti_escape_mean_delta: `0.008058983109689968` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5320910973084886` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5131233595800525` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
