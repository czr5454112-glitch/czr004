# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-27 19:37:43

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `a024b0e`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair5_attention_native\update_labels\phase4_laur_attention_native_dataset.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\repair5_attention_native_smoke_seed61\laur_attention_native_v1.pt`
- model_name: `LAU-SetRuleTransformer-v2`
- parameter_count: `172170`
- seed: `61`
- epochs: `2`

## Validation Metrics

- attention top1: `0.0`
- attention top3: `0.6860068259385665`
- decision accuracy: `0.3616557734204793`
- harmful recall: `1.0`
- harmful precision: `0.1360099595393713`
- mean selected delta: `0.0`
- selected-vs-additive delta: `0.0`
- selected rules: `{'additive_ltm': 459}`
- decisions: `{'defer_ltm': 459}`

## Attention-Native Gate

- validation_top1: `0.0` vs `0.35` -> fail
- validation_top3: `0.6860068259385665` vs `0.7` -> fail
- harmful_recall: `1.0` vs `0.8` -> pass
- harmful_precision: `0.1360099595393713` vs `0.3` -> fail
- mean_selected_delta: `0.0` vs `> 0.0` -> fail
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `185` vs `50` -> pass
- high_margin_capture_rate: `0.0` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `1.0` vs `0.6` -> fail
- anti_escape_mean_delta: `0.0` vs `0.005` -> fail
- opportunity_nonadditive_selection_rate: `0.0` vs `0.35` -> fail
- global_additive_or_defer_rate: `1.0` vs `0.7` -> fail

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
