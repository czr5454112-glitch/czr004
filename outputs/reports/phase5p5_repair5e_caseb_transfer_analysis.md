# Phase5.5 Repair5E Case-B Transfer Analysis

Date: 2026-05-31 16:41:26

Diagnostic-only. Phase5.5 allowed: `false`. Phase6 allowed: `false`.

## Paired Outcome

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| repair3_safe_runtime | 18 | 4 | 11 | 3 | -0.001980357532777798 |
| repair5d_composite_diagnostic_distilled | 18 | 1 | 12 | 5 | 0.0025935989466666395 |
| oracle_teacher_forced_best_safe_update_static_proxy | 18 | 8 | 9 | 1 | -0.010131897741666685 |

## Rule Transfer Shift

- offline validation predicted distribution: `{'additive_ltm': 215, 'block_heavy': 158, 'block_light': 59, 'commit_heavy': 174, 'decay_095': 80, 'wait_heavy': 32, 'wait_light': 44}`
- Repair5D closed-loop distribution: `{'commit_heavy': 43, 'wait_light': 2}`
- oracle/static closed-loop distribution: `{'block_heavy': 7, 'block_light': 12, 'commit_heavy': 1, 'decay_090': 5, 'wait_heavy': 4, 'wait_light': 16}`
- JS divergence Repair5D closed-loop vs offline predicted: `0.3678926460384809`
- JS divergence Repair5D closed-loop vs oracle closed-loop: `0.5703503289737799`
- Repair5D closed-loop commit_heavy share: `0.9555555555555556`

## Worse-Than-LTM Repair5D Rows

- rows: `5`
- `maze-32-32-4` a50 seed 1: delta=0.030131004359999825, rules={"commit_heavy": 3}
- `maze-32-32-4` a50 seed 3: delta=0.013170272809999828, rules={"commit_heavy": 3}
- `maze-32-32-4` a100 seed 2: delta=0.008740359889999993, rules={"commit_heavy": 3}
- `maze-32-32-4` a100 seed 3: delta=0.009993186460000025, rules={"commit_heavy": 3}
- `random-32-32-20` a100 seed 2: delta=0.004122766829999902, rules={"commit_heavy": 3}

## Feature OOD

- source: `proxy_reconstruction_from_update_log_and_map_static_features`
- rows: `45`
- mean max |z|: `76.7624481862428`
- max |z|: `76.7624481862428`
- any outside 3 sigma: `1.0`
- any outside 5 sigma: `1.0`
- top features by max |z|: `{'entropy_edge_usage': 45}`
- note: The pushed Repair5E update log did not include full runtime feature vectors; OOD values are proxy diagnostics unless full_feature_rows is nonzero.

## Repair3 vs Repair5D

- Repair3 wins while Repair5D loses rows: `2`
- non-additive but different rule rows: `18`
- Repair5D commit_heavy vs Repair3 block_light rows: `16`

## Recommendation

- selected repair: `Option 3: OOD/defer guard around the existing Repair5D distill bridge`
- reason: `Repair5D closed-loop choices collapse toward commit_heavy while the oracle/static proxy is diverse; the available OOD proxy also shows large z-score excursions, so a diagnostic defer guard is the least-stacked targeted repair.`

No Phase5.5 or Phase6 claim is made from this analysis.
