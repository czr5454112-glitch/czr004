# Phase4F Repair5 Attention-Native Offline Evaluation

Date: 2026-05-28 23:39:20

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair5_expand5000_hightoken_ht_mlp_target_global_seed61/laur_attention_native_hightoken_ht_mlp_target_global_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v4`
- seed: `61`
- device: `cuda`

## Validation Metrics

- attention top1: `0.14492753623188406`
- attention top3: `0.6997929606625258`
- validation non-neutral/use_nonadditive: `483`
- harmful recall: `0.7623497997329773`
- harmful precision: `0.31425426527242706`
- mean selected delta: `0.0009267253924302559`
- selected-vs-additive delta: `0.0009267253924302559`
- selected rules: `{'additive_ltm': 444, 'block_heavy': 21, 'block_light': 27, 'commit_heavy': 169, 'decay_090': 24, 'wait_light': 77}`
- decisions: `{'defer_ltm': 444, 'use_nonadditive': 318}`

## Attention-Native Gate

- validation_top1: `0.14492753623188406` vs `0.35` -> fail
- validation_top3: `0.6997929606625258` vs `0.7` -> fail
- harmful_recall: `0.7623497997329773` vs `0.8` -> fail
- harmful_precision: `0.31425426527242706` vs `0.3` -> pass
- mean_selected_delta: `0.0009267253924302559` vs `> 0.0` -> pass
- validation_non_neutral: `483` vs `50` -> pass

Overall: `fail`

## Anti-Escape Gate

- high_margin_opportunity_count: `310` vs `50` -> pass
- high_margin_capture_rate: `0.2838709677419355` vs `0.4` -> fail
- avoidable_additive_or_defer_rate: `0.5516129032258065` vs `0.6` -> pass
- anti_escape_mean_delta: `0.007933625598565483` vs `0.005` -> pass
- opportunity_nonadditive_selection_rate: `0.4616977225672878` vs `0.35` -> pass
- global_additive_or_defer_rate: `0.5826771653543307` vs `0.7` -> pass

Overall: `fail`
Reason: `anti_escape_threshold_failed`

## Boundary

This report is offline-only. Repair5 runtime remains forbidden unless all required original, attention-native, safety, anti-escape, and multi-seed gates pass.
