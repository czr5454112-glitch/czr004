# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 10:13:04

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_sf_target_ce2_margin1_hm3_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.14334470989761092`
- attention top3: `0.7064846416382252`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.7871853546910755`
- harmful precision: `0.2778675282714055`
- mean selected delta: `0.002751132135410248`
- selected-vs-additive delta: `0.002751132135410248`
- selected rules: `{'additive_ltm': 262, 'block_heavy': 11, 'block_light': 7, 'commit_heavy': 93, 'decay_090': 9, 'decay_095': 26, 'wait_light': 51}`
- decisions: `{'defer_ltm': 262, 'use_nonadditive': 197}`

## Attention-Native Gate

- validation_top1: `0.14334470989761092` vs `0.35` -> fail
- validation_top3: `0.7064846416382252` vs `0.7` -> pass
- harmful_recall: `0.7871853546910755` vs `0.8` -> fail
- harmful_precision: `0.2778675282714055` vs `0.3` -> fail
- mean_selected_delta: `0.002751132135410248` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.25405405405405407` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5567567567567567` vs `0.6` -> pass
- anti_escape_mean_delta: `0.012868440149763512` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.447098976109215` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5708061002178649` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
