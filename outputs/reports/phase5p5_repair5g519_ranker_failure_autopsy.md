# Phase5.5 Repair5G.5.19 Ranker Failure Autopsy

- ranker_decision: `ranker_ignores_new_candidates_continue_candidate_policy_design`
- best_policy: `no_new_candidate_ablation`
- new_candidate_win_contexts: `16`
- new_candidate_win_budget_pairs: `32`
- new_candidates_too_rare: `False`
- new_wins_concentrated_by_map_agent: `False`
- risk_head_overblocks_new_candidates: `False`
- candidate_space_gain_small_relative_to_noise: `True`
- fixed_new_candidate_outperforms_learned_selector: `False`
- new_candidate_budget_stable_contexts: `16`
- next_candidate_lattice_direction: `explore near recurrent G5.18 new winners with sparse map-agent targeting`
- runtime_claim_allowed: `false`

Autopsy answers the required failure questions using the reconstructed targets, seed-OOF context decisions, and per-budget oracle rows. It does not run a solver and does not reopen Phase5.5, Phase6, runtime, or AAAI claims.
