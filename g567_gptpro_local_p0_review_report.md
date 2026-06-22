# G5.67 local P0 review report for GPT Pro

Date: 2026-06-22

Worktree: `C:\PROGRAMING\czr004-g567`

Branch: `codex/repair5g567-large-scale-tail-safe`

Base HEAD: `43c9bd2a`

Status: local-only repair and tests. No server run, no large-scale context generation, no 48h training, no push.

## Executive summary

GPT Pro's previous judgment was accepted: the earlier unit tests supported the direction of Label-v5.4 and A5, but did not justify launching remote large-scale generation or long GPU training.

This local pass addresses the main P0 issues GPT Pro called out:

1. Repeat identity no longer uses modified `horizon_id`.
2. A* no longer silently replaces BFS in `traffic_prior`.
3. Context validity generation no longer materializes full C0/F0 traffic prior for every generated context.
4. A5 tests now check last-token gradient, OD permutation invariance, masked padding, production-shape forward/backward, and graph global attention config.
5. Label-v5.4 keeps strict joint labels, but actor primary training can use Pareto-safe `primary_safe_AB` candidates instead of only `joint_positive_AB`.

Important: this is still not evidence that the full 3000-agent training run is feasible. It only shows the local P0 fixes compile and pass focused tests.

## Local changes made

### 1. Repeat identity repaired

Problem found by GPT Pro: the previous repeat implementation changed `horizon_id` to values like `..._rep01`. Since G5.66/G5.67 grouping uses `map/agents/seed/budget/horizon_id`, that makes repeats look like different scientific contexts.

Current behavior:

- `horizon_id` remains exactly `ctx.horizon_id`.
- Added `scientific_horizon_id`.
- Added `solver_execution_id = horizon_id|repXX`.
- Added and propagated `plan_row_id`, `replicate_id`, `replicate_group_id`.
- `replicate_group_id` is based on map, assignment hash, theta identity, budget, and LTM iterations.
- `audit_results` prefers `plan_row_id`; falls back to replicate-aware keys; marks ambiguous fallback as `ambiguous_context_method_requires_plan_row_id`.
- `build_three_tier_pairs` includes `replicate_id` in grouping so repeated rows are not overwritten, while all rows still share the same scientific horizon and replicate group.
- `run_replay_phase` executes repeat phases per replicate shard to avoid the older executor's method-level de-duplication.

Key code:

- `scripts/run_repair5g567_strict_pipeline.py:1029` `add_plan_row`
- `scripts/run_repair5g567_strict_pipeline.py:1175` `audit_results`
- `scripts/run_repair5g567_strict_pipeline.py:1316` `group_key`
- `scripts/run_repair5g567_strict_pipeline.py:1555` `run_replay_phase`

Test:

- `tests/test_repair5g567_repeat_identity.py:71`

### 2. Label-v5.4 primary training widened but labels preserved

Kept:

- `safe_A/B/C`
- `primary_safe_AB`
- `stretch_safe_ABC`
- `joint_positive_AB`
- `joint_positive_ABC`
- single-run boundary rows remain uncertain and cannot become stable safe.

Changed:

- `labelv54_positive` remains `joint_positive_AB`.
- Added `pareto_safe_AB`.
- Added `labelv54_primary_training_candidate`.
- Primary actor training uses Pareto-safe `primary_safe_AB` candidates, not only strict `joint_positive_AB`.
- This covers the case GPT Pro mentioned: strong gain vs additive, no quality harm vs static-flow, but not a statistically significant static-flow gain.

Medoid target:

- Still uses a real executed theta, not arithmetic averaging.
- Source candidates are Pareto-safe `primary_safe_AB` candidates when available.
- Theta distance uses legal parameter span normalization.

Key code:

- `scripts/run_repair5g567_strict_pipeline.py:1742` `create_labelv54_from_pairs`
- `scripts/run_repair5g567_strict_pipeline.py:1981` `actor_examples_from_labelv54`

Tests:

- `tests/test_repair5g567_labelv54.py`
- Especially `tests/test_repair5g567_labelv54.py:80`

### 3. A* changed from silent replacement to versioned opt-in

Problem: A* can choose different equal-length shortest paths than BFS. Since C0/F0 traffic prior is built from path edge counts, that changes input semantics, not just speed.

Current behavior:

- Default remains `routing_backend="bfs"`.
- A* is available only as `routing_backend="astar_v1"`.
- BFS summary reports `traffic_prior_v1_bfs`.
- A* summary reports `traffic_prior_v2_astar`.
- Tests check path found, path length, legal edges, start/end, no loops, determinism, feature drift metrics, and a small performance smoke benchmark.

Key code:

- `src/gcst/traffic_prior.py:107` `shortest_path`
- `src/gcst/traffic_prior.py:112` `compute_traffic_prior`
- `src/gcst/traffic_prior.py:153` `traffic_prior_version`

Tests:

- `tests/test_repair5g567_traffic_prior_backends.py:48`

### 4. Context generation and feature materialization decoupled

Problem: generating every valid context and immediately calling full `compute_traffic_prior` causes 3000-agent generation to stall.

Current behavior:

- Stage A context generation:
  - computes connected components;
  - samples unique starts/goals within the same component;
  - writes map/scenario/assignment/hash;
  - does not compute full C0/F0 path-based traffic prior.
- Stage B feature materialization:
  - still happens later in `context_from_manifest_row`;
  - only contexts that are actually loaded for replay/training pay the full traffic-prior cost.

Important bug found during this change:

- Removing path materialization initially made `assignment["distances"]` empty.
- `write_scenario` writes rows using `zip(starts, goals, distances)`.
- Empty `distances` would silently produce a scenario file with only the header and zero agents.
- Fixed by writing Manhattan lower-bound distances with `distance_mode = manhattan_lower_bound_no_path_materialization`.
- Added test that parses the generated scenario and asserts row count equals `agent_count`.

Key code:

- `scripts/run_repair5g567_strict_pipeline.py:484` `make_generated_contexts`
- `scripts/run_repair5g567_strict_pipeline.py:775` `context_from_manifest_row`

Test:

- `tests/test_repair5g567_context_generation.py:13`

### 5. A5 OD Perceiver and graph-side attention audit

A5/A6/A7 actor configs now include:

- OD Perceiver latent cross-attention.
- `graph_global_layers=0` for A5/A6/A7, avoiding full-node Transformer global attention on large maps.
- A5 uses all OD tokens via latent cross-attention; no truncation logic was added.

New tests:

- old ODSetEncoder branch is not called;
- last valid OD token has nonzero gradient;
- valid OD pair permutation keeps theta stable;
- masked padding changes do not affect theta;
- production-shaped A5 config runs forward/backward with a mixed 64/1000/3000-agent batch;
- A5/A6/A7 all have `graph_global_layers == 0`.

Key code:

- `src/gcst/dual_stream_graph_actor.py:36` A5/A6/A7 config
- `src/gcst/dual_stream_graph_actor.py:221` `_od_repr`

Tests:

- `tests/test_repair5g567_od_perceiver.py:52`
- `tests/test_repair5g567_od_perceiver.py:95`
- `tests/test_repair5g567_od_perceiver.py:111`

### 6. Critic calibration gate made stricter

Previous local version only required weak conditions such as Brier skill > 0.

Current gate additionally records/checks:

- per-fold regression positive counts;
- per-agent-tier regression positive counts;
- per-map-family regression positive counts;
- AUPRC lift vs prevalence;
- recall at fixed FPR 0.05;
- q90/q95 empirical coverage;
- explicit `calibration_blockers`, including `insufficient_tail_events_for_calibration`.

This should avoid reporting a calibrated critic from a pretty aggregate Brier score when tail events are too sparse.

Key code:

- `scripts/run_repair5g567_strict_pipeline.py:2539` `train_distributional_outcome_ensemble`

### 7. 3000-agent memory smoke made stricter

The smoke artifact now:

- runs A5 forward and backward;
- uses CUDA BF16 autocast when on CUDA;
- records `cuda_peak_memory_bytes`, elapsed time, and samples/sec;
- records `graph_global_layers` and whether full-node quadratic graph attention is disabled.

Important: this has not been run on RTX5090 yet.

Key code:

- `scripts/run_repair5g567_strict_pipeline.py:853` `write_3000_agent_memory_smoke`

### 8. Synthetic empty map name bug fixed

Problem: names like `g567-large-empty-128x128-a` did not start with `empty`, so fallback synthetic map generation could treat them as random obstacle maps.

Fix:

- `_synthetic_obstacle` now treats any token `empty` in the map name as empty.

Key code:

- `src/gcst/map_hash.py:63`

## Validation performed locally

Compile:

```powershell
python -m py_compile scripts\run_repair5g567_strict_pipeline.py src\gcst\dual_stream_graph_actor.py src\gcst\traffic_prior.py src\gcst\map_hash.py
```

Result: passed.

Focused tests:

```powershell
python -m pytest tests\test_repair5g567_labelv54.py tests\test_repair5g567_od_perceiver.py tests\test_repair5g567_repeat_identity.py tests\test_repair5g567_traffic_prior_backends.py tests\test_repair5g567_context_generation.py tests\test_repair5g566_three_tier.py -q
```

Result:

```text
25 passed in 10.46s
```

Additional individual checks also passed:

- `tests\test_repair5g567_traffic_prior_backends.py -q`
- `tests\test_repair5g567_context_generation.py -q`
- `tests\test_repair5g566_three_tier.py -q`

## Current changed files

Tracked modifications:

- `src/gcst/dual_stream_graph_actor.py`
- `src/gcst/map_hash.py`
- `src/gcst/traffic_prior.py`

New files:

- `czr004_g567_large_scale_tail_safe_direct_actor_plan.md`
- `scripts/run_repair5g567_strict_pipeline.py`
- `scripts/server_start_repair5g567_full.sh`
- `tests/test_repair5g567_context_generation.py`
- `tests/test_repair5g567_labelv54.py`
- `tests/test_repair5g567_od_perceiver.py`
- `tests/test_repair5g567_repeat_identity.py`
- `tests/test_repair5g567_traffic_prior_backends.py`

Ignored for evidence:

- `.tmp_g567_smoke/` is old failed local dry-run output. It is not counted as a passed artifact.

## What is still not validated

Do not treat this as approval to launch the server run yet.

Still missing:

1. Real solver repeat smoke proving the executor returns separate rows for repeated identical scientific pairs.
2. 3000-agent CUDA BF16 forward/backward peak memory on RTX5090.
3. Full large-map graph memory and throughput report.
4. 10,000 OD-pair BFS/A* benchmark across multiple map families.
5. Feature drift matrix for A* vs BFS on real generated contexts.
6. Per-map-family and per-agent-tier 3000-agent distribution audit.
7. Actual large-scale context generation after the Stage A/B split.
8. Long GPU actor training.

## Requested GPT Pro review focus

Please review these points before any server action:

1. Is the repeat repair scientifically correct now that `horizon_id` stays unchanged and `replicate_id/plan_row_id` carry execution identity?
2. Is splitting repeat execution by replicate shard acceptable, given the older executor de-duplicates methods within one context/horizon group?
3. Is `labelv54_primary_training_candidate = primary_safe_AB + A/B quality-safe + Pareto-safe` the right training set, while keeping `joint_positive_AB` as the strict positive label?
4. Is Manhattan lower-bound distance acceptable for MovingAI scenario files during Stage A validity generation, given full C0/F0 paths are deferred to Stage B?
5. Is `traffic_prior_v2_astar` as opt-in backend sufficient, or should A* stay test-only until a larger benchmark report exists?
6. Are the A5 tests enough for local approval, assuming RTX5090 BF16 memory smoke is still required before long training?

## Current operational decision

Recommended current decision:

```text
continue_local_review_only
do_not_start_server_generation
do_not_start_solver_label_collection
do_not_start_48h_gpu_training
do_not_push_until_review_approved
```
