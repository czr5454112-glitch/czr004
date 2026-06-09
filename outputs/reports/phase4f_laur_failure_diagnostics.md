# Phase4F LAUR Failure Diagnostics

Date: 2026-05-26

## Scope

This report is a P0 diagnostic pass over the completed Phase4F full run. It does not lower the Phase4F gate, does not change labels, and does not advance the model into Phase5 learned runtime.

## Inputs

- dataset: `artifacts/teacher/laur/full/update_labels/phase4_laur_update_dataset_full.jsonl`
- probes: `artifacts/teacher/laur/full/probes/phase4_laur_probe_full.jsonl`
- offline eval CSV: `outputs/tables/phase4_laur_ltm_offline_eval_full.csv`
- offline eval summary: `outputs/reports/phase4_laur_ltm_offline_eval_full_summary.json`
- dataset rows: `1897`
- probe rows: `15360`
- eval rows: `1897`
- eval gate script passed operationally: `True`

## Gate Recap

| split | samples | exact top1 | exact top3 | family top1 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 1439 | 0.7470 | 0.9514 | 0.7603 | 0.7454 | 0.7555 | 0.0282 |
| validation | 458 | 0.1943 | 0.4716 | 0.2336 | 0.5525 | 0.5952 | 0.0029 |
| all | 1897 | 0.6136 | 0.8355 | 0.6331 | 0.7008 | 0.7201 | 0.0221 |

Family top1 collapses `block_*`, `wait_*`, `decay_*`, `commit_*`, and additive/neutral variants. It is diagnostic only; the Phase4F gate still uses exact rule top1/top3.

## Label Margins

- Validation checkpoints with best-vs-second probe margin <= 0.005: `230` / `458` (50.22%).
- Validation checkpoints with margin <= 0.010: `304` / `458` (66.38%).
- All checkpoints with margin <= 0.005: `926` / `1897` (48.81%).
- Near ties make hard best-rule classification brittle: a top1 miss can still be a near-equivalent update by measured short-probe delta.

## Validation Confusions

| target | predicted | target family | predicted family | count |
|---|---|---|---|---:|
| neutral_additive | block_heavy | additive_or_neutral | block | 28 |
| block_heavy | neutral_additive | block | additive_or_neutral | 24 |
| wait_light | neutral_additive | wait | additive_or_neutral | 24 |
| commit_heavy | block_heavy | commit | block | 20 |
| wait_heavy | block_heavy | wait | block | 20 |
| neutral_additive | block_light | additive_or_neutral | block | 15 |
| wait_light | block_heavy | wait | block | 14 |
| neutral_additive | commit_heavy | additive_or_neutral | commit | 13 |
| neutral_additive | wait_heavy | additive_or_neutral | wait | 12 |
| neutral_additive | wait_light | additive_or_neutral | wait | 12 |

The largest failures remain concentrated around neutral/additive semantics, block-heavy predictions, and wait-vs-block confusion on held-out maps.

## Safety Threshold Sweep

The current offline eval uses threshold `0.50`. The sweep below is diagnostic only; any deployable threshold must be chosen on train/calibration data and then re-evaluated.

- Train-calibrated candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.40`, recall `0.8419`, precision `0.6941`, fallback rate `0.5066`, mean delta after fallback `0.0122`.
- Validation diagnostic candidate meeting recall >= 0.80 and precision >= 0.30: threshold `0.10`, recall `0.8453`, precision `0.4796`, fallback rate `0.6965`, mean delta after fallback `0.0055`.

## Feature Drift

| feature | standardized mean diff | train mean | validation mean |
|---|---:|---:|---:|
| map_width | 1.1491 | 87.1154 | 40.3843 |
| map_height | 1.1171 | 56.4955 | 40.3843 |
| free_cells | 1.0686 | 3968.7985 | 1583.3624 |
| obstacle_ratio | 0.9606 | 0.2276 | 0.1088 |
| local_degree_mean_topk | 0.5766 | 3.1367 | 3.4506 |
| nonzero_edges_before | 0.5171 | 5095.4482 | 2780.3297 |
| new_nonzero_edges_count | 0.4542 | 2266.4010 | 1236.2009 |
| topk_blocked_edge_concentration | 0.3842 | 0.0604 | 0.0853 |
| density | 0.3671 | 0.0966 | 0.1427 |
| blocked_per_agent | 0.3204 | 13.0341 | 31.2015 |
| blocked_count | 0.2765 | 3899.0535 | 10204.4192 |
| mean_topk_raw_before | 0.2606 | 50.4452 | 112.2866 |

Validation maps covered in drift comparisons: `empty-48-48, maze-32-32-4`.

## Generated Tables

- label margin details: `outputs/tables/phase4f_laur_label_margin_details.csv`
- label margin histogram: `outputs/tables/phase4f_laur_label_margin_histogram.csv`
- per-map confusion: `outputs/tables/phase4f_laur_per_map_confusion.csv`
- safety threshold sweep: `outputs/tables/phase4f_laur_safety_threshold_sweep.csv`
- feature drift: `outputs/tables/phase4f_laur_feature_drift.csv`

## Next Repair Order

1. Preserve the current exact-rule gate, but add diagnostics for collapsed additive/neutral and rule-family accuracy so we can tell semantic confusion from total failure.
2. Try safety calibration next: lower or calibrate the harmful threshold on train/calibration to recover recall, then measure fallback rate and mean predicted delta.
3. If exact rule top1/top3 remains poor, move to margin-aware labels or a rule-aware scorer that ranks `(checkpoint, update_rule)` candidates instead of predicting one hard class from checkpoint features alone.
4. Keep Phase5 learned runtime blocked until the exact validation top1/top3 and harmful recall gates pass without using validation to tune final thresholds.
