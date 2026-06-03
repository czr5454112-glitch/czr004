# Phase5.5 Repair5G.2 Final Interpretation

Repair5G.2 is a strong positive fresh-holdout result for flow-shielded, goal-aware dual-channel `UpdateLTM`.

The frozen final protocol used IDs 46..65 after the selector and static candidates were frozen from earlier support/development data. The fresh final grid covered:

- maps: `random-32-32-20`, `maze-32-32-4`, `warehouse-10-20-10-2-1`
- agents: `50`, `100`
- instance IDs: `46..65`
- rows: `2520 / 2520`
- missing rows: `0`
- schema errors: `0`
- solver crashes: `0`

## Core Result

The frozen selected method was `repair5g2_frozen_static_or_selector`.

```text
better / equal / worse vs LTM = 62 / 44 / 14
mean_delta_ratio_vs_ltm = -0.020112979571774988
bootstrap_probability_mean_delta_lt_0 = 1.0
ratio_worse_than_ltm_groups = 0
success_worse_than_ltm_groups = 0
```

Strict final controls passed exactly:

- additive parity
- always-additive-defer parity
- `laur_disable` parity
- direct force-additive parity
- dual-additive parity
- dual C-equivalent additive parity
- finite bounded costs

## Interpretation

G2 validates the representation more strongly than selector intelligence. The best static flow-shield candidate and the shuffled flow-shield diagnostic are close to the frozen selector on final IDs:

```text
repair5g2_best_frozen_static_candidate:
  64 / 43 / 13
  mean_delta_ratio_vs_ltm = -0.020043939351749987

repair5g2_shuffled_flow_shield_diagnostic:
  63 / 43 / 14
  mean_delta_ratio_vs_ltm = -0.019850973894158318
```

By contrast, scalar/C-equivalent congestion baselines are much weaker. This supports the flow-shield representation: successful goal-progress evidence should reduce over-penalty only on the current agent's goal-progress edges, not create a global cheap-flow bonus.

Warehouse is mostly a no-op or fallback regime. The G2 gains are driven mainly by random and maze, while warehouse mostly demonstrates that the selector/fallback can avoid obvious harm rather than that it finds large benefit.

## Boundary

IDs `46..65` are now observed and cannot be reused as untouched final evidence.

This remains diagnostic-only:

```text
phase5p5_allowed = false
phase6_allowed = false
no learned actions = true
no learned restart = true
no LaCAM*/PIBT semantic change = true
```

The correct next step is Repair5G.3 broader validation plus a learning bridge, not Phase5.5 or Phase6 promotion.
