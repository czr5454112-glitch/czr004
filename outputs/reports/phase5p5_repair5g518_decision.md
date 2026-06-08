# Phase5.5 Repair5G.5.18 Decision

- decision: `g518_full_primary_candidate_space_improved_continue_ranker`
- rationale: Full-primary candidate-space oracle improved.
- autopsy_decision: `g517_lattice_autopsy_passed_continue_surrogate_proposal`
- proposal_decision: `surrogate_candidate_batches_selected_continue_adapter_verification`
- adapter_decision: `adapter_grammar_passed_continue_probe_batches`
- probe_batches_decision: `g518_candidate_space_improved_continue_full_primary`
- full_primary_integrity_decision: `g518_full_primary_integrity_passed_continue_oracle`
- full_primary_oracle_decision: `g518_full_primary_candidate_space_improved_continue_ranker`
- ranker_decision: `ranker_allowed_next_round`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- runtime_claim_allowed: `false`
- learned_runtime_policy_validated: `false`
- aaai_ready: `false`

## Batch Evidence

- Batch `A`: `g518_batch_candidate_space_improved_continue_full_primary`, wins `4`, mean gap `-0.00020502306599996524`
- Batch `B`: `g518_batch_candidate_space_improved_continue_full_primary`, wins `2`, mean gap `-0.002255253715999972`
- Batch `C`: `g518_batch_candidate_space_improved_continue_full_primary`, wins `2`, mean gap `-0.0013326499239999733`

G5.18 does not train or promote rankers unless executable candidate-space evidence first improves and survives full-primary confirmation.
