# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- high-margin capture rate: `0.18064516129032257`
- avoidable additive/defer rate: `0.6161290322580645`
- mean selected-vs-additive delta: `0.00831967929851638`
- opportunity non-additive selection rate: `0.41821946169772256`
- global additive/defer rate: `0.6338582677165354`
- selected rules: `{'additive_ltm': 483, 'block_heavy': 37, 'block_light': 19, 'commit_heavy': 105, 'decay_090': 23, 'decay_095': 35, 'wait_heavy': 2, 'wait_light': 58}`
- decisions: `{'defer_ltm': 483, 'use_nonadditive': 279}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
