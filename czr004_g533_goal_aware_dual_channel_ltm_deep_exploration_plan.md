# Repair5G.5.33 Goal-Aware Dual-Channel LTM Exploration Plan

Date: 2026-06-10

Round name: `Repair5G.5.33 goal-aware dual-channel LTM`

This round continues after G5.32. G5.32 proved that project-owned real solver
checkpoint exports can materialize real trace slices, but it did not prove that
learned UpdateLTM improves solver outcomes. G5.33 therefore changes the target
from observed traffic-delta prediction to solver-facing outcome labels and
strict leakage diagnostics.

## Guardrails

- Do not edit `external/lacam2/lacam2/**`.
- Do not change PIBT conflicts, candidate domains, agent actions, priorities,
  h-values, candidate deletion, LaCAM* high-level search, OPEN/EXPLORED,
  rewrite, incumbent pruning, or restart semantics.
- Do not inspect or run reserved IDs `166..205`.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`,
  `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and
  `aaai_ready=false` in every summary.
- Treat all learned components as offline diagnostics only.

## Execution Stages

1. Red-team G5.32 materialization, model leakage, micro-counterfactual
   semantics, and gold-join alias counts.
2. Build goal-aware dual-channel edge/context/event features from committed
   real solver slices, marking unavailable raw-goal-distance features as
   `bounded_committed_slice_only`.
3. Define a bounded candidate family using existing project-owned
   `repair5g59_*` UpdateParams aliases.
4. Run a bounded real solver probe over required map families, two agent
   counts, budgets `500/1000/2000`, primary `ltm_max_iterations=2`, and a
   smaller `ltm_max_iterations=4` subset if needed.
5. Convert solver outcomes into utility, pairwise dominance, high-margin,
   residual, and safety/fallback labels.
6. Train/evaluate offline selector, ranker, residual, and safety diagnostics
   under strict context/seed/map/budget holdouts with negative controls.
7. Analyze paired rule evidence versus additive LTM and static flow shield.
8. Write a final decision that either continues toward neural training,
   records static-rule promise without model readiness, or sends the project
   back to label design.

## Validation Commands

The required validation commands are the commands listed in the G5.33 prompt:
script compilation, all stage scripts, JSON summary parsing, `git diff --check`,
and `git status --short -- external/lacam2/lacam2`.

Raw logs under `outputs/logs/phase5p5_repair5g533_*` are local evidence and
should remain ignored unless represented by small samples and manifests.
