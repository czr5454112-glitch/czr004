# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.3387096774193548`
- avoidable additive/defer rate: `0.42258064516129035`
- mean selected-vs-additive delta: `0.013024309763773877`
- opportunity non-additive selection rate: `0.5652173913043478`
- global additive/defer rate: `0.484251968503937`
- selected rules: `{'additive_ltm': 369, 'block_heavy': 58, 'block_light': 15, 'commit_heavy': 181, 'decay_090': 30, 'decay_095': 26, 'wait_light': 83}`
- decisions: `{'defer_ltm': 369, 'use_nonadditive': 393}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
