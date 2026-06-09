# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.5513513513513514`
- avoidable additive/defer rate: `0.10810810810810811`
- mean selected-vs-additive delta: `0.04511697872451627`
- opportunity non-additive selection rate: `0.8156996587030717`
- global additive/defer rate: `0.23529411764705882`
- selected rules: `{'additive_ltm': 108, 'block_heavy': 83, 'block_light': 40, 'commit_heavy': 116, 'decay_090': 15, 'decay_095': 11, 'wait_heavy': 8, 'wait_light': 78}`
- decisions: `{'defer_ltm': 108, 'use_nonadditive': 351}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
