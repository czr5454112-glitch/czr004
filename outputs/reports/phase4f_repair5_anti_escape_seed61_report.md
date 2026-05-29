# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.4648648648648649`
- avoidable additive/defer rate: `0.2`
- mean selected-vs-additive delta: `0.04699217708345323`
- opportunity non-additive selection rate: `0.6962457337883959`
- global additive/defer rate: `0.3355119825708061`
- selected rules: `{'additive_ltm': 154, 'block_heavy': 50, 'block_light': 23, 'commit_heavy': 112, 'decay_090': 7, 'decay_095': 21, 'wait_heavy': 17, 'wait_light': 75}`
- decisions: `{'defer_ltm': 154, 'use_nonadditive': 305}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
