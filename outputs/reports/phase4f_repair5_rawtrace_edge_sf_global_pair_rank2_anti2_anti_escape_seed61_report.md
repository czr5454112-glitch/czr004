# Phase4F Repair5 Anti-Escape Gate

- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- high-margin capture rate: `0.2594594594594595`
- avoidable additive/defer rate: `0.5621621621621622`
- mean selected-vs-additive delta: `0.01607638617055497`
- opportunity non-additive selection rate: `0.47440273037542663`
- global additive/defer rate: `0.5272331154684096`
- selected rules: `{'additive_ltm': 242, 'block_heavy': 18, 'block_light': 10, 'commit_heavy': 126, 'decay_095': 25, 'wait_heavy': 12, 'wait_light': 26}`
- decisions: `{'defer_ltm': 242, 'use_nonadditive': 217}`
- passed: `False`
- reason: `anti_escape_threshold_failed`

A pass here is required but not sufficient for runtime. It only checks that the model did not pass by escaping to additive/defer on high-margin safe non-additive opportunity samples.
