# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.25405405405405407`
- avoidable additive/defer rate: `0.5567567567567567`
- mean selected-vs-additive delta: `0.012868440149763512`
- opportunity non-additive selection rate: `0.447098976109215`
- global additive/defer rate: `0.5708061002178649`
- selected rules: `{'additive_ltm': 262, 'block_heavy': 11, 'block_light': 7, 'commit_heavy': 93, 'decay_090': 9, 'decay_095': 26, 'wait_light': 51}`
- decisions: `{'defer_ltm': 262, 'use_nonadditive': 197}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
