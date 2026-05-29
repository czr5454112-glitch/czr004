# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.29354838709677417`
- avoidable additive/defer rate: `0.46774193548387094`
- mean selected-vs-additive delta: `0.008058983109689968`
- opportunity non-additive selection rate: `0.5320910973084886`
- global additive/defer rate: `0.5131233595800525`
- selected rules: `{'additive_ltm': 391, 'block_heavy': 19, 'block_light': 13, 'commit_heavy': 197, 'decay_090': 8, 'decay_095': 72, 'wait_heavy': 1, 'wait_light': 61}`
- decisions: `{'defer_ltm': 391, 'use_nonadditive': 371}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
