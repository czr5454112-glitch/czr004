# Phase5.5 Repair5G.5.9 Learned Bounded Dual-Channel Update Policy Design

## Design

The target learned component is not a MAPF action policy and not a restart policy. It maps pre-update trace/context and C/F traffic-map state to bounded UpdateLTM parameters or safe expert mixtures:

```text
context / trace / C-F traffic state
  -> bounded alpha/rho/beta/max_flow_shield parameter policy
  -> UpdateLTM
  -> DirectedTrafficMap
  -> WeightedDistanceTable
  -> original LaCAM*/PIBT semantics unchanged
```

## Permitted Outputs

- `bounded alpha_cong_committed`
- `bounded alpha_cong_blocked`
- `bounded alpha_flow_progress`
- `bounded alpha_flow_wait_or_nonprogress`
- `bounded rho_cong`
- `bounded rho_flow`
- `bounded flow_shield_beta`
- `bounded max_flow_shield`
- `safe expert mixture weights`
- `abstention/static/additive fallback probabilities`

## Forbidden Outputs

- `agent actions`
- `PIBT priorities`
- `restart nodes`
- `h_i(v) heuristic values`
- `candidate deletion`
- `collision decisions`
- `OPEN/EXPLORED/rewrite/incumbent decisions`

## Stage Gate

This design is offline-only. Runtime claims require corrected controls, calibrated abstention, counterfactual oracle-gap evidence over the expanded lattice, deterministic export, and parity checks.
