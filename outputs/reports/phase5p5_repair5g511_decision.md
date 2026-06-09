# Phase5.5 Repair5G.5.11 Decision

- decision: `confidence_targets_v5_failed_continue_label_design`
- integrity_decision: `full_lattice_integrity_passed`
- oracle_decision: `full_lattice_candidate_space_passed_continue_targets`
- confidence_targets_decision: `confidence_targets_v5_failed_continue_label_design`
- measured_contexts: `60`
- primary_1000_2000_stable_contexts: `60`
- candidate_space_oracle_gap_vs_g58: `-0.028445334327249994`
- oracle_beats_static_fraction: `0.8666666666666667`
- oracle_beats_additive_fraction: `1.0`
- target_label_counts: `{'stable_high_confidence_parameter_candidate': 52, 'stable_static': 8}`

G5.11 successfully completes the full observed-ID server lattice run and confirms the lattice oracle upper bound improves over G5.8. It stops before feature v3 and policy training because the confidence-target gate does not provide enough safe abstention/static/no-solution coverage. Phase5.5, Phase6, runtime learned-policy, and AAAI-ready claims remain closed.
