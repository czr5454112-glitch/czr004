# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 09:20:13

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.23208191126279865`
- attention top3: `0.7064846416382252`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.5766590389016019`
- harmful precision: `0.31343283582089554`
- mean selected delta: `0.002122196951869791`
- selected-vs-additive delta: `0.002122196951869791`
- selected rules: `{'additive_ltm': 212, 'block_heavy': 18, 'block_light': 3, 'commit_heavy': 136, 'decay_090': 6, 'decay_095': 10, 'wait_heavy': 7, 'wait_light': 67}`
- decisions: `{'defer_ltm': 212, 'use_nonadditive': 247}`

## Attention-Native Gate

- validation_top1: `0.23208191126279865` vs `0.35` -> fail
- validation_top3: `0.7064846416382252` vs `0.7` -> pass
- harmful_recall: `0.5766590389016019` vs `0.8` -> fail
- harmful_precision: `0.31343283582089554` vs `0.3` -> pass
- mean_selected_delta: `0.002122196951869791` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.43783783783783786` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.32972972972972975` vs `0.6` -> pass
- anti_escape_mean_delta: `0.034749479796327344` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5938566552901023` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.46187363834422657` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
