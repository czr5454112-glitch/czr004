# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 20:58:23

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/repair5_debug_seed991/laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- parameter_count: `172170`
- seed: `991`
- epochs: `1`

## Validation Metrics

- attention top1: `0.017064846416382253`
- attention top3: `0.6860068259385665`
- decision accuracy: `0.40522875816993464`
- harmful recall: `0.965675057208238`
- harmful precision: `0.16732751784298175`
- mean selected delta: `0.0005538746414428322`
- selected-vs-additive delta: `0.0005538746414428322`
- selected rules: `{'additive_ltm': 429, 'block_heavy': 23, 'decay_095': 3, 'wait_heavy': 4}`
- decisions: `{'defer_ltm': 429, 'use_nonadditive': 30}`

## Attention-Native Gate

- validation_top1: `0.017064846416382253` vs `0.35` -> fail
- validation_top3: `0.6860068259385665` vs `0.7` -> fail
- harmful_recall: `0.965675057208238` vs `0.8` -> pass
- harmful_precision: `0.16732751784298175` vs `0.3` -> fail
- mean_selected_delta: `0.0005538746414428322` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.06486486486486487` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.9027027027027027` vs `0.6` -> fail
- anti_escape_mean_delta: `0.0016851919700523244` vs `0.005` -> fail
- opportunity_nonadditive_selection_rate: `0.08532423208191127` vs `0.35` -> fail
- global_additive_or_defer_rate: `0.934640522875817` vs `0.7` -> fail

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
