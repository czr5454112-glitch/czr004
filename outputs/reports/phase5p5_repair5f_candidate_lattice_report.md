# Phase5.5 Repair5F Candidate Lattice

This is a diagnostic-only bounded UpdateParams lattice for learned UpdateLTM.

## Boundary

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`
- richer_traffic_map_state_enabled: `false`

## Summary

- candidate_count: `47`
- full_cartesian_count: `375`
- sparse_vs_full_cartesian: `47 / 375`
- exact_additive_candidate_id: `additive_ltm`
- old_preset_equivalent_count: `8`
- new_candidate_count: `39`

## Old Preset Equivalents

- `additive_ltm` -> `additive_ltm`
- `block_heavy` -> `c100_b150_w100_d100`
- `block_light` -> `c100_b050_w100_d100`
- `commit_heavy` -> `c150_b100_w100_d100`
- `decay_090` -> `c100_b100_w100_d090`
- `decay_095` -> `c100_b100_w100_d095`
- `wait_heavy` -> `c100_b100_w150_d100`
- `wait_light` -> `c100_b100_w050_d100`

## Candidate Table

| candidate_id | commit | block | wait | decay | construction | old preset |
|---|---:|---:|---:|---:|---|---|
| additive_ltm | 1 | 1 | 1 | 1 | exact_additive_anchor | additive_ltm |
| c050_b100_w100_d100 | 0.5 | 1 | 1 | 1 | one_axis_alpha_commit |  |
| c075_b100_w100_d100 | 0.75 | 1 | 1 | 1 | one_axis_alpha_commit |  |
| c125_b100_w100_d100 | 1.25 | 1 | 1 | 1 | one_axis_alpha_commit |  |
| c150_b100_w100_d100 | 1.5 | 1 | 1 | 1 | one_axis_alpha_commit | commit_heavy |
| c100_b050_w100_d100 | 1 | 0.5 | 1 | 1 | one_axis_alpha_block | block_light |
| c100_b075_w100_d100 | 1 | 0.75 | 1 | 1 | one_axis_alpha_block |  |
| c100_b125_w100_d100 | 1 | 1.25 | 1 | 1 | one_axis_alpha_block |  |
| c100_b150_w100_d100 | 1 | 1.5 | 1 | 1 | one_axis_alpha_block | block_heavy |
| c100_b100_w050_d100 | 1 | 1 | 0.5 | 1 | one_axis_alpha_wait_spillover | wait_light |
| c100_b100_w075_d100 | 1 | 1 | 0.75 | 1 | one_axis_alpha_wait_spillover |  |
| c100_b100_w125_d100 | 1 | 1 | 1.25 | 1 | one_axis_alpha_wait_spillover |  |
| c100_b100_w150_d100 | 1 | 1 | 1.5 | 1 | one_axis_alpha_wait_spillover | wait_heavy |
| c100_b100_w100_d090 | 1 | 1 | 1 | 0.9 | one_axis_rho_decay | decay_090 |
| c100_b100_w100_d095 | 1 | 1 | 1 | 0.95 | one_axis_rho_decay | decay_095 |
| c075_b075_w100_d100 | 0.75 | 0.75 | 1 | 1 | two_axis_alpha_commit_alpha_block |  |
| c075_b125_w100_d100 | 0.75 | 1.25 | 1 | 1 | two_axis_alpha_commit_alpha_block |  |
| c125_b075_w100_d100 | 1.25 | 0.75 | 1 | 1 | two_axis_alpha_commit_alpha_block |  |
| c125_b125_w100_d100 | 1.25 | 1.25 | 1 | 1 | two_axis_alpha_commit_alpha_block |  |
| c075_b100_w075_d100 | 0.75 | 1 | 0.75 | 1 | two_axis_alpha_commit_alpha_wait_spillover |  |
| c075_b100_w125_d100 | 0.75 | 1 | 1.25 | 1 | two_axis_alpha_commit_alpha_wait_spillover |  |
| c125_b100_w075_d100 | 1.25 | 1 | 0.75 | 1 | two_axis_alpha_commit_alpha_wait_spillover |  |
| c125_b100_w125_d100 | 1.25 | 1 | 1.25 | 1 | two_axis_alpha_commit_alpha_wait_spillover |  |
| c100_b075_w075_d100 | 1 | 0.75 | 0.75 | 1 | two_axis_alpha_block_alpha_wait_spillover |  |
| c100_b075_w125_d100 | 1 | 0.75 | 1.25 | 1 | two_axis_alpha_block_alpha_wait_spillover |  |
| c100_b125_w075_d100 | 1 | 1.25 | 0.75 | 1 | two_axis_alpha_block_alpha_wait_spillover |  |
| c100_b125_w125_d100 | 1 | 1.25 | 1.25 | 1 | two_axis_alpha_block_alpha_wait_spillover |  |
| c075_b100_w100_d095 | 0.75 | 1 | 1 | 0.95 | decay_interaction_alpha_commit |  |
| c125_b100_w100_d095 | 1.25 | 1 | 1 | 0.95 | decay_interaction_alpha_commit |  |
| c100_b075_w100_d095 | 1 | 0.75 | 1 | 0.95 | decay_interaction_alpha_block |  |
| c100_b125_w100_d095 | 1 | 1.25 | 1 | 0.95 | decay_interaction_alpha_block |  |
| c100_b100_w075_d095 | 1 | 1 | 0.75 | 0.95 | decay_interaction_alpha_wait_spillover |  |
| c100_b100_w125_d095 | 1 | 1 | 1.25 | 0.95 | decay_interaction_alpha_wait_spillover |  |
| c075_b100_w100_d090 | 0.75 | 1 | 1 | 0.9 | decay_interaction_alpha_commit |  |
| c125_b100_w100_d090 | 1.25 | 1 | 1 | 0.9 | decay_interaction_alpha_commit |  |
| c100_b075_w100_d090 | 1 | 0.75 | 1 | 0.9 | decay_interaction_alpha_block |  |
| c100_b125_w100_d090 | 1 | 1.25 | 1 | 0.9 | decay_interaction_alpha_block |  |
| c100_b100_w075_d090 | 1 | 1 | 0.75 | 0.9 | decay_interaction_alpha_wait_spillover |  |
| c100_b100_w125_d090 | 1 | 1 | 1.25 | 0.9 | decay_interaction_alpha_wait_spillover |  |
| c075_b075_w125_d095 | 0.75 | 0.75 | 1.25 | 0.95 | conservative_decay_combo |  |
| c125_b075_w125_d095 | 1.25 | 0.75 | 1.25 | 0.95 | conservative_decay_combo |  |
| c075_b125_w125_d095 | 0.75 | 1.25 | 1.25 | 0.95 | conservative_decay_combo |  |
| c125_b125_w075_d095 | 1.25 | 1.25 | 0.75 | 0.95 | conservative_decay_combo |  |
| c075_b100_w125_d090 | 0.75 | 1 | 1.25 | 0.9 | conservative_decay_combo |  |
| c100_b075_w125_d090 | 1 | 0.75 | 1.25 | 0.9 | conservative_decay_combo |  |
| c125_b075_w100_d090 | 1.25 | 0.75 | 1 | 0.9 | conservative_decay_combo |  |
| c075_b125_w100_d090 | 0.75 | 1.25 | 1 | 0.9 | conservative_decay_combo |  |
