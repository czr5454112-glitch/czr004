# Repair5G.5.26 Full-Coverage Rank-Effect Policy Plan

Date: 2026-06-09

## Objective

G5.26 tests whether the G5.25 blocked/rank-effect signal survives full 60-context coverage and whether a top-k shortlist plus calibrated risk/utility selector can safely improve policy selection over the G5.24/G5.25 baselines.

## Execution Stages

1. Verify G5.25 and G5.23/G5.24 starting evidence, including closed claims, observed-ID guards, and full-primary candidate-space counts.
2. Autopsy the G5.25 partial gain: feature-group lift, top-k errors, risk calibration, subset coverage bias, and candidate reduction effects.
3. Static-check v2 logging needs. Do not change solver semantics; record exact v2 audit keys as present or explicitly unavailable.
4. Run a fresh full-coverage rank-trace probe over all 60 contexts and budgets `1000/2000`, using committed G5.23/G5.24 candidate outcome rows for the 44-candidate response-surface panel.
5. Build rank-effect v2 features with full-coverage, shortlist, failed-candidate audit/proxy, and goal-aware dual-channel rank-effect fields.
6. Build the top-k policy teacher that separates shortlist recall from final safe selection/fallback.
7. Evaluate risk-calibrated top-k policies, neural rank-effect diagnostics, constrained contextual-bandit diagnostics, and goal-aware update residual surrogates.
8. Write final policy-gap autopsy and decision with all runtime, Phase5.5, Phase6, learned-runtime, and AAAI claims closed.

## Guardrails

- Do not run or inspect IDs `166..205`.
- Do not modify `external/lacam2/lacam2/**`.
- Do not alter PIBT, LaCAM*, h-values, candidate deletion, action prediction, priority prediction, restart, OPEN/EXPLORED, rewrite, pruning, or incumbent semantics.
- Keep all generated reports and summaries carrying:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

## Validation

The required validation commands are the scripts named in `czr004_g526_after_g525_full_coverage_topk_policy_prompt.md`. PowerShell uses here-strings instead of Bash heredocs for the two inline Python validation snippets.
