# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-29 10:40:02

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_nextwave_hightoken_attn_linear_head_candidate_safe_lh6_seed61/laur_attention_native_expand5000_nextwave_hightoken_attn_linear_head_candidate_safe_lh6_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `382378`
- seed: `61`
- epochs: `240`

## Validation Metrics

- attention top1: `0.16770186335403728`
- attention top3: `0.6645962732919255`
- decision accuracy: `0.5301837270341208`
- harmful recall: `0.9052069425901201`
- harmful precision: `0.2634032634032634`
- mean selected delta: `0.003218942249353385`
- selected-vs-additive delta: `0.003218942249353385`
- selected rules: `{'additive_ltm': 415, 'block_heavy': 37, 'block_light': 32, 'commit_heavy': 193, 'decay_090': 65, 'decay_095': 3, 'wait_heavy': 5, 'wait_light': 12}`
- decisions: `{'defer_ltm': 415, 'use_nonadditive': 347}`

## Attention-Native Gate

- validation_top1: `0.16770186335403728` vs `0.35` -> fail
- validation_top3: `0.6645962732919255` vs `0.7` -> fail
- harmful_recall: `0.9052069425901201` vs `0.8` -> pass
- harmful_precision: `0.2634032634032634` vs `0.3` -> fail
- mean_selected_delta: `0.003218942249353385` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.25483870967741934` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5290322580645161` vs `0.6` -> pass
- anti_escape_mean_delta: `0.008175908406188549` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.4886128364389234` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5446194225721784` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
