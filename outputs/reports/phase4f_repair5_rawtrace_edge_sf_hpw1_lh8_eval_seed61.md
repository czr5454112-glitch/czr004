# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 08:12:45

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_hpw1_lh8_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.21160409556313994`
- attention top3: `0.5938566552901023`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.13272311212814644`
- harmful precision: `0.3372093023255814`
- mean selected delta: `0.013572036079291059`
- selected-vs-additive delta: `0.013572036079291059`
- selected rules: `{'additive_ltm': 183, 'block_heavy': 71, 'block_light': 41, 'commit_heavy': 71, 'decay_090': 8, 'decay_095': 15, 'wait_heavy': 14, 'wait_light': 56}`
- decisions: `{'defer_ltm': 183, 'use_nonadditive': 276}`

## Attention-Native Gate

- validation_top1: `0.21160409556313994` vs `0.35` -> fail
- validation_top3: `0.5938566552901023` vs `0.7` -> fail
- harmful_recall: `0.13272311212814644` vs `0.8` -> fail
- harmful_precision: `0.3372093023255814` vs `0.3` -> pass
- mean_selected_delta: `0.013572036079291059` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.4648648648648649` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.2702702702702703` vs `0.6` -> pass
- anti_escape_mean_delta: `0.05633194500537319` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6757679180887372` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.39869281045751637` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
