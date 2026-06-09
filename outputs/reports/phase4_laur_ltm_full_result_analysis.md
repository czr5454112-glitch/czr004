# Phase4F Full Result Analysis

Date: 2026-05-26

## Summary

Phase4F full completed end to end on the old server with streaming-compressed raw traces. The run is operationally valid, but it does not pass the Phase4F performance gate, so it is not ready for Phase5 learned runtime integration.

The main failure mode is validation generalization. Train metrics are strong, while held-out validation metrics are far below gate.

## Evidence

- run commit: `9c395b1`
- server workdir: `/root/shared-nvme/czr004_phase4_full_9c395b1_zstd`
- tmux session: `phase4_laur_full_9c395b1_zstd`
- runs: `480`
- checkpoints: `1897`
- probe rows: `15360`
- dataset rows: `1897`
- non-neutral checkpoints: `1484`
- validation non-neutral checkpoints: `349`
- raw trace archive: `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst`
- raw trace size: `810218454` bytes
- raw trace sha256: `c2a8deadfa8c7628fd8411b91bc369b3c1d69aa171184f278c1f1171ffd0ad47`

## Gate Status

Operational gate passed:

- record completed
- probe completed
- dataset completed
- train completed
- eval completed

Performance gate failed:

| metric | validation | threshold | status |
|---|---:|---:|---|
| non-neutral checkpoints | 349 | 50 | pass |
| rule top1 accuracy | 0.1943 | 0.35 | fail |
| rule top3 accuracy | 0.4716 | 0.70 | fail |
| harmful update recall | 0.5525 | 0.80 | fail |
| harmful update precision | 0.5952 | 0.30 | pass |
| predicted-rule mean delta ratio | 0.0029 | 0.0 | pass |

## Train vs Validation

| split | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|---:|
| train | 1439 | 0.7470 | 0.9514 | 0.7454 | 0.7555 | 0.0282 |
| validation | 458 | 0.1943 | 0.4716 | 0.5525 | 0.5952 | 0.0029 |

Interpretation: the model fits the training maps/rules but does not transfer well to held-out validation maps. This is a modeling/data generalization issue, not a storage or execution issue.

## Validation Breakdown

By validation map:

| map | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|---:|
| empty-48-48 | 240 | 0.2500 | 0.5333 | 0.2653 | 0.3171 | 0.0060 |
| maze-32-32-4 | 218 | 0.1330 | 0.4037 | 0.6591 | 0.6850 | -0.0006 |

By agent count:

| agents | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 120 | 0.1667 | 0.5333 | 0.3611 | 0.5417 | 0.0039 |
| 100 | 120 | 0.2250 | 0.4250 | 0.3061 | 0.7143 | 0.0111 |
| 200 | 120 | 0.1917 | 0.4667 | 0.7049 | 0.6935 | 0.0338 |
| 400 | 98 | 0.1939 | 0.4592 | 0.8286 | 0.4754 | -0.0464 |

By iteration:

| iteration | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 120 | 0.2167 | 0.6083 | 0.6471 | 0.6111 | 0.0304 |
| 1 | 120 | 0.2083 | 0.4667 | 0.5957 | 0.5600 | -0.0346 |
| 2 | 110 | 0.1091 | 0.3727 | 0.5333 | 0.6486 | 0.0138 |
| 3 | 108 | 0.2407 | 0.4259 | 0.3947 | 0.5556 | 0.0028 |

## Error Pattern

The largest validation confusions are between `neutral_additive`, `block_heavy`, `commit_heavy`, and wait-heavy/light variants:

- `neutral_additive -> block_heavy`: 28
- `commit_heavy -> commit_heavy`: 28 correct
- `block_heavy -> neutral_additive`: 24
- `wait_light -> neutral_additive`: 24
- `block_heavy -> block_heavy`: 23 correct
- `neutral_additive -> neutral_additive`: 22 correct
- `wait_heavy -> block_heavy`: 20
- `commit_heavy -> block_heavy`: 20

The model predicts a plausible-looking distribution, but it cannot rank the exact best update rule reliably on held-out maps. It is better at safety than exact rule selection, but harmful recall is still below the Phase4F threshold.

## Storage/Trace Conclusion

The raw trace concern is resolved:

- Full raw trace is preserved as zstd and has been downloaded locally.
- The compressed trace is too large for normal GitHub storage, so it is intentionally not committed as a regular Git object.
- The committed reports record its local/server path, size, and sha256.
- Checkpoint-only dataset construction no longer drops the two raw-trace-derived spatial features because checkpoint rows now include blocked-edge summaries.

## Recommended Next Work

1. Add validation-generalization diagnostics before changing thresholds.
2. Compare per-map feature distributions for train vs validation, especially `empty-48-48` and `maze-32-32-4`.
3. Improve harmful-update recall with either class weighting, threshold tuning, or a safety-first fallback that predicts additive when harmful probability is uncertain.
4. Investigate whether top1/top3 labels are too noisy when several rules have near-equal delta ratios; consider margin-aware labels or top-k target smoothing.
5. Keep Phase5 learned runtime blocked until validation top1/top3 and harmful recall gates pass.
