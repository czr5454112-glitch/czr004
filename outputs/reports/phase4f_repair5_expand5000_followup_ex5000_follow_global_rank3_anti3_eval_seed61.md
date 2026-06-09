# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-29 00:53:40

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_followup_ex5000_follow_global_rank3_anti3_seed61/laur_attention_native_expand5000_followup_ex5000_follow_global_rank3_anti3_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.18426501035196688`
- attention top3: `0.6645962732919255`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.7476635514018691`
- harmful precision: `0.30684931506849317`
- mean selected delta: `0.0019174720854631903`
- selected-vs-additive delta: `0.0019174720854631903`
- selected rules: `{'additive_ltm': 353, 'block_heavy': 108, 'commit_heavy': 172, 'decay_090': 6, 'decay_095': 53, 'wait_light': 70}`
- decisions: `{'defer_ltm': 353, 'use_nonadditive': 409}`

## Attention-Native Gate

- validation_top1: `0.18426501035196688` vs `0.35` -> fail
- validation_top3: `0.6645962732919255` vs `0.7` -> fail
- harmful_recall: `0.7476635514018691` vs `0.8` -> fail
- harmful_precision: `0.30684931506849317` vs `0.3` -> pass
- mean_selected_delta: `0.0019174720854631903` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.3419354838709677` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.4129032258064516` vs `0.6` -> pass
- anti_escape_mean_delta: `0.013207061571385138` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5859213250517599` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.463254593175853` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
