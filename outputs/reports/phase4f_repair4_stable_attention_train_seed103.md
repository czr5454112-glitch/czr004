# Phase4F Repair4 Stable-Attention Train Report

Date: 2026-05-27 15:30:56

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_attention_seed103/laur_stable_attention_v1.pt`
- model_name: `LAU-SetRuleTransformer-v1`
- parameter_count: `171912`
- seed: `103`
- epochs: `220`
- training_time_sec: `678.0718552628532`

## Validation Metrics

- top1: `0.39215686274509803`
- top3: `0.7429193899782135`
- harmful recall: `0.954233409610984`
- harmful precision: `0.2039119804400978`
- mean selected delta: `0.0005753428416190872`
- fallback rate: `0.7494553376906318`

## Phase4F Gate

- validation_top1: `0.39215686274509803` vs `0.35` -> pass
- validation_top3: `0.7429193899782135` vs `0.7` -> pass
- harmful_recall: `0.954233409610984` vs `0.8` -> pass
- harmful_precision: `0.2039119804400978` vs `0.3` -> fail
- mean_selected_delta: `0.0005753428416190872` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline stable-target attention experiment. No Phase5.5 runtime export or C++ solver integration is implied by this report.
