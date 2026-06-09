# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 23:05:38

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_ex5000_mlp_safety_light_seed61/laur_attention_native_expand5000_ex5000_mlp_safety_light_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.19668737060041408`
- attention top3: `0.6666666666666666`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.822429906542056`
- harmful precision: `0.28439519852262235`
- mean selected delta: `0.0005924399816382926`
- selected-vs-additive delta: `0.0005924399816382926`
- selected rules: `{'additive_ltm': 364, 'block_heavy': 61, 'block_light': 3, 'commit_heavy': 190, 'decay_090': 32, 'decay_095': 39, 'wait_heavy': 6, 'wait_light': 67}`
- decisions: `{'defer_ltm': 364, 'use_nonadditive': 398}`

## Attention-Native Gate

- validation_top1: `0.19668737060041408` vs `0.35` -> fail
- validation_top3: `0.6666666666666666` vs `0.7` -> fail
- harmful_recall: `0.822429906542056` vs `0.8` -> pass
- harmful_precision: `0.28439519852262235` vs `0.3` -> fail
- mean_selected_delta: `0.0005924399816382926` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.2903225806451613` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.4870967741935484` vs `0.6` -> pass
- anti_escape_mean_delta: `0.011581451433142658` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5424430641821946` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.4776902887139108` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
