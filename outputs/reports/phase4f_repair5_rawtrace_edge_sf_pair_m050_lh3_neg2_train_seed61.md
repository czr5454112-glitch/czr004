# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-28 09:07:16

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_pair_m050_lh3_neg2_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `180`

## Validation Metrics

- attention top1: `0.15358361774744028`
- attention top3: `0.6825938566552902`
- decision accuracy: `0.5403050108932462`
- harmful recall: `0.7437070938215103`
- harmful precision: `0.29491833030852993`
- mean selected delta: `0.014323520870012856`
- selected-vs-additive delta: `0.014323520870012856`
- selected rules: `{'additive_ltm': 237, 'block_heavy': 63, 'commit_heavy': 71, 'decay_090': 15, 'decay_095': 24, 'wait_heavy': 12, 'wait_light': 37}`
- decisions: `{'defer_ltm': 237, 'use_nonadditive': 222}`

## Attention-Native Gate

- validation_top1: `0.15358361774744028` vs `0.35` -> fail
- validation_top3: `0.6825938566552902` vs `0.7` -> fail
- harmful_recall: `0.7437070938215103` vs `0.8` -> fail
- harmful_precision: `0.29491833030852993` vs `0.3` -> fail
- mean_selected_delta: `0.014323520870012856` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.3027027027027027` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.4594594594594595` vs `0.6` -> pass
- anti_escape_mean_delta: `0.05391317348717691` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5187713310580204` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5163398692810458` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
