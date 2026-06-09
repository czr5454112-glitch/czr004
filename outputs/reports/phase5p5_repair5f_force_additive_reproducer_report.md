# Phase5.5 Repair5F Force-Additive Reproducer

This reproducer reruns only the force-additive mismatch row(s).

## Boundary

- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- selector_runtime_exported: `false`

## Cases

- `warehouse-10-20-10-2-1`, agents `50`, seed `25`

## Parity

- always_additive_defer: `True`
- repair5f_candidate_additive_ltm: `True`
- laur_disable: `True`
- laur_force_additive_direct: `True`

## Rows

| method | success | SoL | LB | ratio | makespan | expanded | pibt | ltm iters | mode | force |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| lacam_star_ltm | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 20998 | 3 | disabled | False |
| always_additive_defer | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 20998 | 3 | force_additive | True |
| repair5f_candidate_additive_ltm | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 20998 | 3 | runtime | False |
| laur_disable | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 20998 | 3 | disabled | False |
| laur_force_additive_direct | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 20998 | 3 | force_additive | True |

## Interpretation

All replayed controls match plain LaCAM*+LTM on the parity tuple. This closes the mismatch at reproducer scope.
