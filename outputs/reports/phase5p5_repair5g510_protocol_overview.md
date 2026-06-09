# Phase5.5 Repair5G.5.10 Protocol Overview

## Inputs

- G5.8 observed confidence contexts: `outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv`
- G5.9 lattice: `outputs/tables/phase5p5_repair5g59_candidate_lattice.csv`
- G5.9 audit/control/feature summaries

## Execution

The adapter maps every G5.9 `candidate_id` to bounded `UpdateParams` inside project-owned code. The probe hook applies the candidate to the same pre-update traffic snapshot and trace events, then runs a short one-shot downstream probe.

Primary budgets are 1000ms and 2000ms. A 250ms stress budget and 500ms bonus budget are included in the server/full command plan and may be run locally when affordable.

## Gates

- Adapter parity: static G5.9 candidate equals prior static flow-shield; additive G5.9 candidate equals additive LTM; C-only/F-disabled runs.
- Counterfactual oracle: report measured contexts, stable primary-pair contexts, oracle gap over static/additive, and candidate-space oracle gap versus G5.8.
- Feature v2: use runtime-safe pre-update features only.
- Targets v4: train only on stable primary-pair gold rows.
- Policy: train/evaluate only if candidate-space, target, and feature gates pass.

## Forbidden

No action prediction, priority learning, restart learning, h-values, candidate deletion, final-ID tuning, external/lacam2 changes, or runtime learned-policy claim.
