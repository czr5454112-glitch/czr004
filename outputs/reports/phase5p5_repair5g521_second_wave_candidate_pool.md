# Repair5G.5.21 Second-Wave Candidate Pool

- decision: `second_wave_candidate_pool_passed_continue_adapter_grammar`
- raw_pool_count: `165`
- selected_candidate_count: `16`
- conservative_selected_count: `6`
- risky_selected_count: `9`
- target_context_count: `16`
- gates: `{'raw_pool_count_ge_48': True, 'selected_count_le_16': True, 'selected_count_eq_16': True, 'at_least_3_per_block': True, 'conservative_candidates_ge_2': True, 'risky_candidates_ge_2': True, 'target_contexts_eq_16': True, 'no_g521_solver_outcome_used': True}`

## Selected Blocks

- block_A_block_heavy: `4` selected
- block_B_high_beta: `4` selected
- block_C_wait_conservative: `4` selected
- block_D_decay_shield_ablation: `4` selected

Selection is deterministic and uses only G5.18/G5.20 recurrent-winner metadata plus parameter-distance diversity. No G5.21 solver outcome is used.
