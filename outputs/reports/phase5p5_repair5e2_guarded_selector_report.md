# Phase5.5 Repair5E.2 Guarded Selector Diagnostic

- diagnostic-only = `true`
- phase5p5_allowed = `false`
- phase6_allowed = `false`
- solver_semantic_changes = `false`
- output_space = `existing_8_rules_plus_additive_defer`
- bounded_delta_updateparams = `false`

## Runtime

- source runtime: `artifacts\models\laur_ltm\repair5d_composite_distilled`
- output runtime: `artifacts\models\laur_ltm\repair5e2_guarded_oracle_aligned_selector`
- OOD guard: enabled by `--laur-ood-z-threshold`
- guard stat overrides: `entropy_edge_usage`, `has_solution_before`, `improved_last_iteration`

## Recovery Rules

| map | agents | rule | mean delta | better/equal/worse |
|---|---:|---|---:|---:|
| maze-32-32-4 | 100 | block_light | -0.01617138095666674 | 3/0/0 |
| random-32-32-20 | 50 | block_light | 0.0 | 0/3/0 |
| random-32-32-20 | 100 | decay_095 | -0.01840053936999997 | 3/0/0 |
| warehouse-10-20-10-2-1 | 50 | block_light | 0.0 | 0/3/0 |
| warehouse-10-20-10-2-1 | 100 | block_light | 0.0 | 0/3/0 |

Unsupported contexts defer to `additive_ltm`; `commit_heavy` is never introduced by the recovery layer.
