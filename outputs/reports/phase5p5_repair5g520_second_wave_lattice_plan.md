# Phase5.5 Repair5G.5.20 Second-Wave Lattice Plan

- decision: `second_wave_lattice_planned_continue_local_probe`
- plan_created: `True`
- solver_run: `false`
- target_context_count: `16`
- budgets_ms: `[1000, 2000]`
- max_workers: `1`
- old14_controls: `all old14`
- new_candidate_cap: `16`
- observed_ids_only: `true`
- ids_166_205_untouched: `true`

## Planning Gates

`{'policy_new_opportunity_capture_rate_lt_0p20': True, 'new_candidate_harmful_selection_count_gt_0': False, 'corrected_targets_reveal_candidate_space_gain_too_sparse': False}`

## Candidate Blocks

- block_heavy: around c0p90,b1p40..1p65,w0p40..0p55,beta0p35..0p50 (cap 4)
- high_beta: around c1p20,b1p15..1p35,w0p70,beta0p55..0p65 (cap 4)
- wait_conservative: around w0p35..0p50,beta0p30..0p35 (cap 4)
- flow_decay: around dc/df combinations that reduce old-oracle regret (cap 4)

This script only plans the probe. It does not run the solver and does not reopen runtime, Phase5.5, Phase6, or AAAI claims.
