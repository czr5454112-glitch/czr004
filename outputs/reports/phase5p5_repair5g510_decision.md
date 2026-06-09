# Phase5.5 Repair5G.5.10 Decision

- decision: `lattice_adapter_smoke_passed_server_required_for_full_run`
- adapter_decision: `lattice_adapter_parity_passed`
- counterfactuals_run: `True`
- measured_contexts: `2`
- candidate_space_oracle_gap_vs_g58: `-0.015080627924999979`
- confidence_targets_decision: `confidence_targets_v4_training_gate_failed`
- policy_decision: `abstention_parameter_policy_failed_continue_features_or_lattice`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- aaai_ready: `False`
- runtime_claim_allowed: `False`
- ids_166_205_untouched: `True`

Repair5G.5.10 executes the bounded G5.9 lattice adapter path without changing LaCAM*/PIBT semantics. Policy training remains gated by candidate-space, label, and feature evidence.
