# Repair5G.5.67 Remote Gate Report

Date: 2026-06-22 Asia/Shanghai

Branch: `codex/repair5g567-large-scale-tail-safe`

Latest pushed commit at report time: `65c807b7`

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

## Stage-3A Closure Attempt

Decision: `stage2a_blocked_no_gate3a_launch`

Remote repo:

`/root/shared-nvme/czr004-g567`

Exact remote HEAD:

`65c807b7b68b87e69c343062307baa9c0e567bdf`

Key checks completed:

- Source checkout was clean by `git status --short`.
- `external/lacam2` submodule was initialized recursively.
- Remote P0 after the latest fixes: `52 passed`.
- RTX5090 CUDA BF16 available: `true`.
- Solver binary and seed actor checkpoint were present.

Fixes pushed during this closure attempt:

- `a245b791`: enforced uniform `30.0s` solver internal budget and `60.0s` process hard timeout for every staged agent/map row.
- `65c807b7`: disabled context-level multi-candidate batching for G5.67 replay hard-timeout accounting; each planned solver row now launches as its own subprocess.

Failed Stage-2A attempts:

- `uniform30_r4`: 64 contexts, tiers `32/64/128/256`, all rows recorded `30.0s/60.0s`, but replay failed closed with `process_hard_timeout_rows=24`. Root cause was context-batched candidate execution: four planned rows shared one 60s outer timeout.
- `uniform30_r5`: row isolation was active (`candidate_count=1` in status), but the run still did not pass. It streamed `248/256` result rows, observed `8` true row-level hard timeouts, then the tmux runner exited without writing its rc file or final Stage-2A summary.

`uniform30_r5` timeout rows were concentrated on:

- `g567-tunnel-24x24-a-v0`, 64 agents, additive.
- `g567-cross-32x32-a-v3`, 256 agents, additive/static/g556.
- `g567-connector-48x48-a-v3`, 256 agents, additive/static/g556/A5 actor.

Current block:

Gate-3A was not launched. Gate-3B and full campaign remain locked. The remaining issues are true row-level solver hard timeouts on selected stress contexts and an abnormal runner termination without rc/summary provenance.
