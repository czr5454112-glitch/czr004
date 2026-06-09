# Repair5G.5.22 Response-Surface Teacher Dataset Plan

Date: 2026-06-08

This execution package pivots from G5.21 local second-wave lattice tuning to a
response-surface teacher dataset for goal-aware dual-channel UpdateLTM. It keeps
the same solver semantics and uses observed IDs only.

## Scope

- Verify G5.21 artifacts from starting commit `8120cf1`.
- Autopsy G5.21 failure modes: duplicates, near-duplicates, candidate-induced
  no-solution, missing static recovery, budget stability, and dominant controls.
- Build a stratified observed-ID context panel with new opportunity, static
  recovery, candidate-induced risk, static-near/no-new-safe, and unavoidable
  failure buckets.
- Generate deterministic `repair5g522_grid_*` parameter response-surface
  candidates from local winner neighborhoods, feasibility variants,
  risk-boundary variants, and fractional coverage.
- Verify project-owned bounded adapter recognition for G5.22 without touching
  LaCAM*/PIBT/search semantics.
- Run the local response-surface counterfactual probe with `max_workers=1`.
- Analyze incremental oracle gain over old14 plus retained G5.18 controls.
- Build neural-ready context, candidate, pairwise, and edge/update teacher
  tables when checkpoint fields permit it.
- Train offline neural-readiness surrogate diagnostics with negative controls.
- Write signal/generalization autopsy and final decision.

## Closed Claims

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

No runtime policy, Phase5.5, Phase6, AAAI, action, priority, restart, h-value,
candidate-deletion, PIBT, or LaCAM* search claim is opened by this round.
