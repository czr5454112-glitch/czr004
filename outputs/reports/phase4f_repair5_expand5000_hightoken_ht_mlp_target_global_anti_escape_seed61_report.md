# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.2838709677419355`
- avoidable additive/defer rate: `0.5516129032258065`
- mean selected-vs-additive delta: `0.007933625598565483`
- opportunity non-additive selection rate: `0.4616977225672878`
- global additive/defer rate: `0.5826771653543307`
- selected rules: `{'additive_ltm': 444, 'block_heavy': 21, 'block_light': 27, 'commit_heavy': 169, 'decay_090': 24, 'wait_light': 77}`
- decisions: `{'defer_ltm': 444, 'use_nonadditive': 318}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
