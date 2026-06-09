# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.3027027027027027`
- avoidable additive/defer rate: `0.3837837837837838`
- mean selected-vs-additive delta: `0.014165947998203785`
- opportunity non-additive selection rate: `0.6177474402730375`
- global additive/defer rate: `0.4139433551198257`
- selected rules: `{'additive_ltm': 190, 'block_heavy': 64, 'block_light': 21, 'commit_heavy': 75, 'decay_090': 10, 'decay_095': 53, 'wait_heavy': 15, 'wait_light': 31}`
- decisions: `{'defer_ltm': 190, 'use_nonadditive': 269}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
