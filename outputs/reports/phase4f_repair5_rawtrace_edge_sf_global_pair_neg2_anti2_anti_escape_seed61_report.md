# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.43783783783783786`
- avoidable additive/defer rate: `0.32972972972972975`
- mean selected-vs-additive delta: `0.034749479796327344`
- opportunity non-additive selection rate: `0.5938566552901023`
- global additive/defer rate: `0.46187363834422657`
- selected rules: `{'additive_ltm': 212, 'block_heavy': 18, 'block_light': 3, 'commit_heavy': 136, 'decay_090': 6, 'decay_095': 10, 'wait_heavy': 7, 'wait_light': 67}`
- decisions: `{'defer_ltm': 212, 'use_nonadditive': 247}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
