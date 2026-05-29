# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-27 21:23:11

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_seed103/laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- seed: `103`
- device: `cuda`

## Validation Metrics

- attention top1: `0.22866894197952217`
- attention top3: `0.6109215017064846`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.2425629290617849`
- harmful precision: `0.3002832861189802`
- mean selected delta: `0.00377316688997132`
- selected-vs-additive delta: `0.00377316688997132`
- selected rules: `{'additive_ltm': 165, 'block_heavy': 74, 'block_light': 32, 'commit_heavy': 94, 'decay_090': 1, 'decay_095': 46, 'wait_heavy': 4, 'wait_light': 43}`
- decisions: `{'defer_ltm': 165, 'use_nonadditive': 294}`

## Attention-Native Gate

- validation_top1: `0.22866894197952217` vs `0.35` -> fail
- validation_top3: `0.6109215017064846` vs `0.7` -> fail
- harmful_recall: `0.2425629290617849` vs `0.8` -> fail
- harmful_precision: `0.3002832861189802` vs `0.3` -> pass
- mean_selected_delta: `0.00377316688997132` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.4810810810810811` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.1945945945945946` vs `0.6` -> pass
- anti_escape_mean_delta: `0.036741190777588965` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6996587030716723` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.35947712418300654` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
