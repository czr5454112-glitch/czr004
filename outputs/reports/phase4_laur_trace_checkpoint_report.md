# Phase4C LAU Trace/Checkpoint Report

Date: 2026-05-26 10:56:47
Status: passed

## Scope

Phase4C records iteration-level LAU checkpoints and raw PIBT trace events. No learning/training, `cpp/ntm` change, learned restart, or runtime learned update is included.

## Code State

- branch: `phase4-laur-ltm`
- commit: `fef6956`
- dirty: `tracked-dirty`
- config: `configs\phase4\laur_ltm.yaml`

## Smoke Run

- map: `random-32-32-10`
- agents: 50
- seed: 1
- time_limit_sec: 3
- max_iterations: 4
- record exit code: 0

## Commands

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_record.ps1
C:\PROGRAMING\czr004\build\phase4-laur-ltm\phase4_laur_record.exe --map C:\PROGRAMING\czr004\external\lacam2\assets\random-32-32-10.map --scen C:\PROGRAMING\czr004\external\lacam2\assets\random-32-32-10-random-1.scen --map-name random-32-32-10 --split train --agents 50 --seed 1 --time-limit-sec 3 --max-iterations 4 --run-id random-32-32-10__a50__s1__phase4c_smoke --checkpoint-jsonl C:\PROGRAMING\czr004\artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl --trace-jsonl C:\PROGRAMING\czr004\artifacts\teacher\laur\traces\phase4_laur_trace_smoke.jsonl --traffic-snapshot-root C:\PROGRAMING\czr004\artifacts\teacher\laur\checkpoints\snapshots --checkpoint-topk-edges 16 --branch phase4-laur-ltm --commit fef6956 --dirty tracked-dirty --export-raw-trace --export-checkpoints --force-additive
C:\Users\38908\.conda\envs\czr004\python.exe C:\PROGRAMING\czr004\src\czr004_teacher\update_sequences.py --checkpoint-jsonl C:\PROGRAMING\czr004\artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl --trace-jsonl C:\PROGRAMING\czr004\artifacts\teacher\laur\traces\phase4_laur_trace_smoke.jsonl --summary-json C:\PROGRAMING\czr004\outputs\reports\phase4_laur_trace_checkpoint_audit_summary.json
powershell -ExecutionPolicy Bypass -File scripts\build_phase1_ltm.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_phase4_laur_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\phase4_laur_update_smoke.ps1
```

## Outputs

- checkpoint JSONL: `artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl` (12923 bytes)
- raw trace JSONL: `artifacts\teacher\laur\traces\phase4_laur_trace_smoke.jsonl` (4528715 bytes)
- traffic snapshots: `artifacts\teacher\laur\checkpoints\snapshots` (14647 bytes)
- audit summary: `outputs\reports\phase4_laur_trace_checkpoint_audit_summary.json` (541 bytes)

## Audit Result

- checkpoint rows: 4
- trace rows: 11489
- checkpoint schema errors: 0
- trace schema errors: 0
- checkpoint-trace join errors: 0
- split leakage errors: 0
- audit passed: True

## Regression Gates

- Phase1 LTM smoke: passed via `powershell -ExecutionPolicy Bypass -File scripts\phase1_ltm_smoke.ps1`
  - loop: `ltm_sum_of_loss=15`, iterations=3
  - random-32-32-10: `ltm_sum_of_loss=76`, iterations=3
- Phase4B force-additive update smoke: passed via `powershell -ExecutionPolicy Bypass -File scripts\phase4_laur_update_smoke.ps1`
  - output: `phase4_laur_update_smoke ok`

## Record Stdout

```text
phase4_laur_record run_id=random-32-32-10__a50__s1__phase4c_smoke map=random-32-32-10 agents=50 seed=1 iterations=4 success=1 feasible=1 runtime_ms=1671.79 checkpoint_jsonl=C:\PROGRAMING\czr004\artifacts\teacher\laur\checkpoints\phase4_laur_checkpoints_smoke.jsonl trace_jsonl=C:\PROGRAMING\czr004\artifacts\teacher\laur\traces\phase4_laur_trace_smoke.jsonl
```
