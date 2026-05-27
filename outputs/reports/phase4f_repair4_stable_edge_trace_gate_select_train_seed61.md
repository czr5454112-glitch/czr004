# Phase4F Repair4 Stable-Attention Train Report

Date: 2026-05-27 16:42:25

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- dataset: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair4_stable_attention/update_labels/phase4_laur_stable_attention_dataset.jsonl`
- model_path: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/models/laur_ltm/full_repair4_stable_edge_trace_gate_select_seed61/laur_stable_attention_v1.pt`
- model_name: `LAU-EdgeTraceTransformer-v3`
- parameter_count: `381992`
- seed: `61`
- epochs: `220`
- training_time_sec: `711.6804232783616`

## Validation Metrics

- top1: `0.4008714596949891`
- top3: `0.7494553376906318`
- harmful recall: `0.782608695652174`
- harmful precision: `0.2871536523929471`
- mean selected delta: `0.005733711873736213`
- fallback rate: `0.5751633986928104`

## Phase4F Gate

- validation_top1: `0.4008714596949891` vs `0.35` -> pass
- validation_top3: `0.7494553376906318` vs `0.7` -> pass
- harmful_recall: `0.782608695652174` vs `0.8` -> fail
- harmful_precision: `0.2871536523929471` vs `0.3` -> fail
- mean_selected_delta: `0.005733711873736213` vs `> 0.0` -> pass
- validation_non_neutral: `293` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline stable-target attention experiment. No Phase5.5 runtime export or C++ solver integration is implied by this report.
