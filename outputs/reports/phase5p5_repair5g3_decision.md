# Phase5.5 Repair5G.3 Decision

Decision: `protocol_failed`

- Does flow-shield survive broader new-ID validation? `directional_only=True`, but protocol acceptance is blocked.
- Is static flow-shield enough? `tied_within_0p001` under directional P4 metrics.
- Does map-agent selector add value over static? `tied_within_0p001`.
- Is there evidence that a learned contextual selector is worth building/running? `not evaluated because P4 protocol did not pass`.
- Is the effect stable across time budgets and LTM iteration budgets? `not run because P4 protocol did not pass`.
- Observed IDs now include `1..105`; IDs `66..105` were used in a failed/blocked G3 protocol and should not be reused as untouched final evidence.
- Recommended next split: after protocol/time-budget autopsy, use the next clean range, preferably `106..145`, unless `106..125` remains reserved for a later learning-bridge holdout.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- diagnostic_only: `true`
