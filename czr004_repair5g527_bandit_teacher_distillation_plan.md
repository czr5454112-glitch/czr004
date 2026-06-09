# Repair5G.5.27 Conservative Bandit Teacher Distillation Plan

Date: 2026-06-09

## Scope

G5.27 audits the G5.26 constrained contextual-bandit result as an offline teacher, not as a runtime policy. The round uses G5.26 full-coverage rank-effect features and counterfactual outcomes to build teacher labels, then evaluates whether runtime-safe feature-only selectors can imitate the teacher and preserve safe policy value under heldout controls.

## Stages

1. Verify G5.26 starting artifacts, full-coverage rows, closed claims, reserved ID guard, and untouched `external/lacam2/lacam2/**`.
2. Audit why G5.26 final policy arbitration ignored the bandit suite for runtime best-policy selection.
3. Classify bandit fields as runtime-safe features, counterfactual outcomes, oracle labels, risk labels, fallback baselines, or audit-only fields.
4. Build context, candidate, and policy-decision teacher tables from `conservative_policy_improvement_over_g525_best`.
5. Create runtime-safe distillation features with fold-style policy priors and leakage scans.
6. Evaluate bandit-teacher distillation models, controls, heldout families, budget holdout, bootstrap, and calibration.
7. Evaluate safe policy calibration and abstention variants.
8. Verify exact failure-audit logging statically and run only a bounded manifest/probe path if the learned selector remains blocked.
9. Run offline-only conservative policy-improvement/CQL diagnostics.
10. Refine goal-aware residual teacher labels as future UpdateLTM training proxies.
11. Synthesize failure/success and write the final G5.27 decision.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not touch PIBT, LaCAM*, search semantics, OPEN/EXPLORED behavior, h-values, action logits, action prediction, priority prediction, or learned runtime solver control.
- Do not inspect or run IDs `166..205`.
- Use counterfactual/oracle/risk fields only for teacher labels and evaluation, never in model-facing `feature_*` columns.
- Keep all runtime, Phase5.5, Phase6, learned-runtime-policy, and AAAI claims closed.

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```
