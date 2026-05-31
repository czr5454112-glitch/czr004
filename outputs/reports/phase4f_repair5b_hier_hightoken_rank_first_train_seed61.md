# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-31 10:43:34

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5b_hier_hightoken_rank_first_seed61/laur_attention_native_hier_v5.pt`
- model_name: `LAU-HierEdgeTraceTransformer-v5`
- parameter_count: `433388`
- seed: `61`
- epochs: `180`

## Validation Metrics

- attention top1: `0.13457556935817805`
- attention top3: `0.6107660455486542`
- decision accuracy: `0.5236220472440944`
- harmful recall: `0.7049399198931909`
- harmful precision: `0.25882352941176473`
- mean selected delta: `0.0016504043718991392`
- selected-vs-additive delta: `0.0016504043718991392`
- selected rules: `{'additive_ltm': 518, 'block_heavy': 77, 'block_light': 8, 'commit_heavy': 88, 'decay_090': 29, 'decay_095': 24, 'wait_heavy': 1, 'wait_light': 17}`
- decisions: `{'defer_ltm': 518, 'use_nonadditive': 244}`

## Attention-Native Gate

- validation_top1: `0.13457556935817805` vs `0.35` -> fail
- validation_top3: `0.6107660455486542` vs `0.7` -> fail
- harmful_recall: `0.7049399198931909` vs `0.8` -> fail
- harmful_precision: `0.25882352941176473` vs `0.3` -> fail
- mean_selected_delta: `0.0016504043718991392` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.22580645161290322` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.6225806451612903` vs `0.6` -> fail
- anti_escape_mean_delta: `0.008453125058679838` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.37681159420289856` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.6797900262467191` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
