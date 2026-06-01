# Phase5.5 Repair5E.5 Final Interpretation

Date: 2026-06-01

## Decision

Repair5E.5 is a useful diagnostic result, but it is not promotable.

- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`
- learned_restart_enabled: `false`

Repair5E.5 improved the evidence quality through cross-fold support, held-out
diagnostics, threshold/risk sweeps, force-additive parity, and shuffled-label
controls. Those controls make the negative result more informative, not more
promotable.

## Evidence

Out-of-fold was weak-positive:

```text
repair5e5_crossfold_utility_reranker:
  better / equal / worse = 22 / 114 / 14
  mean_delta_ratio_vs_ltm = -0.0013255900057666681
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
```

Final holdout failed:

```text
repair5e5_crossfold_utility_reranker:
  better / equal / worse = 4 / 22 / 4
  mean_delta_ratio_vs_ltm = -0.0009245170596666741
  ratio_worse_than_ltm_groups = 2
  success_worse_than_ltm_groups = 0
```

The shuffled-label diagnostic was stronger than the real selector:

```text
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic:
  better / equal / worse = 7 / 20 / 3
  mean_delta_ratio_vs_ltm = -0.0039024738501666654
```

This is the key blocker. Repair5E.5 has not proven that learned utility
structure, rather than group bias or accidental safe choices, explains the
observed gains.

## Interpretation

The 8-preset-rule selector is not trustworthy enough for a runtime or method
claim. It can find weak signal in OOF evaluation, but final holdout does not
meet the better-than-worse and group-risk gates, and the shuffled-label control
is stronger than the real selector.

The oracle/static proxy still shows UpdateLTM headroom, so the correct response
is not to abandon learned UpdateLTM. The controlled next step is Repair5F:
bounded `UpdateParams` lattice probing inside the existing path:

```text
PIBT trace
  -> UpdateLTM
  -> DirectedTrafficMap raw_count / normalized_weight
  -> WeightedDistanceTable
  -> existing LTM guidance path
```

Repair5F remains aligned only as a diagnostic side branch. It must not become
manual per-map tuning, an exact map/agent/instance recovery table, action
prediction, learned restart, candidate pruning, conflict semantic changes, or a
richer traffic-map representation before bounded `UpdateParams` is exhausted.

## Repair5F Boundary

Repair5F may ask whether a bounded `UpdateParams` lattice has stronger
closed-loop headroom than the 8-rule preset space. A selector claim is allowed
only later, and only if held-out closed-loop metrics beat shuffled/random
diagnostics.

Current policy remains:

```text
phase5p5_allowed = false
phase6_allowed = false
```
