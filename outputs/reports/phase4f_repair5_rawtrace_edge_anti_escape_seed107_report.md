# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.43783783783783786`
- avoidable additive/defer rate: `0.2756756756756757`
- mean selected-vs-additive delta: `0.04520045039782073`
- opportunity non-additive selection rate: `0.658703071672355`
- global additive/defer rate: `0.3790849673202614`
- selected rules: `{'additive_ltm': 174, 'block_heavy': 80, 'block_light': 15, 'commit_heavy': 76, 'decay_090': 33, 'decay_095': 12, 'wait_heavy': 24, 'wait_light': 45}`
- decisions: `{'defer_ltm': 174, 'use_nonadditive': 285}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
