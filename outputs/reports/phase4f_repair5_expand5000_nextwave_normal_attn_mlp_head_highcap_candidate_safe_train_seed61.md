# Phase4F Repair5 Attention-Native Train Report

Date: 2026-05-29 11:09:16

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_nextwave_normal_attn_mlp_head_highcap_candidate_safe_seed61/laur_attention_native_expand5000_nextwave_normal_attn_mlp_head_highcap_candidate_safe_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- parameter_count: `947466`
- seed: `61`
- epochs: `240`

## Validation Metrics

- attention top1: `0.16563146997929606`
- attention top3: `0.6997929606625258`
- decision accuracy: `0.5236220472440944`
- harmful recall: `0.753004005340454`
- harmful precision: `0.29147286821705426`
- mean selected delta: `0.004326666818644141`
- selected-vs-additive delta: `0.004326666818644141`
- selected rules: `{'additive_ltm': 448, 'block_heavy': 68, 'block_light': 6, 'commit_heavy': 131, 'decay_090': 11, 'wait_heavy': 12, 'wait_light': 86}`
- decisions: `{'defer_ltm': 448, 'use_nonadditive': 314}`

## Attention-Native Gate

- validation_top1: `0.16563146997929606` vs `0.35` -> fail
- validation_top3: `0.6997929606625258` vs `0.7` -> fail
- harmful_recall: `0.753004005340454` vs `0.8` -> fail
- harmful_precision: `0.29147286821705426` vs `0.3` -> fail
- mean_selected_delta: `0.004326666818644141` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.3161290322580645` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5290322580645161` vs `0.6` -> pass
- anti_escape_mean_delta: `0.019439847211877928` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.4492753623188406` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5879265091863517` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.
