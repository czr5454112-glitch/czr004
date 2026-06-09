# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.4648648648648649`
- avoidable additive/defer rate: `0.2594594594594595`
- mean selected-vs-additive delta: `0.05224879271854443`
- opportunity non-additive selection rate: `0.6416382252559727`
- global additive/defer rate: `0.4226579520697168`
- selected rules: `{'additive_ltm': 194, 'block_heavy': 46, 'block_light': 62, 'commit_heavy': 88, 'decay_090': 2, 'decay_095': 11, 'wait_heavy': 11, 'wait_light': 45}`
- decisions: `{'defer_ltm': 194, 'use_nonadditive': 265}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
