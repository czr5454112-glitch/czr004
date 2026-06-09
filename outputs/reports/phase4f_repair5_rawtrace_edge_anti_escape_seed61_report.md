# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.5351351351351351`
- avoidable additive/defer rate: `0.21621621621621623`
- mean selected-vs-additive delta: `0.06283511793527741`
- opportunity non-additive selection rate: `0.7098976109215017`
- global additive/defer rate: `0.33769063180827885`
- selected rules: `{'additive_ltm': 155, 'block_heavy': 57, 'block_light': 22, 'commit_heavy': 116, 'decay_090': 2, 'decay_095': 12, 'wait_heavy': 7, 'wait_light': 88}`
- decisions: `{'defer_ltm': 155, 'use_nonadditive': 304}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
