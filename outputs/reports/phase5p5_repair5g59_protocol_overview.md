# Phase5.5 Repair5G.5.9 Protocol Overview

G5.9 is an observed-ID offline diagnostic phase. It uses the tracked G5.8 artifacts as immutable input evidence and writes new G5.9 artifacts separately.

## Inputs

- G5.8 confidence targets and summaries.
- G5.8 performance-safe feature matrix.
- G5.8 offline safe-mixture train/eval summaries.
- G5.6/G5.8 counterfactual update labels used to score observed contexts.

## Outputs

- G5.8 offline eval autopsy.
- Corrected semantic controls with true random-feature and shuffled-label trained models.
- Feature signal quality audit.
- Bounded goal-aware dual-channel UpdateLTM candidate lattice.
- Counterfactual probe plan and server-required status if local execution cannot evaluate the expanded lattice.
- Confidence targets v3 with feasibility/abstention classes.
- Two-head abstention-aware offline policy train/eval.
- Learned bounded dual-channel UpdateLTM design.
- Final G5.9 decision summary.

## Gates

- Required G5.8 artifacts must exist or G5.9 stops with `missing_g58_artifacts_stop`.
- Corrected controls must distinguish trained random-feature/shuffled-label models from random candidate baselines.
- No-solution and longer-budget labels train only the feasibility/abstention head.
- Expanded lattice candidates must remain bounded UpdateLTM-only candidates.
- If local compute cannot execute lattice counterfactuals, the decision must record server-required status rather than infer oracle-gap evidence.
- IDs 166..205 remain untouched.

## Closed Claims

`phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`, and `runtime_claim_allowed=false` remain mandatory throughout G5.9.
