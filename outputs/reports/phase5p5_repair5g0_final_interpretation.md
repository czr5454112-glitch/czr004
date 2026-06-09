# Phase5.5 Repair5G.0 Final Interpretation

Repair5G.0 was a clean negative result for a small global-F dual-channel candidate family.

The G0 build, parity, schema, solver-crash, and cost-bound gates passed. The diagnostic probe completed without missing rows, and the exact additive controls remained closed.

G0 does not reject dual-channel LTM in general. It tested:

```text
cost(e) = clip(1 + lambda_cong * C_norm(e) - lambda_flow * F_norm(e))
```

where the flow discount was global edge-level rather than projected through the current agent's goal direction.

Two likely problems remain:

```text
1. C-only scalar mismatch:
   committed goal-progress events updated only F in G0 dual mode.
   With alpha_flow_commit_progress=0, dual C-only candidates ignored those
   committed progress edges instead of matching scalar Repair5F.

2. Agent-agnostic global F bonus:
   a flow edge discovered by one agent became cheap for every agent, including
   agents for whom that edge was not goal-progress.
```

Therefore Repair5G.0 should be interpreted as:

```text
dual_channel_no_headroom for the narrow global-F G0 family
not a general rejection of scalar-equivalent or agent-aware dual-channel LTM
```

Mandatory boundary:

```text
phase5p5_allowed=false
phase6_allowed=false
```
