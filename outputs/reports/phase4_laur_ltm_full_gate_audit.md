# Phase4F LAU-LTM Full Gate Audit

Date: 2026-05-26

## Run

- server: old instance `ackcs-00gjgxxy`
- workdir: `/root/shared-nvme/czr004_phase4_full_9c395b1_zstd`
- commit: `9c395b1`
- tmux session: `phase4_laur_full_9c395b1_zstd`
- started: `2026-05-26T16:50:51+08:00`
- finished: `2026-05-26T17:53:34+08:00`

## Storage

- raw trace was streamed through FIFO and retained as zstd.
- compressed trace: `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst`
- compressed size: `810218454` bytes (`773M`)
- sha256: `c2a8deadfa8c7628fd8411b91bc369b3c1d69aa171184f278c1f1171ffd0ad47`
- shared disk remained healthy: about `3.0G / 50G` used after completion.

## Data

- runs: `480`
- checkpoint rows: `1897`
- probe rows: `15360`
- dataset rows: `1897`
- non-neutral checkpoints: `1484`
- validation non-neutral checkpoints: `349`
- harmful update count: `782`

Label distribution:

```json
{
  "block_heavy": 325,
  "block_light": 163,
  "commit_heavy": 316,
  "decay_090": 98,
  "decay_095": 87,
  "neutral_additive": 413,
  "wait_heavy": 213,
  "wait_light": 282
}
```

## Gate

Operational gate passed: record, probe, dataset, train, and eval all completed.

Phase4F performance gate failed on held-out validation:

- top1 rule accuracy: `0.1943231441048035` (`fail`, threshold `0.35`)
- top3 rule accuracy: `0.47161572052401746` (`fail`, threshold `0.70`)
- harmful recall: `0.5524861878453039` (`fail`, threshold `0.80`)
- harmful precision: `0.5952380952380952` (`pass`, threshold `0.30`)
- predicted-rule mean delta ratio: `0.0028657477581722716` (`pass`)
- validation neutral additive rate: `0.24017467248908297` (`documented`)

## Interpretation

The full experiment is operationally valid and no longer blocked by disk usage. It is not yet valid evidence for Phase5 learned runtime because the held-out validation rule-selection metrics remain below gate. Train metrics are much higher than validation metrics, so the next work should focus on validation generalization and harmful-update recall rather than infrastructure.
