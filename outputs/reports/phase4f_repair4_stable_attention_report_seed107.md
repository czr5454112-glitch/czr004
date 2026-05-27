# Phase4F Repair4 Stable-Attention Offline Evaluation

Date: 2026-05-27 15:43:01

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_attention_seed107/laur_stable_attention_v1.pt`
- model_name: `LAU-SetRuleTransformer-v1`
- parameter_count: `171912`
- seed: `107`
- device: `cuda`

## Validation Metrics

- executable/stable top1: `0.39651416122004357`
- executable/stable top3: `0.7581699346405228`
- original top1: `0.28540305010893247`
- original top3: `0.6100217864923747`
- harmful recall: `0.9862700228832952`
- harmful precision: `0.18450342465753425`
- mean selected delta: `0.0024942630822401765`
- selected-vs-additive delta: `0.0024942630822401765`
- fallback rate: `0.8191721132897604`
- pairwise ranking accuracy: `0.5627024579205118`
- Spearman q/delta: `0.1599128315563622`

## Phase4F Gate

- validation_top1: `0.39651416122004357` vs `0.35` -> pass
- validation_top3: `0.7581699346405228` vs `0.7` -> pass
- harmful_recall: `0.9862700228832952` vs `0.8` -> pass
- harmful_precision: `0.18450342465753425` vs `0.3` -> fail
- mean_selected_delta: `0.0024942630822401765` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Advanced Promotion Gate

- condition_a_positive_delta_two_of_three: `3` vs `>= 2` -> pass
- condition_b_average_delta_positive: `0.0018879867286103289` vs `> 0.0` -> pass
- condition_c_top3_not_worse_than_repair3_minus_002: `0.7407407407407408` vs `0.7490631808278867` -> fail
- condition_d_recall_every_seed: `0.954233409610984` vs `>= 0.80` -> pass

Phase5.5 allowed: `no`

## Boundary

This report is offline-only. Phase5.5 runtime integration is allowed only if the original Phase4F gate and the multi-seed advanced promotion gate both pass.
