# Phase4F LAUR Failure Diagnostics

Date: 2026-05-27

## Scope

This report is a P0 diagnostic pass over the completed Phase4F full run. It does not lower the Phase4F gate, does not change labels, and does not advance the model into Phase5 learned runtime.

## Inputs

- dataset: `artifacts/teacher/laur/full_repair3_stable_targets/update_labels/phase4_laur_update_dataset_full_repair3_stable_tie001.jsonl`
- probes: `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- offline eval CSV: `outputs/tables/phase4f_repair3_stable_tie001_s107_eval_h010.csv`
- offline eval summary: `outputs/reports/phase4f_repair3_stable_tie001_s107_eval_h010_summary.json`
- dataset rows: `2985`
- probe rows: `24216`
- eval rows: `2985`
- eval gate script passed operationally: `True`

## Gate Recap

| split | samples | exact top1 | exact top3 | family top1 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.4992 | 0.8349 | 0.5075 | 0.9984 | 0.5272 | 0.0292 |
| validation | 459 | 0.3922 | 0.7669 | 0.4074 | 0.9711 | 0.3916 | -0.0012 |
| all | 2985 | 0.4827 | 0.8245 | 0.4921 | 0.9951 | 0.5064 | 0.0246 |

Family top1 collapses `block_*`, `wait_*`, `decay_*`, `commit_*`, and additive/neutral variants. It is diagnostic only; the Phase4F gate still uses exact rule top1/top3.

## Label Margins

- Validation checkpoints with best-vs-second probe margin <= 0.005: `245` / `459` (53.38%).
- Validation checkpoints with margin <= 0.010: `324` / `459` (70.59%).
- All checkpoints with margin <= 0.005: `1407` / `2985` (47.14%).
- Near ties make hard best-rule classification brittle: a top1 miss can still be a near-equivalent update by measured short-probe delta.

## Validation Confusions

| target | predicted | target family | predicted family | count |
|---|---|---|---|---:|
| commit_heavy | neutral_additive | commit | additive_or_neutral | 46 |
| neutral_additive | commit_heavy | additive_or_neutral | commit | 40 |
| block_heavy | neutral_additive | block | additive_or_neutral | 36 |
| wait_light | neutral_additive | wait | additive_or_neutral | 21 |
| neutral_additive | block_heavy | additive_or_neutral | block | 17 |
| block_heavy | commit_heavy | block | commit | 14 |
| neutral_additive | wait_light | additive_or_neutral | wait | 10 |
| decay_095 | neutral_additive | decay | additive_or_neutral | 8 |
| wait_heavy | neutral_additive | wait | additive_or_neutral | 8 |
| block_light | neutral_additive | block | additive_or_neutral | 7 |

The largest failures remain concentrated around neutral/additive semantics, block-heavy predictions, and wait-vs-block confusion on held-out maps.

## Safety Threshold Sweep

The current offline eval uses threshold `0.50`. The sweep below is diagnostic only; any deployable threshold must be chosen on train/calibration data and then re-evaluated.

- Train-calibrated candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.40`, recall `0.8421`, precision `0.6519`, fallback rate `0.6413`, mean delta after fallback `0.0073`.
- Validation diagnostic candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.30`, recall `0.8439`, precision `0.4725`, fallback rate `0.6732`, mean delta after fallback `0.0014`.

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

- label margin details: `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_label_margin_details.csv`
- label margin histogram: `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_label_margin_histogram.csv`
- per-map confusion: `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_per_map_confusion.csv`
- safety threshold sweep: `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_safety_threshold_sweep.csv`
- feature drift: `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_feature_drift.csv`

## Next Repair Order

1. Preserve the current exact-rule gate, but add diagnostics for collapsed additive/neutral and rule-family accuracy so we can tell semantic confusion from total failure.
2. Try safety calibration next: lower or calibrate the harmful threshold on train/calibration to recover recall, then measure fallback rate and mean predicted delta.
3. If exact rule top1/top3 remains poor, move to margin-aware labels or a rule-aware scorer that ranks `(checkpoint, update_rule)` candidates instead of predicting one hard class from checkpoint features alone.
4. Keep Phase5 learned runtime blocked until the exact validation top1/top3 and harmful recall gates pass without using validation to tune final thresholds.
