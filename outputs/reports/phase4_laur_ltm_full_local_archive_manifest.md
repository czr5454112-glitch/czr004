# Phase4F Full Local Archive Manifest

Date: 2026-05-26

## Server Source

- server: `ackcs-00gjgxxy`
- server workdir: `/root/shared-nvme/czr004_phase4_full_9c395b1_zstd`
- run commit: `9c395b1`
- tmux session: `phase4_laur_full_9c395b1_zstd`

## Local Archive

Local root: `C:\PROGRAMING\czr004`

Downloaded and retained locally:

- `artifacts/teacher/laur/full/checkpoints/`
- `artifacts/teacher/laur/full/probes/`
- `artifacts/teacher/laur/full/update_labels/`
- `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst`
- `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst.sha256`
- `artifacts/models/laur_ltm/full/`
- `outputs/reports/phase4_laur_*full*`
- `outputs/tables/phase4_laur_*full*`
- `outputs/logs/phase4_laur_full/`
- `outputs/logs/phase4_laur_full_tmux/`

## Sizes And Counts

- teacher full tree local size: `849622361` bytes
- checkpoint/snapshot files: `1898`
- checkpoint/snapshot size: `13734091` bytes
- probe/update-label files: `3`
- probe/update-label size: `25669717` bytes
- log files: `1933`
- log size: `345117` bytes
- compressed trace size: `810218454` bytes

## Raw Trace Checksum

- local path: `artifacts/teacher/laur/full/traces/phase4_laur_trace_full.jsonl.zst`
- sha256: `c2a8deadfa8c7628fd8411b91bc369b3c1d69aa171184f278c1f1171ffd0ad47`
- verification: local sha256 matches server sidecar.

## Git Policy

The compressed raw trace is intentionally not added to normal Git because the single file is larger than GitHub's regular file size limit. The sidecar checksum and reports are committed, and the trace archive remains available locally and on the server.
