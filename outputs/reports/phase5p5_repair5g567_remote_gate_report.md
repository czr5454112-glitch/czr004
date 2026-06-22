# Repair5G.5.67 Remote Gate Report

Date: 2026-06-22 Asia/Shanghai

Branch: `codex/repair5g567-large-scale-tail-safe`

Latest pushed commit at report time: `fb3af544`

Remote instance: RTX5090, 32 GB VRAM, Ubuntu 24.04, PyTorch image.

## Scope

Executed only the GPT Pro approved scope:

- Gate-1 remote preflight.
- Gate-2 bounded pilot after Gate-1 passed.

Not executed:

- 100k-context full generation.
- Million-row solver acquisition.
- 48h training campaign.
- Final blind panel construction or access.
- `astar_v1` as primary traffic-prior backend.

## Gate-1 Result

Decision: `gate1_pass`

Artifact dir:

`/root/shared-nvme/g567_gate_work/artifacts_gate1_20260622_173238`

Local evidence copy:

`outputs/evidence/phase5p5_repair5g567_remote_gates/gate1_20260622_173238`

Key checks:

- Remote P0: `27 passed`.
- Default traffic prior remained BFS: `traffic_prior_v1_bfs`.
- 3000-agent Stage-A family distribution did not collapse: `large_empty=1`, `large_maze=1`, `large_warehouse=2`.
- Stage-A generation did not call full traffic prior: `traffic_prior_calls=0`.
- Manhattan scenario-distance consumer parity passed: solver lower bound, makespan, sum-of-loss, and ratio matched exact-distance scenario output.
- Exact real-solver replicate preservation passed: 3 same-pair real solver runs, all return code `0`.
- RTX5090 BF16 A5 throughput passed:
  - 64x64: 3000 agents, 4096 nodes, 16128 edges, 6.864 sec, peak 986082304 bytes.
  - 96x96: 3000 agents, 9216 nodes, 36480 edges, 13.733 sec, peak 3317451264 bytes.
  - large/small elapsed ratio: `2.0006409091160897`.
  - A5 used OD Perceiver and `graph_global_layers=0`.

## Gate-2 Result

Decision: `gate2_bounded_pilot_pass`

Artifact dir:

`/root/shared-nvme/g567_gate_work/artifacts_gate2_20260622_175228`

Local evidence copy:

`outputs/evidence/phase5p5_repair5g567_remote_gates/gate2_20260622_175228`

Bounded pilot details:

- Generated contexts: `76`.
- Selected contexts: `2`.
- Agent tiers: `2000`, `3000`.
- Selected budgets: `8000 ms`, `20000 ms`.
- Families: `large_maze=1`, `large_room=1`.
- Blind split constructed: `false`.
- Forbidden actions flags: all `false`.

Solver replay checks:

- Planned rows: `8`.
- Executed rows: `8`.
- Additive rows present: `2`.
- Static-flow rows present: `2`.
- g556 rows present: `2`.
- Generated full-theta registry smoke rows: `2`.
- Candidate recognized rate: `1.0`.
- Exact materialization rate: `1.0`.
- Identity retention rate: `1.0`.
- Scenario hash match rate: `1.0`.
- Replay decision: `g567_three_tier_replay_materialized`.

A5 BF16 large-context check:

- Agent count: `3000`.
- Map: `g567-large-room-128x128-a-v2`.
- Map family: `large_room`.
- Graph nodes: `16133`.
- Graph edges: `63516`.
- OD tokens: `3000`.
- Hidden dim: `256`.
- Latent tokens: `96`.
- `graph_global_layers=0`.
- Forward and backward executed under CUDA BF16 autocast.
- Elapsed: `25.7799653429538 sec`.
- Peak CUDA allocated memory: `8386809856 bytes`.

## Notes

The remote run directory was a minimal source extraction, not a full Git checkout. This caused provenance warnings in tmux logs:

`fatal: not a git repository`

The source branch itself was pushed to GitHub, and local evidence artifacts were pulled back. Before any full campaign, the remote runner should use a complete clean Git worktree so provenance logs are not degraded.
