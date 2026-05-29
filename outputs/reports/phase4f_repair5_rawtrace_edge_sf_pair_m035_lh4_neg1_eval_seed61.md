# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 08:56:32

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_pair_m035_lh4_neg1_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.20819112627986347`
- attention top3: `0.6416382252559727`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.6842105263157895`
- harmful precision: `0.31145833333333334`
- mean selected delta: `0.008596097071324617`
- selected-vs-additive delta: `0.008596097071324617`
- selected rules: `{'additive_ltm': 186, 'block_heavy': 33, 'block_light': 3, 'commit_heavy': 118, 'decay_090': 17, 'decay_095': 49, 'wait_heavy': 12, 'wait_light': 41}`
- decisions: `{'defer_ltm': 186, 'use_nonadditive': 273}`

## Attention-Native Gate

- validation_top1: `0.20819112627986347` vs `0.35` -> fail
- validation_top3: `0.6416382252559727` vs `0.7` -> fail
- harmful_recall: `0.6842105263157895` vs `0.8` -> fail
- harmful_precision: `0.31145833333333334` vs `0.3` -> pass
- mean_selected_delta: `0.008596097071324617` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.33513513513513515` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.3567567567567568` vs `0.6` -> pass
- anti_escape_mean_delta: `0.026065629336783788` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6484641638225256` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.40522875816993464` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
