# Phase4F LAU-LTM Pilot Server Note

Date: 2026-05-26

## Run

- server: Paratera `ackcs-00gjgxxy`, RTX 4090 12GB
- session: `phase4_laur_pilot`
- start: `2026-05-26T14:52:21+08:00`
- finish: `2026-05-26T14:57:56+08:00`
- elapsed: about 5 minutes 35 seconds
- status: `passed`
- local source commit before run: `1f6ad35`
- server sync commits: `5204c5a`, `2921052`, `e648089`

## Scope

- runs: 80
- maps: 8
- agent counts: 50, 100
- instances per map/count: 5
- update dataset rows: 320
- non-neutral checkpoints: 250
- validation non-neutral checkpoints: 58

## Offline Metrics

- all rows rule top-1: 0.784375
- all rows rule top-3: 0.871875
- all rows harmful F1: 0.836158
- all rows safety AUROC: 0.790864
- validation rule top-1: 0.1375
- validation rule top-3: 0.4875
- validation harmful F1: 0.121212
- validation safety AUROC: 0.387363

## Notes

The pilot passed the execution and data-coverage gate, not a learned-runtime
performance gate. Validation metrics are weak, so the next server run should be
treated as a larger data and diagnosis experiment before any Phase5 runtime
claim.

The server run reported `tracked-dirty` because `--prepare-scenarios` rewrote
the earlier Phase1a scenario metadata report. The pilot config has been updated
after this run to write pilot scenario metadata to a Phase4-specific report path.
