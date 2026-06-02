# Phase5.5 Repair5G.0 Design Memo

Repair5G.0 is a diagnostic-only representation test for learning-enhanced
`UpdateLTM`. It asks whether the traffic map needs two bounded evidence
channels:

```text
C[e] = congestion / blockage / wait-risk penalty evidence
F[e] = successful goal-progress flow / corridor evidence
```

The first implementation keeps the solver intervention global and edge-level:

```text
cost(e) = clip(1 + lambda_cong * C_norm(e) - lambda_flow * F_norm(e),
               min_edge_cost,
               max_edge_cost)
```

Goal awareness enters only through the update rule. A committed move that
decreases the agent's unweighted distance to its goal updates `F`; blocked moves
update `C`; waits are split so progress exits can be penalized weakly while
non-progress exits are penalized strongly. The diagnostic does not predict
actions, priorities, restart nodes, candidate pruning, or conflict outcomes.

Boundary:

- `phase5p5_allowed=false`
- `phase6_allowed=false`
- `external/lacam2/lacam2/**` remains untouched
- PIBT legality, LaCAM* candidate generation, vertex/swap conflict handling,
  OPEN/EXPLORED/rewrite, incumbent pruning, and restart semantics remain
  unchanged
- F4-observed static candidates remain diagnostic-only

Required artifacts:

- `scripts/create_repair5g_dual_channel_candidates.py`
- `scripts/run_repair5g_dual_channel_probe.py`
- `scripts/analyze_repair5g_dual_channel_oracle.py`
- `outputs/tables/phase5p5_repair5g_dual_channel_candidate_lattice.csv`
- `outputs/reports/phase5p5_repair5g_dual_channel_*`
