# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.0`
- avoidable additive/defer rate: `1.0`
- mean selected-vs-additive delta: `0.0`
- opportunity non-additive selection rate: `0.0`
- global additive/defer rate: `1.0`
- selected rules: `{'additive_ltm': 459}`
- decisions: `{'defer_ltm': 459}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
