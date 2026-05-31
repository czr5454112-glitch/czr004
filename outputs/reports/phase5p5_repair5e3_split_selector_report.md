# Phase5.5 Repair5E.3 Split Guarded Selector

- diagnostic-only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- output_space: `existing_8_rules_plus_additive_defer`

- source runtime: `artifacts\models\laur_ltm\repair5d_composite_distilled`
- output runtime: `artifacts\models\laur_ltm\repair5e3_split_guarded_selector`
- train support paths: `['outputs\\logs\\phase5p5_repair5e_caseb_preflight\\phase5p5_repair5e_caseb_preflight.jsonl', 'outputs\\logs\\phase5p5_repair5e_caseb_preflight\\phase5p5_repair5e_caseb_preflight_laur_updates.jsonl']`
- train instance ids: `[1, 2, 3]`
- eval instance ids forbidden: `[4, 5, 6, 7, 8, 9, 10, 11, 12, 13]`
- OOD stat source: `train_support_update_logs_only`

## Recovery Rules

| map | agents | rule | support | better/equal/worse | mean delta |
|---|---:|---|---:|---:|---:|
| maze-32-32-4 | 100 | block_light | 3 | 3/0/0 | -0.01617138095666674 |
| random-32-32-20 | 50 | block_light | 3 | 0/3/0 | 0.0 |
| random-32-32-20 | 100 | decay_095 | 3 | 3/0/0 | -0.01840053936999997 |
| warehouse-10-20-10-2-1 | 50 | block_light | 3 | 0/3/0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | block_light | 3 | 0/3/0 | 0.0 |
