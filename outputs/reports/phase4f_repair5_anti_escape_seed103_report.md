# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.4810810810810811`
- avoidable additive/defer rate: `0.1945945945945946`
- mean selected-vs-additive delta: `0.036741190777588965`
- opportunity non-additive selection rate: `0.6996587030716723`
- global additive/defer rate: `0.35947712418300654`
- selected rules: `{'additive_ltm': 165, 'block_heavy': 74, 'block_light': 32, 'commit_heavy': 94, 'decay_090': 1, 'decay_095': 46, 'wait_heavy': 4, 'wait_light': 43}`
- decisions: `{'defer_ltm': 165, 'use_nonadditive': 294}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
