# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.3567567567567568`
- avoidable additive/defer rate: `0.43783783783783786`
- mean selected-vs-additive delta: `0.02175787393299951`
- opportunity non-additive selection rate: `0.5836177474402731`
- global additive/defer rate: `0.43790849673202614`
- selected rules: `{'additive_ltm': 201, 'block_heavy': 44, 'block_light': 4, 'commit_heavy': 101, 'decay_090': 29, 'decay_095': 6, 'wait_heavy': 16, 'wait_light': 58}`
- decisions: `{'defer_ltm': 201, 'use_nonadditive': 258}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
