# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-28 08:21:41

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_rawtrace_edge_sf_hpw2_lh8_seed61/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `160`

## Validation Metrics

- attention top1: `0.19112627986348124`
- attention top3: `0.6450511945392492`
- decision accuracy: `0.5838779956427015`
- harmful recall: `0.2311212814645309`
- harmful precision: `0.2936046511627907`
- mean selected delta: `0.01067540326608789`
- selected-vs-additive delta: `0.01067540326608789`
- selected rules: `{'additive_ltm': 175, 'block_heavy': 61, 'block_light': 15, 'commit_heavy': 108, 'decay_090': 7, 'decay_095': 8, 'wait_heavy': 31, 'wait_light': 54}`
- decisions: `{'defer_ltm': 175, 'use_nonadditive': 284}`

## Attention-Native Gate

- validation_top1: `0.19112627986348124` vs `0.35` -> fail
- validation_top3: `0.6450511945392492` vs `0.7` -> fail
- harmful_recall: `0.2311212814645309` vs `0.8` -> fail
- harmful_precision: `0.2936046511627907` vs `0.3` -> fail
- mean_selected_delta: `0.01067540326608789` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.5081081081081081` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.22702702702702704` vs `0.6` -> pass
- anti_escape_mean_delta: `0.05764449994726013` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.658703071672355` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.3812636165577342` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
