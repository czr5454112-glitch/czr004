# Phase5.5 Repair5G.5.3 Protocol Overview

G5.3 split the old runtime equivalence failure into separate transform, hook, overhead, and label-infrastructure gates.

## Gate Results

- Gate A, UpdateLTM transform equivalence: passed.
  - Observed matrix: maps `random-32-32-20`, `maze-32-32-4`, `warehouse-10-20-10-2-1`; agents 50/100; IDs 146..155; 3s; max LTM iterations 4.
  - Rows: 870 transform audit rows.
  - Mismatches: 0 traffic-after hash, 0 params hash, 0 C/F update stats.
- Gate B, overhead-neutral minimal hook at primary 3s budget: failed.
  - Rows: 1500 analyzed overhead rows.
  - Minimal-hook mismatches: 10, all classified as `time_budget_sensitivity`.
  - True semantic mismatches: 0.
  - Narrow failure set: `warehouse-10-20-10-2-1`, 100 agents, IDs 146..155.
- Gate C, overhead attribution: classified.
  - Dominant component: `repair5g53_cost_audit_ms`.
  - Primary 3s mean positive cost-audit component: 1607.4005457627118 ms.
  - Targeted warehouse/100 budget sensitivity passed at 5s and 10s, with 0 minimal-hook mismatches.
- Checkpoint export: blocked by primary minimal-hook equivalence failure.
- Checkpoint replayability: blocked by checkpoint export.
- Counterfactual labels: unavailable because replayable checkpoint/probe infrastructure remains blocked.

## Evidence Artifacts

- `outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json`
- `outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json`
- `outputs/tables/phase5p5_repair5g53_hook_overhead_mismatches.csv`
- `outputs/reports/phase5p5_repair5g53_hook_overhead_budget_5s_summary.json`
- `outputs/reports/phase5p5_repair5g53_hook_overhead_budget_10s_summary.json`
- `outputs/reports/phase5p5_repair5g53_checkpoint_export_smoke_summary.json`
- `outputs/reports/phase5p5_repair5g53_checkpoint_replayability_summary.json`
- `outputs/reports/phase5p5_repair5g53_counterfactual_label_summary.json`

## Boundary

No reserved IDs were run: command logs cover IDs 146..155 only, and IDs 166..205 remain untouched. No learned selector, mixture, residual model, MLP, GNN, or transformer was trained. Solver semantics remain unchanged.

G5.3 remains diagnostic-only: `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`.
