# Phase4F LAUR Repair Attempts Round 1

Date: 2026-05-26

## Scope

This round tried local, checkpoint-level repairs after the full Phase4F run failed validation top1/top3 and harmful recall. These attempts do not lower the Phase4F gate and do not move the model into Phase5 learned runtime.

## Baseline

Full-run validation gate before repairs:

| model | top1 | top3 | harmful recall | harmful precision | mean predicted delta |
|---|---:|---:|---:|---:|---:|
| full baseline, threshold 0.50 | 0.1943 | 0.4716 | 0.5525 | 0.5952 | 0.0029 |

P0 diagnostics showed that `230 / 458` validation checkpoints have best-vs-second probe margin `<= 0.005`, and `304 / 458` have margin `<= 0.010`. That makes exact hard-label top1 brittle, but the low family-collapsed accuracy means this is not only a harmless within-family tie issue.

## Attempt Summary

| attempt | best validation top1 | best validation top3 | harmful recall range | note |
|---|---:|---:|---:|---|
| lower harmful threshold to 0.10 | 0.1943 | 0.4716 | 0.8453 | fixes safety recall only |
| MLP hyperparameter sweep | 0.2227 | 0.5328 | 0.5083-0.9392 | capacity/regularization alone insufficient |
| feature-drop sweep | 0.2293 | 0.5742 | 0.9337-0.9669 | removing strong OOD map/traffic features helps |
| feature-drop seed sweep | 0.2402 | 0.5917 | 0.9337-0.9779 | stable improvement, still below top3 gate |
| margin-aware soft labels | 0.2489 | 0.6048 | 0.8785-0.9669 | best local top3 result, still below 0.70 |
| rule-aware delta scorer | 0.1878 | 0.4956 | 0.8398 | candidate delta regression did not solve OOD ranking |
| five-model ensemble | 0.2467 | 0.5742 | 0.9669 | averaging did not beat best single soft-label model |

## Best Local Result

The best local top3 came from `soft_t005_mix07_drop_top_h64`:

| metric | validation |
|---|---:|
| top1 | 0.2314 |
| top3 | 0.6048 |
| harmful recall | 0.9669 |
| harmful precision | 0.4289 |
| mean predicted delta | -0.0036 |
| neutral/additive predicted rate | 0.3057 |

The best local top1 came from `soft_t01_mix05_drop_top_h64`:

| metric | validation |
|---|---:|
| top1 | 0.2489 |
| top3 | 0.5524 |
| harmful recall | 0.8785 |
| harmful precision | 0.4517 |
| mean predicted delta | 0.0241 |

## Interpretation

Safety recall is repairable with a conservative threshold chosen from train/calibration behavior. This should remain part of the next full attempt.

Exact rule top1/top3 are not repaired by local training changes alone. The most useful signal is that dropping highly drifting map/traffic features and using margin-aware labels improves top3 from `0.4716` to `0.6048`, but it still misses the `0.70` gate. The remaining gap points to training coverage and label-task design rather than a simple training bug.

The current full dataset has no train map from the maze family, while validation includes `maze-32-32-4`. It also validates on `empty-48-48`, while train has `empty-32-32` only. The strongest next attempt should therefore be a repair-full data pass that adds train coverage for neighboring held-out families without leaking the exact validation maps.

## Next Attempt

Prepare a server run with:

- keep validation maps as `empty-48-48` and `maze-32-32-4`
- add train maps such as `empty-16-16`, `maze-32-32-2`, `random-64-64-10`, `room-32-32-4`, and one larger warehouse variant
- keep `empty-48-48` and `maze-32-32-4` held out
- train with feature-drop plus margin-aware soft labels
- evaluate harmful threshold at `0.10` or a train-calibrated equivalent

If this richer train coverage still fails top1/top3, then the current hard exact-rule gate likely needs a deeper label-quality redesign, not just more local model tuning.
