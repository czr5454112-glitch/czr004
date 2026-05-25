# Phase3 Teacher Data Report

Date: 2026-05-25
Status: Phase3 teacher-data gate complete

## Gate Result

- teacher manifest: `artifacts\teacher\manifest.jsonl`
- edge-label schema: `phase3_edge_label_v1`
- PIBT trace schema: `phase3_pibt_trace_v1`
- runs generated: 8
- edge-label rows generated: 90992
- sample policy: `fixed` agents=50, instances=[1], time_limit_sec=3
- successful runs: 8 / 8
- feasible runs: 8 / 8
- split leakage audit: passed

## Supervision Route

Primary route is `online_residual`: future NTM inference should start from `w_ntm = clamp(w_ltm + delta, 0, 10)` and remain safely comparable to LTM. The exported `ltm_normalized_weight` is a warm-start teacher target, not the final solver-facing claim. Pure edge regression is therefore diagnostic/pretraining only.

## Split Rule

The split is map-holdout: a map appears in exactly one split, so generated seeds and scenarios for that map cannot cross train/validation/test.

- train: runs=6, maps=6, label_rows=79274, map_names=`empty-32-32;random-32-32-20;random-64-64-20;room-64-64-8;warehouse-10-20-10-2-1;warehouse-10-20-10-2-2`
- validation: runs=1, maps=1, label_rows=9024, map_names=`empty-48-48`
- test: runs=1, maps=1, label_rows=2694, map_names=`maze-32-32-4`

## Edge Label Rows

Each label row is one directed graph edge after a LaCAM*+LTM run. Core fields are `run_id`, map/scenario metadata, `from_id`, `to_id`, grid coordinates, `ltm_raw_count`, `ltm_normalized_weight`, `warm_start_target_weight`, `residual_reference_weight`, `residual_delta_target`, and `traversal_cost`.

## PIBT Trace Schema

Raw PIBT trace events use schema `phase3_pibt_trace_v1`: `run_id`, `iteration`, `event_index`, `kind` (`committed` or `blocked`), `agent_id`, `from_id`, `to_id`, `at_goal`, plus map/scenario/agent/seed metadata. Phase3 stores derived edge labels by default; raw traces belong under ignored `artifacts/teacher/traces/` when enabled.

## Outputs

- config: `configs\phase3\teacher_data.yaml`
- manifest: `artifacts\teacher\manifest.jsonl`
- dataset summary CSV: `outputs\tables\phase3_teacher_dataset_summary.csv`
- split audit CSV: `outputs\tables\phase3_teacher_split_audit.csv`
- ignored edge labels root: `artifacts/teacher/edge_labels`

## Repro Commands

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_phase1a_batch.ps1
& 'C:\PROGRAMING\anaconda\Scripts\conda.exe' run -n czr004 python scripts\generate_phase1a_scenarios.py --manifest configs\phase1a\manifest_plus_3000.jsonl --overwrite
& 'C:\PROGRAMING\anaconda\Scripts\conda.exe' run -n czr004 python scripts\run_phase3_teacher_data.py --config configs\phase3\teacher_data.yaml --overwrite
```

## Validation

- every generated edge-label row passed schema validation
- every manifest row passed schema validation
- map/map-seed/run-id leakage audit passed
