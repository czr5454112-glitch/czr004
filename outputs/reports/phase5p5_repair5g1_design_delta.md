# Phase5.5 Repair5G.1 Design Delta

Repair5G.1 changes the diagnostic question from "does a global flow bonus help?" to "does dual-channel LTM help after C-channel scalar equivalence and agent-aware projection are closed?"

## Delta From G0

G0:

```text
committed progress -> F only
cost(e) = clip(1 + lambda_C * C(e) - lambda_F * F(e))
```

G1:

```text
committed progress -> C and optionally F
scalar-equivalent C-only candidates match Repair5F bounded UpdateParams
goal_projection_mode in {none, agent_progress, flow_shield}
```

## New C-Channel Semantics

Committed progress events now support:

```text
C[e] += alpha_cong_commit_progress
F[e] += alpha_flow_commit_progress * progress
```

Committed non-progress events remain:

```text
C[e] += alpha_cong_commit_nonprogress
```

Scalar-equivalent C-only candidates set both committed C alphas to the scalar `alpha_commit`, set wait C alphas to scalar `alpha_wait_spillover`, set `rho_cong_decay` to scalar `rho_decay`, and set `lambda_flow=0`.

## New Cost Projection Modes

```text
none:
  legacy G0 global edge-level formula

agent_progress:
  subtract F only when the traversed edge reduces the current agent's
  unweighted distance to its own goal

flow_shield:
  never makes an edge cheaper than base cost;
  F only reduces the C penalty on current-agent progress edges
```

This remains guidance-only. It does not alter PIBT legality, conflict handling, candidate generation, LaCAM* search, restart semantics, action prediction, or learned priority control.

Mandatory boundary:

```text
phase5p5_allowed=false
phase6_allowed=false
```
