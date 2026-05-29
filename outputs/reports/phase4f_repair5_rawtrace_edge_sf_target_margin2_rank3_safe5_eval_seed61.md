# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 10:26:52

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_sf_target_margin2_rank3_safe5_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.22184300341296928`
- attention top3: `0.689419795221843`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.8146453089244852`
- harmful precision: `0.270516717325228`
- mean selected delta: `0.0039328747482869665`
- selected-vs-additive delta: `0.0039328747482869665`
- selected rules: `{'additive_ltm': 201, 'block_heavy': 44, 'block_light': 4, 'commit_heavy': 101, 'decay_090': 29, 'decay_095': 6, 'wait_heavy': 16, 'wait_light': 58}`
- decisions: `{'defer_ltm': 201, 'use_nonadditive': 258}`

## Attention-Native Gate

- validation_top1: `0.22184300341296928` vs `0.35` -> fail
- validation_top3: `0.689419795221843` vs `0.7` -> fail
- harmful_recall: `0.8146453089244852` vs `0.8` -> pass
- harmful_precision: `0.270516717325228` vs `0.3` -> fail
- mean_selected_delta: `0.0039328747482869665` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.3567567567567568` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.43783783783783786` vs `0.6` -> pass
- anti_escape_mean_delta: `0.02175787393299951` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5836177474402731` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.43790849673202614` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
