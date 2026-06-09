# Phase4F Repair4 Stable-Attention Offline Evaluation

Date: 2026-05-27 15:31:11

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_attention_seed103/laur_stable_attention_v1.pt`
- model_name: `LAU-SetRuleTransformer-v1`
- parameter_count: `171912`
- seed: `103`
- device: `cuda`

## Validation Metrics

- executable/stable top1: `0.39215686274509803`
- executable/stable top3: `0.7429193899782135`
- original top1: `0.2701525054466231`
- original top3: `0.6318082788671024`
- harmful recall: `0.954233409610984`
- harmful precision: `0.2039119804400978`
- mean selected delta: `0.0005753428416190872`
- selected-vs-additive delta: `0.0005753428416190872`
- fallback rate: `0.7494553376906318`
- pairwise ranking accuracy: `0.5695692340958455`
- Spearman q/delta: `0.17156448471233096`

## Phase4F Gate

- validation_top1: `0.39215686274509803` vs `0.35` -> pass
- validation_top3: `0.7429193899782135` vs `0.7` -> pass
- harmful_recall: `0.954233409610984` vs `0.8` -> pass
- harmful_precision: `0.2039119804400978` vs `0.3` -> fail
- mean_selected_delta: `0.0005753428416190872` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Advanced Promotion Gate

- condition_a_positive_delta_two_of_three: `2` vs `>= 2` -> pass
- condition_b_average_delta_positive: `0.0015848485517954052` vs `> 0.0` -> pass
- condition_c_top3_not_worse_than_repair3_minus_002: `0.7320261437908497` vs `0.7490631808278867` -> fail
- condition_d_recall_every_seed: `0.954233409610984` vs `>= 0.80` -> pass

Phase5.5 allowed: `no`

## Boundary

This report is offline-only. Phase5.5 runtime integration is allowed only if the original Phase4F gate and the multi-seed advanced promotion gate both pass.
