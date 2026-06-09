# Phase4F LAUR Failure Diagnostics

Date: 2026-05-26

## Scope

This report is a P0 diagnostic pass over the completed Phase4F full run. It does not lower the Phase4F gate, does not change labels, and does not advance the model into Phase5 learned runtime.

## Inputs

- dataset: `artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl`
- probes: `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- offline eval CSV: `outputs/tables/phase4_laur_ltm_offline_eval_full_repair1.csv`
- offline eval summary: `outputs/reports/phase4_laur_ltm_offline_eval_full_repair1_summary.json`
- dataset rows: `2985`
- probe rows: `24216`
- eval rows: `2985`
- eval gate script passed operationally: `True`

## Gate Recap

| split | samples | exact top1 | exact top3 | family top1 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.4279 | 0.7672 | 0.4513 | 0.9960 | 0.5308 | 0.0352 |
| validation | 459 | 0.3072 | 0.6427 | 0.3442 | 0.9538 | 0.4015 | 0.0110 |
| all | 2985 | 0.4094 | 0.7481 | 0.4348 | 0.9909 | 0.5116 | 0.0315 |

Family top1 collapses `block_*`, `wait_*`, `decay_*`, `commit_*`, and additive/neutral variants. It is diagnostic only; the Phase4F gate still uses exact rule top1/top3.

## Label Margins

- Validation checkpoints with best-vs-second probe margin <= 0.005: `245` / `459` (53.38%).
- Validation checkpoints with margin <= 0.010: `324` / `459` (70.59%).
- All checkpoints with margin <= 0.005: `1407` / `2985` (47.14%).
- Near ties make hard best-rule classification brittle: a top1 miss can still be a near-equivalent update by measured short-probe delta.

## Validation Confusions

| target | predicted | target family | predicted family | count |
|---|---|---|---|---:|
| wait_light | neutral_additive | wait | additive_or_neutral | 22 |
| wait_light | block_heavy | wait | block | 17 |
| neutral_additive | block_heavy | additive_or_neutral | block | 16 |
| neutral_additive | wait_light | additive_or_neutral | wait | 16 |
| block_light | neutral_additive | block | additive_or_neutral | 14 |
| neutral_additive | commit_heavy | additive_or_neutral | commit | 14 |
| wait_heavy | neutral_additive | wait | additive_or_neutral | 14 |
| block_heavy | wait_light | block | wait | 13 |
| commit_heavy | neutral_additive | commit | additive_or_neutral | 13 |
| block_light | wait_light | block | wait | 12 |

The largest failures remain concentrated around neutral/additive semantics, block-heavy predictions, and wait-vs-block confusion on held-out maps.

## Safety Threshold Sweep

The current offline eval uses threshold `0.50`. The sweep below is diagnostic only; any deployable threshold must be chosen on train/calibration data and then re-evaluated.

- Train-calibrated candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.40`, recall `0.8357`, precision `0.6481`, fallback rate `0.6401`, mean delta after fallback `0.0111`.
- Validation diagnostic candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.15`, recall `0.9017`, precision `0.4084`, fallback rate `0.8322`, mean delta after fallback `0.0118`.

## Feature Drift

| feature | standardized mean diff | train mean | validation mean |
|---|---:|---:|---:|
| obstacle_ratio | 0.8143 | 0.2165 | 0.1090 |
| map_width | 0.6234 | 77.9798 | 40.3660 |
| free_cells | 0.5410 | 3921.2102 | 1581.6340 |
| map_height | 0.5202 | 51.0321 | 40.3660 |
| local_degree_mean_topk | 0.4433 | 3.1727 | 3.4254 |
| wait_per_committed | 0.3426 | 0.0530 | 0.0367 |
| nonzero_edges_before | 0.3057 | 4424.8096 | 2785.3442 |
| new_nonzero_edges_count | 0.2986 | 2096.1611 | 1238.1198 |
| blocked_per_committed | 0.2760 | 0.1137 | 0.0871 |
| topk_blocked_edge_concentration | 0.2439 | 0.0662 | 0.0818 |
| entropy_edge_usage | 0.2001 | 5.9621 | 5.7263 |
| mean_topk_raw_before | 0.1359 | 74.8881 | 120.5268 |

Validation maps covered in drift comparisons: `empty-48-48, maze-32-32-4`.

## Generated Tables

- label margin details: `outputs/tables/phase4f_repair1_diagnostics/phase4f_laur_label_margin_details.csv`
- label margin histogram: `outputs/tables/phase4f_repair1_diagnostics/phase4f_laur_label_margin_histogram.csv`
- per-map confusion: `outputs/tables/phase4f_repair1_diagnostics/phase4f_laur_per_map_confusion.csv`
- safety threshold sweep: `outputs/tables/phase4f_repair1_diagnostics/phase4f_laur_safety_threshold_sweep.csv`
- feature drift: `outputs/tables/phase4f_repair1_diagnostics/phase4f_laur_feature_drift.csv`

## Next Repair Order

1. Preserve the current exact-rule gate, but add diagnostics for collapsed additive/neutral and rule-family accuracy so we can tell semantic confusion from total failure.
2. Try safety calibration next: lower or calibrate the harmful threshold on train/calibration to recover recall, then measure fallback rate and mean predicted delta.
3. If exact rule top1/top3 remains poor, move to margin-aware labels or a rule-aware scorer that ranks `(checkpoint, update_rule)` candidates instead of predicting one hard class from checkpoint features alone.
4. Keep Phase5 learned runtime blocked until the exact validation top1/top3 and harmful recall gates pass without using validation to tune final thresholds.
