# Phase4F Repair4 Stable-Attention Train Report

Date: 2026-05-27 16:11:27

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_edge_trace_seed61/laur_stable_attention_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v3`
- parameter_count: `381992`
- seed: `61`
- epochs: `220`
- training_time_sec: `706.552422253415`

## Validation Metrics

- top1: `0.39433551198257083`
- top3: `0.7494553376906318`
- harmful recall: `0.9588100686498856`
- harmful precision: `0.21788871554862194`
- mean selected delta: `0.003256466287066279`
- fallback rate: `0.6775599128540305`

## Phase4F Gate

- validation_top1: `0.39433551198257083` vs `0.35` -> pass
- validation_top3: `0.7494553376906318` vs `0.7` -> pass
- harmful_recall: `0.9588100686498856` vs `0.8` -> pass
- harmful_precision: `0.21788871554862194` vs `0.3` -> fail
- mean_selected_delta: `0.003256466287066279` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline stable-target attention experiment. No Phase5.5 runtime export or C++ solver integration is implied by this report.
