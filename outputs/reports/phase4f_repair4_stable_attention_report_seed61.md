# Phase4F Repair4 Stable-Attention Offline Evaluation

Date: 2026-05-27 15:19:23

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_attention_seed61/laur_stable_attention_v1.pt`
- model_name: `LAU-SetRuleTransformer-v1`
- parameter_count: `171912`
- seed: `61`
- device: `cuda`

## Validation Metrics

- executable/stable top1: `0.38344226579520696`
- executable/stable top3: `0.7211328976034859`
- original top1: `0.27450980392156865`
- original top3: `0.579520697167756`
- harmful recall: `0.9679633867276888`
- harmful precision: `0.20950965824665677`
- mean selected delta: `0.002594354261971723`
- selected-vs-additive delta: `0.002594354261971723`
- fallback rate: `0.7625272331154684`
- pairwise ranking accuracy: `0.553995759041156`
- Spearman q/delta: `0.1367973033991735`

## Phase4F Gate

- validation_top1: `0.38344226579520696` vs `0.35` -> pass
- validation_top3: `0.7211328976034859` vs `0.7` -> pass
- harmful_recall: `0.9679633867276888` vs `0.8` -> pass
- harmful_precision: `0.20950965824665677` vs `0.3` -> fail
- mean_selected_delta: `0.002594354261971723` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Advanced Promotion Gate

- condition_a_positive_delta_two_of_three: `1` vs `>= 2` -> pass
- condition_b_average_delta_positive: `0.002594354261971723` vs `> 0.0` -> pass
- condition_c_top3_not_worse_than_repair3_minus_002: `0.7211328976034859` vs `0.7490631808278867` -> fail
- condition_d_recall_every_seed: `0.9679633867276888` vs `>= 0.80` -> pass

Phase5.5 allowed: `no`

## Boundary

This report is offline-only. Phase5.5 runtime integration is allowed only if the original Phase4F gate and the multi-seed advanced promotion gate both pass.
