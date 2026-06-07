# Phase5.5 Repair5G.5.7 Protocol Overview

G5.7 is an observed-ID diagnostic wave for budget-aware label confidence and an offline G6 safe-mixture gate.

## Protocol

- Treat 250 ms as stress-only.
- Treat 1000/2000 ms as the primary label-confidence pair.
- Treat 500 ms as an agreement bonus, not a hard gate.
- Preserve no-solution and warehouse failures as explicit label classes.
- Build two feature variants:
  - `perf_safe_only` for any future runtime-performance claim.
  - `audit_plus_perf` as diagnostic-only.
- Train offline G6 only if confidence-weighted labels pass the training thresholds.

## Training Gate

Training requires:

- `training_eligible_contexts >= 30`
- `stable_high_confidence_nonstatic_count >= 10`
- `stable_static_or_abstain_count >= 10`
- budget-tier analysis completed
- warehouse policy classified
- performance-safe feature matrix passed
- IDs 166..205 untouched

If the gate fails, the correct decision is to continue label-confidence or candidate-space work, not to force a G6 model.

## Closed Claims

- phase5p5_allowed: `False`
- phase6_allowed: `False`
- aaai_ready: `False`
- runtime_claim_allowed: `False`
