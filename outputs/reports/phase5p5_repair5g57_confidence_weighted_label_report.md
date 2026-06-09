# Phase5.5 Repair5G.5.7 Confidence-Weighted Label Analysis

- default_margin_threshold: `0.005`
- default_threshold_contexts: `30`
- training_eligible_contexts: `20`
- stable_high_confidence_nonstatic_count: `11`
- stable_static_count: `9`
- abstain_to_static_count: `0`
- no_solution_abstain_count: `5`
- budget_sensitive_count: `5`
- confidence_training_gate_passed: `False`

Training remains blocked unless the default-threshold label mix has enough high-confidence nonstatic and static/abstain examples.
