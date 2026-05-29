# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 23:45:01

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/phase4_laur_attention_native_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_attention_native_rawtrace_edge_seed103/laur_attention_native_rawtrace_edge_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `103`
- epochs: `160`

## Validation Metrics

- attention top1: `0.23890784982935154`
- attention top3: `0.6143344709897611`
- decision accuracy: `0.6078431372549019`
- harmful recall: `0.37528604118993136`
- harmful precision: `0.340956340956341`
- mean selected delta: `0.02061652308881321`
- selected-vs-additive delta: `0.02061652308881321`
- selected rules: `{'additive_ltm': 148, 'block_heavy': 66, 'block_light': 17, 'commit_heavy': 149, 'decay_090': 3, 'decay_095': 7, 'wait_heavy': 17, 'wait_light': 52}`
- decisions: `{'defer_ltm': 148, 'use_nonadditive': 311}`

## Attention-Native Gate

- validation_top1: `0.23890784982935154` vs `0.35` -> fail
- validation_top3: `0.6143344709897611` vs `0.7` -> fail
- harmful_recall: `0.37528604118993136` vs `0.8` -> fail
- harmful_precision: `0.340956340956341` vs `0.3` -> pass
- mean_selected_delta: `0.02061652308881321` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.4918918918918919` vs `0.4` -> pass
- avoidable_additive_or_defer_rate: `0.23783783783783785` vs `0.6` -> pass
- anti_escape_mean_delta: `0.06727594623294492` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.7235494880546075` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.3224400871459695` vs `0.7` -> pass

Overall: `pass`
Reason: `passed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
