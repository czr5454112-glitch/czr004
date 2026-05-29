# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.36774193548387096`
- avoidable additive/defer rate: `0.4483870967741935`
- mean selected-vs-additive delta: `0.01304037981223101`
- opportunity non-additive selection rate: `0.5817805383022774`
- global additive/defer rate: `0.45931758530183725`
- selected rules: `{'additive_ltm': 350, 'block_heavy': 29, 'block_light': 1, 'commit_heavy': 254, 'decay_090': 4, 'decay_095': 13, 'wait_light': 111}`
- decisions: `{'defer_ltm': 350, 'use_nonadditive': 412}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
