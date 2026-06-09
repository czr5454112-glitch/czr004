# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.2967741935483871`
- avoidable additive/defer rate: `0.5612903225806452`
- mean selected-vs-additive delta: `0.014747601645512823`
- opportunity non-additive selection rate: `0.463768115942029`
- global additive/defer rate: `0.5590551181102362`
- selected rules: `{'additive_ltm': 426, 'block_heavy': 41, 'block_light': 8, 'commit_heavy': 172, 'decay_095': 31, 'wait_heavy': 13, 'wait_light': 71}`
- decisions: `{'defer_ltm': 426, 'use_nonadditive': 336}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
