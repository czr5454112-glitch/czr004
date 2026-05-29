# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.4918918918918919`
- avoidable additive/defer rate: `0.23783783783783785`
- mean selected-vs-additive delta: `0.06727594623294492`
- opportunity non-additive selection rate: `0.7235494880546075`
- global additive/defer rate: `0.3224400871459695`
- selected rules: `{'additive_ltm': 148, 'block_heavy': 66, 'block_light': 17, 'commit_heavy': 149, 'decay_090': 3, 'decay_095': 7, 'wait_heavy': 17, 'wait_light': 52}`
- decisions: `{'defer_ltm': 148, 'use_nonadditive': 311}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
