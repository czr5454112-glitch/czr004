# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-28 09:32:08

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_global_pair_rank2_anti2_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `200`

## Validation Metrics

- attention top1: `0.18771331058020477`
- attention top3: `0.689419795221843`
- decision accuracy: `0.49455337690631807`
- harmful recall: `0.7459954233409611`
- harmful precision: `0.2900355871886121`
- mean selected delta: `0.00419224785535776`
- selected-vs-additive delta: `0.00419224785535776`
- selected rules: `{'additive_ltm': 242, 'block_heavy': 18, 'block_light': 10, 'commit_heavy': 126, 'decay_095': 25, 'wait_heavy': 12, 'wait_light': 26}`
- decisions: `{'defer_ltm': 242, 'use_nonadditive': 217}`

## Attention-Native Gate

- validation_top1: `0.18771331058020477` vs `0.35` -> fail
- validation_top3: `0.689419795221843` vs `0.7` -> fail
- harmful_recall: `0.7459954233409611` vs `0.8` -> fail
- harmful_precision: `0.2900355871886121` vs `0.3` -> fail
- mean_selected_delta: `0.00419224785535776` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.2594594594594595` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5621621621621622` vs `0.6` -> pass
- anti_escape_mean_delta: `0.01607638617055497` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.47440273037542663` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5272331154684096` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
