# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-29 00:32:53

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_followup_ex5000_follow_pair_focal_m035_lh4_seed61/laur_attention_native_expand5000_followup_ex5000_follow_pair_focal_m035_lh4_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.12836438923395446`
- attention top3: `0.6832298136645962`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.8050734312416555`
- harmful precision: `0.2750912408759124`
- mean selected delta: `0.0020923863782431914`
- selected-vs-additive delta: `0.0020923863782431914`
- selected rules: `{'additive_ltm': 483, 'block_heavy': 37, 'block_light': 19, 'commit_heavy': 105, 'decay_090': 23, 'decay_095': 35, 'wait_heavy': 2, 'wait_light': 58}`
- decisions: `{'defer_ltm': 483, 'use_nonadditive': 279}`

## Attention-Native Gate

- validation_top1: `0.12836438923395446` vs `0.35` -> fail
- validation_top3: `0.6832298136645962` vs `0.7` -> fail
- harmful_recall: `0.8050734312416555` vs `0.8` -> pass
- harmful_precision: `0.2750912408759124` vs `0.3` -> fail
- mean_selected_delta: `0.0020923863782431914` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.18064516129032257` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.6161290322580645` vs `0.6` -> fail
- anti_escape_mean_delta: `0.00831967929851638` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.41821946169772256` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.6338582677165354` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
