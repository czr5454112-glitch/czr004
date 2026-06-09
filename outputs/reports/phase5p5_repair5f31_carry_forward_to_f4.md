# Repair5F.3.1 Carry-Forward to Repair5F.4

Status: diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false`.

## Carry-Forward Facts

- F3.1 closed exact additive parity controls:
  - `force_additive_parity_exact=true`
  - `exact_additive_candidate_parity_exact=true`
  - `laur_disable_parity_exact=true`
  - `laur_force_additive_direct_parity_exact=true`
- F3.1 preserved the runtime positive signal:
  - `repair5f_bounded_updateparam_selector_runtime` selected `c100_b100_w075_d090` on 30 / 30 final-holdout cases.
  - better / equal / worse vs `lacam_star_ltm` was `6 / 19 / 5`.
  - `mean_delta_ratio_vs_ltm=-0.0027415721339999993`.
  - `ratio_worse_than_ltm_groups=1`.
  - `success_worse_than_ltm_groups=0`.
- Runtime-vs-table audit closed with `mismatch_count=0`.
- Runtime selector and static `c100_b100_w075_d090` were metric-identical.

## Interpretation

F3.1 supports only a support-trained static bounded `UpdateParams` replacement for additive `UpdateLTM`.
It does not support a context-adaptive selection claim, because the runtime selector did not choose different candidates across contexts.

The locked F4 rule is:

```text
candidate_id = c100_b100_w075_d090
alpha_commit = 1.00
alpha_block = 1.00
alpha_wait_spillover = 0.75
rho_decay = 0.90
```

F4 must not use fresh-validation outcomes to retune this rule.

## Required F4 Boundary

- Use fresh IDs after 25 for the primary validation summary.
- Do not include support IDs `1..20`.
- Do not include F2/F3 diagnostic holdout IDs `21..25`.
- Do not modify PIBT, LaCAM*, candidate generation, pruning, conflict semantics, OPEN/EXPLORED, incumbent pruning, rewrite, or restart semantics.
- Do not introduce action prediction, learned restart, or richer LTM state.
- Keep `phase5p5_allowed=false` and `phase6_allowed=false`.
