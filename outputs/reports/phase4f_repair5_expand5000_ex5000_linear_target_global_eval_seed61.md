# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 22:45:03

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_ex5000_linear_target_global_seed61/laur_attention_native_expand5000_ex5000_linear_target_global_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.18633540372670807`
- attention top3: `0.6645962732919255`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.7369826435246996`
- harmful precision: `0.30837988826815643`
- mean selected delta: `-0.00012984526082879396`
- selected-vs-additive delta: `-0.00012984526082879396`
- selected rules: `{'additive_ltm': 350, 'block_heavy': 29, 'block_light': 1, 'commit_heavy': 254, 'decay_090': 4, 'decay_095': 13, 'wait_light': 111}`
- decisions: `{'defer_ltm': 350, 'use_nonadditive': 412}`

## Attention-Native Gate

- validation_top1: `0.18633540372670807` vs `0.35` -> fail
- validation_top3: `0.6645962732919255` vs `0.7` -> fail
- harmful_recall: `0.7369826435246996` vs `0.8` -> fail
- harmful_precision: `0.30837988826815643` vs `0.3` -> pass
- mean_selected_delta: `-0.00012984526082879396` vs `> 0.0` -> fail
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.36774193548387096` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.4483870967741935` vs `0.6` -> pass
- anti_escape_mean_delta: `0.01304037981223101` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5817805383022774` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.45931758530183725` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
