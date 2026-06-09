# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.25483870967741934`
- avoidable additive/defer rate: `0.5290322580645161`
- mean selected-vs-additive delta: `0.008175908406188549`
- opportunity non-additive selection rate: `0.4886128364389234`
- global additive/defer rate: `0.5446194225721784`
- selected rules: `{'additive_ltm': 415, 'block_heavy': 37, 'block_light': 32, 'commit_heavy': 193, 'decay_090': 65, 'decay_095': 3, 'wait_heavy': 5, 'wait_light': 12}`
- decisions: `{'defer_ltm': 415, 'use_nonadditive': 347}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
