# Phase4F Full Repair1 Local Archive Manifest

Date: 2026-05-27

## Server Source

- server: old Phase4F server `ackcs-00gjgxxy`
- remote workspace: `/root/shared-nvme/czr004_phase4_repair1_43633e7`
- server code commit: `43633e7`
- local branch: `phase4-laur-ltm`

## Git-Backed Artifacts

The following useful repair1 artifacts were downloaded locally and are intended to be committed to git:

- `outputs/reports/phase4_laur_ltm_full_repair1_batch_report.md`
- `outputs/reports/phase4_laur_ltm_full_repair1_batch_summary.json`
- `outputs/reports/phase4_laur_ltm_train_full_repair1.md`
- `outputs/reports/phase4_laur_ltm_offline_eval_full_repair1.md`
- `outputs/reports/phase4_laur_ltm_offline_eval_full_repair1_summary.json`
- `outputs/reports/phase4_laur_update_dataset_full_repair1_summary.json`
- `outputs/tables/phase4_laur_ltm_offline_eval_full_repair1.csv`
- `outputs/tables/phase4_laur_update_dataset_full_repair1_summary.csv`
- `artifacts/models/laur_ltm/full_repair1/`
- `artifacts/teacher/laur/full_repair1/checkpoints/phase4_laur_checkpoints_full_repair1.jsonl`
- `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- `artifacts/teacher/laur/full_repair1/update_labels/`
- `artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst.sha256`

## Raw Trace Status

The compressed raw trace is intentionally not committed to git:

- path: `artifacts/teacher/laur/full_repair1/traces/phase4_laur_trace_full_repair1.jsonl.zst`
- remote size: `3516816240` bytes
- local partial size after interrupted resume: `3154116608` bytes
- remaining to download: `362699632` bytes, about `345.9 MiB`
- sha256 sidecar: `0dc42e4e9f6bf8d40642371897b208c2ce3c5901a4576687d11c5f48647a2ccc`

The `.zst` file is ignored by `.gitignore`; only the sha256 sidecar is git-backed.

## Notes

The partial local `.zst` is useful for resuming the later raw-trace download but should not be treated as a verified archive until its size reaches `3516816240` bytes and the sha256 matches the sidecar.
