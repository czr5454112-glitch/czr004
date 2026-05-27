# Phase4F Repair4 Stable-Attention Offline Evaluation

Date: 2026-05-27 16:42:44

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_edge_trace_gate_select_seed61/laur_stable_attention_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v3`
- parameter_count: `381992`
- seed: `61`
- device: `cuda`

## Validation Metrics

- executable/stable top1: `0.4008714596949891`
- executable/stable top3: `0.7494553376906318`
- original top1: `0.289760348583878`
- original top3: `0.5816993464052288`
- harmful recall: `0.782608695652174`
- harmful precision: `0.2871536523929471`
- mean selected delta: `0.005733711873736213`
- selected-vs-additive delta: `0.005733711873736213`
- fallback rate: `0.5751633986928104`
- pairwise ranking accuracy: `0.5622920592857472`
- Spearman q/delta: `0.1519784151475033`

## Phase4F Gate

- validation_top1: `0.4008714596949891` vs `0.35` -> pass
- validation_top3: `0.7494553376906318` vs `0.7` -> pass
- harmful_recall: `0.782608695652174` vs `0.8` -> fail
- harmful_precision: `0.2871536523929471` vs `0.3` -> fail
- mean_selected_delta: `0.005733711873736213` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Advanced Promotion Gate

- condition_a_positive_delta_two_of_three: `1` vs `>= 2` -> pass
- condition_b_average_delta_positive: `0.005733711873736213` vs `> 0.0` -> pass
- condition_c_top3_not_worse_than_repair3_minus_002: `0.7494553376906318` vs `0.7490631808278867` -> pass
- condition_d_recall_every_seed: `0.782608695652174` vs `>= 0.80` -> fail

Phase5.5 allowed: `no`

## Boundary

This report is offline-only. Phase5.5 runtime integration is allowed only if the original Phase4F gate and the multi-seed advanced promotion gate both pass.
