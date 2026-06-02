# Repair5F.3.1 Parity Closure Decision

Repair5F.3.1 closed the runtime additive parity controls for the same
final-holdout scope used by Repair5F.3.

## Evidence

- Closure eval rows: `360 / 360`, with `missing_rows = 0` and no schema errors.
- `force_additive_parity_exact = true`
- `exact_additive_candidate_parity_exact = true`
- `laur_disable_parity_exact = true`
- `laur_force_additive_direct_parity_exact = true`
- Runtime-vs-table audit mismatch count: `0`
- `runtime_selected_candidate_matches_table_policy = true`
- `runtime_updateparams_match_artifact = true`

The runtime selector again selected `c100_b100_w075_d090` on all 30 final
holdout cases. Its closure metrics were 6 better, 19 equal, and 5 worse
versus additive LTM, with mean delta ratio `-0.0027415721339999993`,
`ratio_worse_than_ltm_groups = 1`, and `success_worse_than_ltm_groups = 0`.
The static `c100_b100_w075_d090` ablation was metric-identical.

## Decision

Proceed to Repair5F.4 larger validation of support-trained static bounded
UpdateParams.

This is not evidence for context-adaptive UpdateParams selection. It is not
Phase5.5 or Phase6 permission. `phase5p5_allowed = false` and
`phase6_allowed = false` remain mandatory.
