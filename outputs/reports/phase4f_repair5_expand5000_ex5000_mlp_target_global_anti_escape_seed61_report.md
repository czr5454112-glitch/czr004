# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.38064516129032255`
- avoidable additive/defer rate: `0.3741935483870968`
- mean selected-vs-additive delta: `0.026818417316147942`
- opportunity non-additive selection rate: `0.6231884057971014`
- global additive/defer rate: `0.431758530183727`
- selected rules: `{'additive_ltm': 329, 'block_heavy': 82, 'block_light': 6, 'commit_heavy': 162, 'decay_090': 45, 'decay_095': 3, 'wait_heavy': 8, 'wait_light': 127}`
- decisions: `{'defer_ltm': 329, 'use_nonadditive': 433}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
