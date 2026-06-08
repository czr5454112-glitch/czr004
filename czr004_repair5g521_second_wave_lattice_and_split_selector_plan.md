# Repair5G.5.21 Second-Wave Lattice and Split Selector Plan

Date: 2026-06-08

This G5.21 package executes the G5.20 follow-up as an observed-ID-only local diagnostic round:

1. Verify G5.20 corrected targets, feature matrix, policy failure, and second-wave plan.
2. Decompose no-solution/nonfinite risk into avoidable and unavoidable failure semantics.
3. Build a deterministic second-wave bounded dual-channel UpdateLTM candidate pool.
4. Verify project-owned adapter grammar for `repair5g521_grid_*` names and preserve G5.18 fingerprints.
5. Run a local targeted second-wave probe on the G5.20 missed new-opportunity contexts plus controls.
6. Analyze second-wave oracle gain and only run full-primary confirmation if the predeclared targeted gate passes.
7. Build v10 split context/family/candidate targets and runtime-safe feature tables.
8. Evaluate split opportunity selectors with context gate, family gate, candidate ranker, avoidable-risk guard, and static fallback.
9. Write oracle-to-policy gap autopsy and final decision.

Closed claims for all G5.21 artifacts:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

Execution constraints:

- Local PC only.
- `max_workers=1` for solver probes.
- Do not inspect or run IDs `166..205`.
- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, OPEN/EXPLORED, rewrite/incumbent/pruning/restart semantics, h-values, MAPF action logits, action prediction, priority prediction, learned solver control, or candidate deletion behavior.
