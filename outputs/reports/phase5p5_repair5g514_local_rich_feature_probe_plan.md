# Phase5.5 Repair5G.5.14 Local Rich Feature Probe Plan

- decision: `local_probe_plan_recorded_not_run`
- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agents: `[50, 100]`
- ids: `[146, 147, 148, 149, 150, 151, 152, 153, 154, 155]`
- budgets: `[1000, 2000]`
- max_contexts_per_group: `1`
- max_workers: `1`
- checkpoint_export_enabled: `true`
- shared_concurrent_jsonl_append_allowed: `false`
- ids_166_205_untouched: `true`
- runtime_claim_allowed: `false`

This wrapper records the safe local probe shape and enforces the reserved-ID and single-worker guards. The current G5.14 run should not execute it when existing checkpoint artifacts are usable.
