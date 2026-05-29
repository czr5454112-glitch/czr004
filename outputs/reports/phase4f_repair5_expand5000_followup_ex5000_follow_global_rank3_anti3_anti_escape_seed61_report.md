# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.3419354838709677`
- avoidable additive/defer rate: `0.4129032258064516`
- mean selected-vs-additive delta: `0.013207061571385138`
- opportunity non-additive selection rate: `0.5859213250517599`
- global additive/defer rate: `0.463254593175853`
- selected rules: `{'additive_ltm': 353, 'block_heavy': 108, 'commit_heavy': 172, 'decay_090': 6, 'decay_095': 53, 'wait_light': 70}`
- decisions: `{'defer_ltm': 353, 'use_nonadditive': 409}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
