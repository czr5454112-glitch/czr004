# Repair5G.5.36 Safe Opportunity Recovery Plan

Date: 2026-06-11

G5.36 continues after G5.35 commit `f630b4d` on `codex/g531-slice-pilot`.
G5.35 removed the G5.34 success regressions, but it did so by falling back too
often. This round audits that conservatism, recovers safe non-additive
opportunities, and runs newly executed solver replay rather than calling copied
rows real replay.

## Guardrails

- Do not edit `external/lacam2/lacam2/**`.
- Do not change PIBT conflict semantics, candidate domain, agent actions,
  priorities, h-values, candidate deletion, LaCAM* high-level search, restart
  semantics, or incumbent pruning.
- Do not use reserved IDs `166..205`.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`,
  `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and
  `aaai_ready=false`.
- Optimize success preservation before ratio improvement.

## Stages

1. Verify G5.35 artifacts and audit policy integrity.
2. Build a safe-opportunity dataset with unsafe regressions, safe high-margin
   gains, low-margin gains, equals, safe-worse, both-fail, and success-gain
   classes.
3. Derive candidate-specific whitelist and blacklist rules by family, budget,
   agent count, and iteration.
4. Evaluate Pareto safety gates that keep false negatives at zero while
   maximizing safe-opportunity retention.
5. Evaluate opportunity-recovery selectors with non-additive recovery and
   additive/static fallback.
6. Build a real solver replay plan including known regression contexts,
   G5.35-prevented contexts, safe opportunities, safe equal controls, and new
   heldout seeds `254..285`.
7. Execute new real solver rows through the project-owned Phase1a batch runner.
8. Analyze selected-vs-additive/static/G5.35 real replay evidence.
9. Write the G5.36 decision with all claims closed.

## Success Criteria

Strong positive requires newly executed real solver replay, at least 1200 new
solver-result rows, at least 500 selected-vs-additive policy pairs, zero success
regressions, fallback rate below 0.85, non-additive selection above 0.05, safe
high-margin capture above zero, non-positive quality-only mean delta, all known
G5.34 regressions avoided, no external solver edits, and closed claims.

If real replay is runtime-limited, G5.36 must say so directly and must not call
copied or materialized prior rows real replay.
