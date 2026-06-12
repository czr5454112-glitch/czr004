# Repair5G.5.38 Static-Flow Residual Candidate Design and Label Rebuild Plan

## Scope

G5.38 repairs the G5.37 static-flow-relative failure by auditing the old evidence path, rebuilding labels from direct real solver outcomes, and testing a bounded residual candidate family around deployable static-flow baselines.

## Guardrails

- Do not edit `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, priorities, h-values, restart, pruning, rewrite, or conflict semantics.
- Do not inspect or run reserved IDs `166..205`.
- Keep all Phase5.5, Phase6, runtime, learned-runtime, and AAAI claim flags closed.
- Treat static-flow-relative comparisons as mandatory; beating additive alone is not enough.

## Stages

1. Verify G5.37 artifacts and audit failure modes: label source precedence, policy sparsity, deployable vs posthoc static baselines, and failure clusters.
2. Rebuild direct static-relative labels from G5.34, G5.36, and G5.37 real solver outcome rows.
3. Create a small executable static-flow residual candidate family using existing project-owned `repair5g518_grid_*` adapter grammar.
4. Run a real solver residual candidate screening probe on seeds `366..405`.
5. Analyze residual-vs-static-flow, residual-vs-best-fixed, and residual-vs-family-static evidence.
6. Train or skip a residual selector according to the screening evidence.
7. Create and run a blind residual replay on fresh seeds `406..485`.
8. Analyze blind evidence and write the G5.38 decision.
9. Run validation, keep `external/lacam2/lacam2` clean, commit, and push.

## Expected Interpretation

The likely positive path is not another selector over old labels. G5.38 should first establish whether executable residual UpdateParams create safe static-relative gains. If residual candidates do not beat static-flow safely, the decision should identify candidate design as the bottleneck and keep learned-runtime claims closed.
