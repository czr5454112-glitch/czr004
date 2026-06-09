# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-29 01:14:12

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_followup_ex5000_follow_target_ce2_margin1_hm3_seed61/laur_attention_native_expand5000_followup_ex5000_follow_target_ce2_margin1_hm3_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.16149068322981366`
- attention top3: `0.6790890269151139`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.8651535380507344`
- harmful precision: `0.27586206896551724`
- mean selected delta: `0.0030470683629112336`
- selected-vs-additive delta: `0.0030470683629112336`
- selected rules: `{'additive_ltm': 426, 'block_heavy': 41, 'block_light': 8, 'commit_heavy': 172, 'decay_095': 31, 'wait_heavy': 13, 'wait_light': 71}`
- decisions: `{'defer_ltm': 426, 'use_nonadditive': 336}`

## Attention-Native Gate

- validation_top1: `0.16149068322981366` vs `0.35` -> fail
- validation_top3: `0.6790890269151139` vs `0.7` -> fail
- harmful_recall: `0.8651535380507344` vs `0.8` -> pass
- harmful_precision: `0.27586206896551724` vs `0.3` -> fail
- mean_selected_delta: `0.0030470683629112336` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.2967741935483871` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5612903225806452` vs `0.6` -> pass
- anti_escape_mean_delta: `0.014747601645512823` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.463768115942029` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5590551181102362` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
