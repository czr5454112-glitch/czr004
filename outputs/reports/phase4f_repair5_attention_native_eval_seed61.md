# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-27 21:14:06

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_seed61/laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.2150170648464164`
- attention top3: `0.5767918088737202`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.2814645308924485`
- harmful precision: `0.26170212765957446`
- mean selected delta: `0.00990702449332689`
- selected-vs-additive delta: `0.00990702449332689`
- selected rules: `{'additive_ltm': 154, 'block_heavy': 50, 'block_light': 23, 'commit_heavy': 112, 'decay_090': 7, 'decay_095': 21, 'wait_heavy': 17, 'wait_light': 75}`
- decisions: `{'defer_ltm': 154, 'use_nonadditive': 305}`

## Attention-Native Gate

- validation_top1: `0.2150170648464164` vs `0.35` -> fail
- validation_top3: `0.5767918088737202` vs `0.7` -> fail
- harmful_recall: `0.2814645308924485` vs `0.8` -> fail
- harmful_precision: `0.26170212765957446` vs `0.3` -> fail
- mean_selected_delta: `0.00990702449332689` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.4648648648648649` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.2` vs `0.6` -> pass
- anti_escape_mean_delta: `0.04699217708345323` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6962457337883959` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.3355119825708061` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
