# Phase5.5 Repair5G.5.20 Decision

- decision: `second_wave_lattice_planned_continue_local_probe`
- best_policy: `no_new_candidate_ablation`
- best_mean_solution_quality_delta_vs_static: `-0.000948564581`
- best_solution_quality_harmful_rate: `0.0`
- best_no_solution_rate: `0.383333333333`
- best_total_harmful_rate: `0.383333333333`
- best_new_candidate_selection_count: `0`
- best_new_candidate_helpful_selection_count: `0`
- best_new_candidate_harmful_selection_count: `0`
- best_new_candidate_opportunity_capture_rate: `0.0`
- static_harm_semantics_repaired: `True`
- second_wave_plan_created: `True`
- solver_run: `false`

## Interpretation

G5.18 candidate-space positive evidence remains valid. G5.19 did not fail the project direction; it showed that the current learned candidate policy ignored the new candidates. G5.20 separates solution-quality harm from no-solution/nonfinite risk, evaluates opportunity-gated policies with corrected labels, and records whether a local second-wave lattice probe is justified.

## Claim Boundaries

- phase5p5_allowed: `False`
- phase6_allowed: `False`
- aaai_ready: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
