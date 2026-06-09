# Phase5.5 Repair5G.5.4 Protocol Overview

G5.4 splits semantic replay from budget-stress runtime reproduction. Semantic replay can support observed-ID diagnostic checkpoint/probe labels after G5.3 transform equivalence passed, while 3s exact minimal-hook reproduction remains a reported stress gate.

## Gates

- semantic_vs_budget_policy_passed: `True`
- checkpoint_replayability_passed: `True`
- counterfactual_labels_passed: `True`
- oracle_gap_over_static_measured: `True`
- budget_protocol_passed: `True`
- learned runtime performance claims: `blocked_not_run`
- IDs 166..205: `untouched`

## Evidence

- `outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json`
- `outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json`
- `outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json`
- `outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json`
- `outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json`

G5.4 remains diagnostic-only: `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`.
