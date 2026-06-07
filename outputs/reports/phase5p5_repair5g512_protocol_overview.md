# Phase5.5 Repair5G.5.12 Protocol Overview

Repair5G.5.12 is a local-PC diagnostic over existing G5.11 observed-ID artifacts.

## Question

Can candidate-level regret/ranking/harmful-risk targets provide a better offline learning object for bounded dual-channel UpdateLTM parameter scoring than the failed G5.11 context-level confidence target?

## Data

- Input lattice: `outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv`
- Candidate lattice: `outputs/tables/phase5p5_repair5g59_candidate_lattice.csv`
- Context-level v5 labels: `outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv`
- Scale: `60 contexts x 14 candidates`
- Primary budgets: `1000ms`, `2000ms`
- Train split: seeds `146..150`
- Dev split: seeds `151..155`

## Guardrails

- No solver semantic changes.
- No `external/lacam2/lacam2/**` modifications.
- No action, priority, restart, h-value, candidate deletion, or MAPF action-logit learning.
- No IDs `166..205`.
- No learned runtime policy, Phase5.5, Phase6, or AAAI-ready claim.

## Evaluation

The candidate ranker is evaluated by grouped context decisions. For each dev context, the model scores all 14 candidate rows, selects a candidate only under predicted-improvement/risk/margin gates, and otherwise falls back to `repair5g59_static_flow_shield`.

Baselines include static flow-shield, additive LTM, `repair5g59_slow_decay_high_shield`, best single train candidate, train-only majority candidate, train-only map-agent prior, random candidate, true random-feature model, true shuffled-label model, and oracle upper bound.

