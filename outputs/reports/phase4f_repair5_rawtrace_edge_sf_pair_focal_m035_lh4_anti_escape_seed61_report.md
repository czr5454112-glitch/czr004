# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.2756756756756757`
- avoidable additive/defer rate: `0.43243243243243246`
- mean selected-vs-additive delta: `0.013605305297136973`
- opportunity non-additive selection rate: `0.5631399317406144`
- global additive/defer rate: `0.47058823529411764`
- selected rules: `{'additive_ltm': 216, 'block_heavy': 36, 'block_light': 5, 'commit_heavy': 97, 'decay_090': 24, 'decay_095': 39, 'wait_heavy': 26, 'wait_light': 16}`
- decisions: `{'defer_ltm': 216, 'use_nonadditive': 243}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
