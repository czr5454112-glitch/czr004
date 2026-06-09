# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.33548387096774196`
- avoidable additive/defer rate: `0.47096774193548385`
- mean selected-vs-additive delta: `0.012829270416048236`
- opportunity non-additive selection rate: `0.5196687370600414`
- global additive/defer rate: `0.5288713910761155`
- selected rules: `{'additive_ltm': 403, 'block_heavy': 39, 'block_light': 2, 'commit_heavy': 163, 'decay_090': 14, 'decay_095': 27, 'wait_light': 114}`
- decisions: `{'defer_ltm': 403, 'use_nonadditive': 359}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
