# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.5081081081081081`
- avoidable additive/defer rate: `0.22702702702702704`
- mean selected-vs-additive delta: `0.05764449994726013`
- opportunity non-additive selection rate: `0.658703071672355`
- global additive/defer rate: `0.3812636165577342`
- selected rules: `{'additive_ltm': 175, 'block_heavy': 61, 'block_light': 15, 'commit_heavy': 108, 'decay_090': 7, 'decay_095': 8, 'wait_heavy': 31, 'wait_light': 54}`
- decisions: `{'defer_ltm': 175, 'use_nonadditive': 284}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
