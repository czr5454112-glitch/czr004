# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.3027027027027027`
- avoidable additive/defer rate: `0.4594594594594595`
- mean selected-vs-additive delta: `0.05391317348717691`
- opportunity non-additive selection rate: `0.5187713310580204`
- global additive/defer rate: `0.5163398692810458`
- selected rules: `{'additive_ltm': 237, 'block_heavy': 63, 'commit_heavy': 71, 'decay_090': 15, 'decay_095': 24, 'wait_heavy': 12, 'wait_light': 37}`
- decisions: `{'defer_ltm': 237, 'use_nonadditive': 222}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
