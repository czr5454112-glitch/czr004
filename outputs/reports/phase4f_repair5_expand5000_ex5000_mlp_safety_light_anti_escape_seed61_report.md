# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.2903225806451613`
- avoidable additive/defer rate: `0.4870967741935484`
- mean selected-vs-additive delta: `0.011581451433142658`
- opportunity non-additive selection rate: `0.5424430641821946`
- global additive/defer rate: `0.4776902887139108`
- selected rules: `{'additive_ltm': 364, 'block_heavy': 61, 'block_light': 3, 'commit_heavy': 190, 'decay_090': 32, 'decay_095': 39, 'wait_heavy': 6, 'wait_light': 67}`
- decisions: `{'defer_ltm': 364, 'use_nonadditive': 398}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
