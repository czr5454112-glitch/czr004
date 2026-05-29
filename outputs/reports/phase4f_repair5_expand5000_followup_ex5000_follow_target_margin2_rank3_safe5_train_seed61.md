# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-29 01:34:02

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_followup_ex5000_follow_target_margin2_rank3_safe5_seed61/laur_attention_native_expand5000_followup_ex5000_follow_target_margin2_rank3_safe5_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `420458`
- seed: `61`
- epochs: `200`

## Validation Metrics

- attention top1: `0.17184265010351968`
- attention top3: `0.6749482401656315`
- decision accuracy: `0.5538057742782152`
- harmful recall: `0.7303070761014686`
- harmful precision: `0.31328751431844215`
- mean selected delta: `0.000446387115559479`
- selected-vs-additive delta: `0.000446387115559479`
- selected rules: `{'additive_ltm': 403, 'block_heavy': 39, 'block_light': 2, 'commit_heavy': 163, 'decay_090': 14, 'decay_095': 27, 'wait_light': 114}`
- decisions: `{'defer_ltm': 403, 'use_nonadditive': 359}`

## Attention-Native Gate

- validation_top1: `0.17184265010351968` vs `0.35` -> fail
- validation_top3: `0.6749482401656315` vs `0.7` -> fail
- harmful_recall: `0.7303070761014686` vs `0.8` -> fail
- harmful_precision: `0.31328751431844215` vs `0.3` -> pass
- mean_selected_delta: `0.000446387115559479` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.33548387096774196` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.47096774193548385` vs `0.6` -> pass
- anti_escape_mean_delta: `0.012829270416048236` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.5196687370600414` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5288713910761155` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
