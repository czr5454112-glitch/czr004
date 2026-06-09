# G5.31 Neural UpdateLTM Slice Dataset Pilot Plan

Date: 2026-06-09

This round implements a local pilot for the new solver-trace-slice route added after G5.30. It does not create another response-surface candidate lattice and does not learn MAPF actions, priorities, restarts, h-values, candidate deletion, or search control.

## Scope

- Verify G5.29 closed with `g529_expanded_data_blocker_stop`.
- Treat G5.23/G5.26/G5.28/G5.29 counterfactual tables as validation/calibration gold only.
- Define context, edge, event, failure, and update-label schemas with evidence-strength tags.
- Build a pilot context source with the original 60 gold anchors plus generated `generated_g531_*` contexts outside reserved IDs `166..205`.
- Run a manageable artifact-backed solver trace slice pilot with five UpdateLTM-style configurations and budgets `1000/2000`.
- Convert raw trace task records into neural-ready context, edge, event, failure, and update slices.
- Create residual and risk/fallback labels without using gold columns as training features.
- Train small offline residual, risk, and world-model auxiliary diagnostics using torch/CUDA if available or sklearn/numpy otherwise.
- Write dataset-quality analysis and a final go/no-go decision.

## Guardrails

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

No files under `external/lacam2/lacam2/**` are modified. Raw logs stay local/ignored; committed artifacts are schemas, summaries, tables, small samples, and manifests.
