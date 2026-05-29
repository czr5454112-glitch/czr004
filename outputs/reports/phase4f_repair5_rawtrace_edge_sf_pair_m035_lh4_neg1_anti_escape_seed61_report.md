# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.33513513513513515`
- avoidable additive/defer rate: `0.3567567567567568`
- mean selected-vs-additive delta: `0.026065629336783788`
- opportunity non-additive selection rate: `0.6484641638225256`
- global additive/defer rate: `0.40522875816993464`
- selected rules: `{'additive_ltm': 186, 'block_heavy': 33, 'block_light': 3, 'commit_heavy': 118, 'decay_090': 17, 'decay_095': 49, 'wait_heavy': 12, 'wait_light': 41}`
- decisions: `{'defer_ltm': 186, 'use_nonadditive': 273}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
