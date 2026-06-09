# Phase5.5 Repair5G.3 Protocol Overview

Repair5G.3 tests whether the G2 flow-shield result survives broader validation and whether the next useful learning step is a contextual `UpdateLTM` parameter selector.

This protocol is diagnostic-only:

```text
phase5p5_allowed = false
phase6_allowed = false
learned action policy = forbidden
learned restart = forbidden
LaCAM*/PIBT semantic changes = forbidden
```

## Split Policy

Observed before G3:

```text
IDs 1..25: support / selector training
IDs 26..45: G1/F4 development validation
IDs 46..65: G2 fresh final, now observed
```

G3 frozen broader validation uses:

```text
IDs 66..105
maps = random-32-32-20, maze-32-32-4, warehouse-10-20-10-2-1
agents = 50, 100
time_limit_sec = 3.0
ltm_max_iterations = 4
```

Learning-bridge fresh holdout remains reserved:

```text
preferred IDs = 106..125
fallback next clean range = 126..145
```

## Gate Order

1. Preserve G2 artifacts with integrity and reproducibility checks.
2. Autopsy G2 as representation vs selector vs diagnostics.
3. Run determinism/repeat stress on IDs 66..75.
4. Only if P3 gates pass, run frozen broader validation on IDs 66..105.
5. Only if P4 protocol gates pass, run time-budget and LTM-iteration stress.
6. If P4 passes, build the contextual learning-bridge dataset and offline selector diagnostics.
7. Write a final G3 decision without claiming Phase5.5 or Phase6.

## Non-Negotiable Constraints

Do not modify `external/lacam2/lacam2/**`.

Do not change:

- PIBT legality, priority inheritance, backtracking, vertex conflicts, or swap conflicts
- LaCAM* candidate generation
- child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- action selection, priority overrides, learned `h_i(v)`, edge action logits, or candidate deletion

Allowed work is limited to project-owned scripts/reports and bounded dual-channel traffic-map parameters/cost projection.

## Required Interpretation Discipline

If static flow-shield matches or beats the selector, the result is:

```text
flow_shield_representation_valid_selector_unclear
```

not an adaptive selector claim.

If a contextual selector is built, it may only select bounded `UpdateLTM`/flow-shield parameters from pre-update context features. It must not use instance ID, seed, scenario filename, held-out candidate outcomes, or final solver outcomes from the same fold as runtime features.
