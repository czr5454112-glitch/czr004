# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 19:50:57

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `a024b0e`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair5_attention_native\update_labels\phase4_laur_attention_native_dataset.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\repair5_attention_native_mid2_seed61\laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- parameter_count: `172170`
- seed: `61`
- epochs: `40`

## Validation Metrics

- attention top1: `0.21160409556313994`
- attention top3: `0.6689419795221843`
- decision accuracy: `0.5490196078431373`
- harmful recall: `0.7688787185354691`
- harmful precision: `0.2847457627118644`
- mean selected delta: `0.0017283597122786584`
- selected-vs-additive delta: `0.0017283597122786584`
- selected rules: `{'additive_ltm': 185, 'block_heavy': 66, 'block_light': 4, 'commit_heavy': 114, 'decay_090': 8, 'decay_095': 50, 'wait_heavy': 13, 'wait_light': 19}`
- decisions: `{'defer_ltm': 185, 'use_nonadditive': 274}`

## Attention-Native Gate

- validation_top1: `0.21160409556313994` vs `0.35` -> fail
- validation_top3: `0.6689419795221843` vs `0.7` -> fail
- harmful_recall: `0.7688787185354691` vs `0.8` -> fail
- harmful_precision: `0.2847457627118644` vs `0.3` -> fail
- mean_selected_delta: `0.0017283597122786584` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.35135135135135137` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.3837837837837838` vs `0.6` -> pass
- anti_escape_mean_delta: `0.01614682523744518` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.6143344709897611` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.40305010893246185` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
