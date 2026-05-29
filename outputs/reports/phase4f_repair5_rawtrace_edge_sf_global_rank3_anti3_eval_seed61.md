# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 09:45:00

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_global_rank3_anti3_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.18430034129692832`
- attention top3: `0.689419795221843`
- validation non-neutral/use_nonadditive: `293`
- harmful recall: `0.8146453089244852`
- harmful precision: `0.2751159196290572`
- mean selected delta: `0.0037781165729336165`
- selected-vs-additive delta: `0.0037781165729336165`
- selected rules: `{'additive_ltm': 190, 'block_heavy': 64, 'block_light': 21, 'commit_heavy': 75, 'decay_090': 10, 'decay_095': 53, 'wait_heavy': 15, 'wait_light': 31}`
- decisions: `{'defer_ltm': 190, 'use_nonadditive': 269}`

## Attention-Native Gate

- validation_top1: `0.18430034129692832` vs `0.35` -> fail
- validation_top3: `0.689419795221843` vs `0.7` -> fail
- harmful_recall: `0.8146453089244852` vs `0.8` -> pass
- harmful_precision: `0.2751159196290572` vs `0.3` -> fail
- mean_selected_delta: `0.0037781165729336165` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.3027027027027027` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.3837837837837838` vs `0.6` -> pass
- anti_escape_mean_delta: `0.014165947998203785` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6177474402730375` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.4139433551198257` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
