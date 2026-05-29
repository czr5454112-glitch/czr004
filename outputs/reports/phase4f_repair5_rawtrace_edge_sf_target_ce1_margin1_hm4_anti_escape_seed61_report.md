# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.2810810810810811`
- avoidable additive/defer rate: `0.5945945945945946`
- mean selected-vs-additive delta: `0.017658009172351705`
- opportunity non-additive selection rate: `0.4402730375426621`
- global additive/defer rate: `0.5773420479302832`
- selected rules: `{'additive_ltm': 265, 'block_heavy': 24, 'block_light': 7, 'commit_heavy': 116, 'decay_090': 10, 'decay_095': 8, 'wait_heavy': 7, 'wait_light': 22}`
- decisions: `{'defer_ltm': 265, 'use_nonadditive': 194}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
