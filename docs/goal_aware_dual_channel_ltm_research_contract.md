# Goal-Aware Dual-Channel LTM Research Contract

This document is the permanent project-level contract for the G5.62 real-label goal-aware graph actor line.

<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_BEGIN -->
## Goal-aware dual-channel LTM representation floor

This block is a project-level research contract. It is a minimum information
floor for any primary production actor in the goal-aware dual-channel LTM line,
not an architecture ceiling.

The primary production actor must consume, in its actual forward pass:

- physical graph topology
- actual paired starts/goals
- paired OD tokens
- directed C0 congestion prior
- directed F0 goal-progress prior
- solver budget
- LTM iteration budget

The primary output remains one continuous bounded solver-facing UpdateParams
theta per MAPF instance. That theta is fixed for the complete solver run while
the ordinary trace-driven C/F traffic maps continue to update online.

G5.62 is explicitly not DAgger. The project must not learn agent actions,
query an expert for learner-visited action labels, aggregate state-action
trajectories, learn priority ordering, learn restart selection, switch theta
during a run, or deploy a stored candidate/codebook selector.

Forbidden regressions:

- agent action imitation
- DAgger or learner-state expert action aggregation
- learned priority ordering
- learned restart selection
- runtime-varying theta
- candidate-ID retrieval or codebook selection as the production method
- scalar-only primary actor

Allowed extensions include richer local/global graph attention, OD-to-graph or
OD-to-edge cross-attention, separate C and F streams, hierarchical graph/raster
fusion, field-group theta heads, safe residual subspaces, uncertainty/trust
heads, and self-supervised pretraining. Scalar features are supplemental
controls or auxiliary inputs only; a scalar-only model is never the primary
goal-aware dual-channel actor.

Every future round claiming a goal-aware graph actor must record:

- actual node tensor count and dimensions
- actual directed edge tensor count and dimensions
- actual paired OD token count
- actual C0 tensor nonzero rate
- actual F0 tensor nonzero rate
- forward-hook evidence for graph, OD, C, F, scalar, fusion, and theta heads
- nonzero graph, OD, C stream, F stream, fusion, and theta-head gradients
- batch-composition, node-order, and agent-order invariance
- paired-goal shuffle, C0, F0, topology, and scalar-shortcut interventions
<!-- GOAL_AWARE_DUAL_CHANNEL_LTM_REPRESENTATION_FLOOR_END -->
