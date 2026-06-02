# Repair5F.3.1 Parity Closure Decision

Decision: proceed to Repair5F.4 larger validation of the support-trained static
bounded UpdateParams rule.

## Closure Evidence

- force_additive_parity_exact: `true`
- exact_additive_candidate_parity_exact: `true`
- laur_disable_parity_exact: `true`
- laur_force_additive_direct_parity_exact: `true`
- runtime_selected_candidate_matches_table_policy: `true`
- runtime_updateparams_match_artifact: `true`
- support_final_leakage_false: `true`

## Runtime Result

The Repair5F.3.1 closure rerun kept the F3 interpretation intact. The runtime
selector and static `c100_b100_w075_d090` ablation were metric-identical on the
30 final-holdout cases:

- better / equal / worse: `6 / 19 / 5`
- mean_delta_ratio_vs_ltm: `-0.0027415721339999993`
- ratio_worse_than_ltm_groups: `1`
- success_worse_than_ltm_groups: `0`
- selected candidate distribution: `c100_b100_w075_d090: 30`

The selector beat the Repair5F random and shuffled-utility diagnostics and
improved over the Repair5E5 real selector on mean delta ratio. This is still
evidence for a support-trained static bounded UpdateParams replacement, not
context-adaptive selection.

## Boundary

No Phase5.5 or Phase6 permission is granted. `phase5p5_allowed=false` and
`phase6_allowed=false` remain mandatory. The next branch should validate the
static bounded UpdateParams rule at larger scope without changing LaCAM*/PIBT
semantics.
