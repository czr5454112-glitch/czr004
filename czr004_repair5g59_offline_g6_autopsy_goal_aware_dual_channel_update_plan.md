# Repair5G.5.9 Offline G6 Autopsy + Goal-Aware Dual-Channel Update Plan

## Objective

G5.8 moved the blocker from "cannot train" to "trained, but not safely better than controls." G5.9 diagnoses that failure without changing LaCAM*/PIBT semantics, then prepares the next safe learning step: an abstention-aware and eventually bounded goal-aware dual-channel UpdateLTM policy.

## Carry-Forward Facts

- G5.8 confidence expansion passed with 60 measured contexts and 40 primary 1000/2000 ms stable contexts.
- G5.8 training used 40 eligible rows, split into 20 train and 20 dev rows.
- The G5.8 model had only two classes: one nonstatic flow-shield candidate and the static flow-shield candidate.
- Mean selected score improved weakly over static and additive, but the safe learned-policy gate failed.
- The G5.8 random/shuffled gate names need correction because the eval path used candidate controls, not true trained random-feature or shuffled-label models.
- No-solution and longer-budget cases were classified but not trained as a feasibility/abstention head.
- IDs 166..205 remain untouched.
- `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`, and `runtime_claim_allowed=false`.

## G5.9 Work Items

1. Verify all required G5.8 artifacts before analysis.
2. Write the G5.8 final interpretation and G5.9 protocol overview.
3. Autopsy the G5.8 offline eval: confusion, harmful/helpful rows, calibration, coverage-risk, and failure attribution.
4. Train and evaluate corrected controls: true random-feature and shuffled-label models, plus candidate and train-only priors.
5. Audit feature signal quality, leakage risk, train/dev shift, and ablations.
6. Create a bounded UpdateLTM-only goal-aware dual-channel lattice.
7. Plan counterfactual probes for the expanded lattice and record server-required status if local execution cannot produce lattice outcomes.
8. Create confidence targets v3 with feasibility/abstention classes.
9. Train and evaluate a two-head abstention-aware offline policy.
10. Write a direct learned bounded dual-channel UpdateLTM policy design.
11. Write the final G5.9 decision ledger.

## Non-Negotiable Boundaries

- Do not modify `external/lacam2/lacam2/**`.
- Do not change solver semantics, candidate generation, conflicts, PIBT priority inheritance, OPEN/EXPLORED, rewrite, incumbent handling, restart behavior, or runtime integration.
- Do not output actions, priorities, h-values, restart choices, or candidate deletion.
- Do not use final full-run outcomes as per-update labels.
- Do not claim Phase5.5, Phase6, AAAI-ready status, or runtime readiness.
