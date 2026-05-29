# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-29 10:00:08

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_nextwave_hightoken_attn_mlp_head_candidate_safe_lh5_seed61/laur_attention_native_expand5000_nextwave_hightoken_attn_mlp_head_candidate_safe_lh5_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.17391304347826086`
- attention top3: `0.6728778467908902`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.829105473965287`
- harmful precision: `0.27393030436700483`
- mean selected delta: `0.0016116074447580684`
- selected-vs-additive delta: `0.0016116074447580684`
- selected rules: `{'additive_ltm': 369, 'block_heavy': 58, 'block_light': 15, 'commit_heavy': 181, 'decay_090': 30, 'decay_095': 26, 'wait_light': 83}`
- decisions: `{'defer_ltm': 369, 'use_nonadditive': 393}`

## Attention-Native Gate

- validation_top1: `0.17391304347826086` vs `0.35` -> fail
- validation_top3: `0.6728778467908902` vs `0.7` -> fail
- harmful_recall: `0.829105473965287` vs `0.8` -> pass
- harmful_precision: `0.27393030436700483` vs `0.3` -> fail
- mean_selected_delta: `0.0016116074447580684` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.3387096774193548` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.42258064516129035` vs `0.6` -> pass
- anti_escape_mean_delta: `0.013024309763773877` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5652173913043478` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.484251968503937` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
