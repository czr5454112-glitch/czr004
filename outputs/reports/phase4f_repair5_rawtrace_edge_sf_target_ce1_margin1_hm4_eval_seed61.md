# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 09:59:40

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_sf_target_ce1_margin1_hm4_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.19112627986348124`
- attention top3: `0.7098976109215017`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.7459954233409611`
- harmful precision: `0.2556862745098039`
- mean selected delta: `0.004457986445089928`
- selected-vs-additive delta: `0.004457986445089928`
- selected rules: `{'additive_ltm': 265, 'block_heavy': 24, 'block_light': 7, 'commit_heavy': 116, 'decay_090': 10, 'decay_095': 8, 'wait_heavy': 7, 'wait_light': 22}`
- decisions: `{'defer_ltm': 265, 'use_nonadditive': 194}`

## Attention-Native Gate

- validation_top1: `0.19112627986348124` vs `0.35` -> fail
- validation_top3: `0.7098976109215017` vs `0.7` -> pass
- harmful_recall: `0.7459954233409611` vs `0.8` -> fail
- harmful_precision: `0.2556862745098039` vs `0.3` -> fail
- mean_selected_delta: `0.004457986445089928` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.2810810810810811` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5945945945945946` vs `0.6` -> pass
- anti_escape_mean_delta: `0.017658009172351705` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.4402730375426621` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5773420479302832` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
