# Phase5.5 Repair5G.5.11 Full Lattice Ingest

- decision: `full_lattice_artifacts_ingested`
- results_rows: `3360`
- plan_rows: `3360`
- probe_rows: `3360`
- run_rows: `240`
- completed_tasks: `240` / `240`
- checkpoint_jsonl_bytes: `1452356904`

The clean server run used a single worker to avoid concurrent JSONL append corruption. Large checkpoint JSONL was pulled into the local raw artifact directory but is not promoted to GitHub-tracked G5.11 outputs.
