# Phase5.5 Repair5F.4 Failure Oracle Diagnosis Decision

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- do_not_promote: `true`
- do_not_retune_from_f4: `true`

## Decision

`plan_new_static_candidate_protocol_with_untouched_final_validation`

A static candidate appears robust on F4, but that is diagnostic-only because F4 outcomes observed it. Any static claim requires a new support/validation protocol and a fresh final holdout. Support-to-F4 transfer is poor or overranked the locked rule, so the selector objective also needs diagnosis.

## Evidence

- F4 oracle: 67 / 53 / 0, mean `-0.017388555948699997`, ratio-worse groups `0`, success-worse groups `0`.
- Best F4 static candidate `c125_b125_w075_d095`: 35 / 64 / 21, mean `-0.0028050352278249997`, ratio-worse groups `0`.
- Leave-one-group static selection: 31 / 66 / 23, mean `-0.0024372178218000046`.
- Support-vs-F4 rank transfer: Spearman `0.18987049028677153`, locked support rank `1`, locked F4 rank `27`.

## Boundary

Any candidate or selector suggested by this diagnosis must be trained/tuned only on allowed support and validation data and evaluated on a new untouched final holdout such as IDs 46..65 or later. F4 outcomes remain diagnostic-only evidence.
