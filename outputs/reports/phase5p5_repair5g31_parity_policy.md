# Phase5.5 Repair5G.3.1 Parity Policy

This policy is conservative and diagnostic-only. It does not grant Phase5.5 or Phase6 permission.

## Layers

### Semantic Parity

No control method may change LaCAM*/PIBT/LTM semantics. The accepted semantic gate is `true_semantic_parity_mismatch_count = 0` after raw-row autopsy and sequential reproduction.

### Strict Wall-Clock Parity

Exact rows are still reported for additive, disabled, force-additive, dual-additive, and dual-C-equivalent controls. A strict exact failure must keep `protocol_gates_passed=false` unless a separate, explicit parity policy is active for broad validation.

### Time-Budget-Equivalent Parity

For broad anytime validation, strict differences may be accepted only when every mismatch is classified as time-budget sensitivity, timeout equivalence, return-code-2 no-solution equivalence, or reporting-only, with zero true semantic mismatches and zero solver crashes.

## Decision

- policy_decision: `time_budget_equivalent_parity_accepted_for_g4_broad_validation`
- strict_parity_restored: `False`
- broad_validation_policy: `semantic_parity_plus_time_budget_equivalence_required`
- parity_policy_accepted: `True`

## Required G4 Protocol

- Keep strict exact parity fields in reports and audits.
- Require semantic parity and time-budget-equivalence classification for broad clean validation.
- Require `returncode 2` to be handled as no-solution/timeout equivalent, not solver crash.
- Require boolean and numeric gate types to remain distinct.
- Do not allow selected or representation gates to override a protocol failure.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
