# Repair5G.5.28 Exact Failure Audit Distillation Plan

Date: 2026-06-09

## Objective

G5.28 audits the G5.26/G5.27 conservative bandit teacher, adds audit-only PIBT-return-false failure traces, rebuilds runtime-safe exact-failure features, trains real fold-based distillation diagnostics, and writes a closed-claims decision.

## Boundaries

- No new candidate lattice wave.
- No changes under `external/lacam2/lacam2/**`.
- No PIBT conflict, LaCAM* search, restart, rewrite, pruning, h-value, candidate-deletion, action-logit, or priority semantic changes.
- Exact failure logging is audit-only and separate from UpdateLTM trace events.
- IDs `166..205` stay untouched.
- `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false` stay closed.

## Stages

1. Verify G5.27 starting artifacts and record that exact failure audit logging was unavailable before G5.28.
2. Reconstruct the conservative teacher directly from G5.26 bandit decisions and check it against G5.27 teacher tables.
3. Add static-verifiable audit-only PIBT failure logging keys and run a tiny smoke.
4. Run a targeted exact-failure trace probe over G5.27 distillation failure contexts.
5. Join exact-failure audit features to runtime-safe policy-distillation features.
6. Create fold-safe train/dev datasets with no dev-label priors.
7. Train real fold-evaluated models and controls.
8. Evaluate calibrated policies and abstention guards.
9. Run offline learned-Q/CPI diagnostics.
10. Create goal-aware UpdateLTM residual teacher-refinement labels and diagnostics.
11. Synthesize whether exact failure features made the teacher learnable and write the G5.28 decision.
