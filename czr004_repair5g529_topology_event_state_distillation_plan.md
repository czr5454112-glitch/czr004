# Repair5G.5.29 Topology/Event-State Distillation Plan

Date: 2026-06-09

## Objective

G5.29 tests whether the G5.28 distillation blocker is mainly caused by data
scarcity, missing topology/event state, or brittle candidate-specific labels.

This round is offline-only. It does not create a new response-surface lattice,
does not modify LaCAM*/PIBT/search semantics, and does not claim runtime,
Phase5.5, Phase6, learned-runtime, or AAAI readiness.

## Execution Stages

1. Verify G5.28 teacher consistency, exact-failure audit, fold-safe data, and
   failed distillation/calibration state.
2. Decompose the blocker by action class, map family, warehouse failures,
   exact-feature ablation, and label granularity.
3. Build an observed-ID context panel, excluding IDs 166..205. If the local
   corpus cannot meet the requested expansion minimum, report the shortfall.
4. Generate an expanded exact-failure audit manifest from the observed panel
   with `max_workers=1`.
5. Reconstruct the conservative teacher on the panel and carry forward the
   no-candidate-induced-failure teacher invariant.
6. Add map topology, agent/topology interaction, event-graph, and
   candidate/topology UpdateParams interaction features.
7. Build hierarchical labels for action class, fallback/risk, region,
   candidate, parameter residual, and utility bucket.
8. Build fold-safe train/dev datasets with train-fold-only priors.
9. Train/evaluate fold-trained hierarchical distillation models, topology/event
   ablations, safe arbitration policies, graph/neural readiness diagnostics,
   and teacher-to-UpdateLTM residual continuation.
10. Write the final G5.29 decision with closed claims preserved.

## Constraints

- `external/lacam2/lacam2/**` remains untouched.
- No PIBT conflict semantics, LaCAM* high-level search, OPEN/EXPLORED,
  rewrite/incumbent/pruning/restart, candidate deletion, h-value, MAPF action,
  action-logit, or priority-prediction changes.
- No IDs `166..205` are used.
- Closed claims remain:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```
