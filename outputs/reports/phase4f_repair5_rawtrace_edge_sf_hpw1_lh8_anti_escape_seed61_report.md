# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.4648648648648649`
- avoidable additive/defer rate: `0.2702702702702703`
- mean selected-vs-additive delta: `0.05633194500537319`
- opportunity non-additive selection rate: `0.6757679180887372`
- global additive/defer rate: `0.39869281045751637`
- selected rules: `{'additive_ltm': 183, 'block_heavy': 71, 'block_light': 41, 'commit_heavy': 71, 'decay_090': 8, 'decay_095': 15, 'wait_heavy': 14, 'wait_light': 56}`
- decisions: `{'defer_ltm': 183, 'use_nonadditive': 276}`
- passed: `True`
- reason: `passed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
