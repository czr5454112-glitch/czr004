# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 08:31:11

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_hpw1_lh12_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.24232081911262798`
- attention top3: `0.6552901023890785`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.07551487414187644`
- harmful precision: `0.308411214953271`
- mean selected delta: `0.005414136049950716`
- selected-vs-additive delta: `0.005414136049950716`
- selected rules: `{'additive_ltm': 108, 'block_heavy': 83, 'block_light': 40, 'commit_heavy': 116, 'decay_090': 15, 'decay_095': 11, 'wait_heavy': 8, 'wait_light': 78}`
- decisions: `{'defer_ltm': 108, 'use_nonadditive': 351}`

## Attention-Native Gate

- validation_top1: `0.24232081911262798` vs `0.35` -> fail
- validation_top3: `0.6552901023890785` vs `0.7` -> fail
- harmful_recall: `0.07551487414187644` vs `0.8` -> fail
- harmful_precision: `0.308411214953271` vs `0.3` -> pass
- mean_selected_delta: `0.005414136049950716` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.5513513513513514` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.10810810810810811` vs `0.6` -> pass
- anti_escape_mean_delta: `0.04511697872451627` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.8156996587030717` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.23529411764705882` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
