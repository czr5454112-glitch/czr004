# Phase5.5 Repair5G.3.1 / G4 Decision

Decision: `continue_learning_bridge_offline`

## Answers

1. What exactly caused G3 strict parity failure?

`{'returncode2_no_solution_equivalent': 106, 'time_budget_sensitivity': 8}; strict differences were attributed to time-budget/return-code-2 equivalence, not semantic mismatch.`

2. Is it a true semantic mismatch or time-budget/reporting equivalence?

`true_semantic=0, reproducer_true_semantic=0`

3. Is the protocol now clean enough for a new final validation?

`True`

4. Did G4 clean validation pass, if run?

`protocol=True, representation=True, decision=flow_shield_representation_valid_selector_unclear`

5. Is static flow-shield enough?

`best_flow_shield=repair5g2_frozen_static_or_selector`

6. Does selector add value over static?

`selector_beats_static`

7. Is a learned contextual UpdateLTM selector justified?

`offline_bridge=True, runtime_integration_feasible=False`

8. Which IDs are now observed?

`IDs 1..105 are observed before G4; IDs 126..165 are observed if G4 clean validation completed.`

9. Which clean IDs are reserved next?

`IDs 166..205 or the next untouched range remain reserved for learned-selector fresh evaluation if a runtime selector is frozen.`

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- diagnostic_only: `true`
