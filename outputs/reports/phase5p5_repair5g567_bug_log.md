# Repair5G.5.67 Bug Log

Date: 2026-06-22 Asia/Shanghai

## Fixed In This Branch

1. BF16 softmax assignment failed in graph local attention.

   Symptom: RTX5090 Gate-1 failed with `Index put requires the source and destination dtypes match`, because CUDA autocast promoted `torch.softmax` output to Float while `weights` was BF16.

   Fix: cast softmax output back to `weights.dtype` in `src/gcst/graph_encoder.py:57`.

   Regression test: `tests/test_repair5g567_od_perceiver.py:111`.

2. BF16 graph aggregation failed in `index_add_`.

   Symptom: after the softmax fix, Gate-1 failed with `index_add_(): self (Float) and source (BFloat16) must have the same scalar type`.

   Fix: cast message tensor to accumulator dtype before `index_add_` in `src/gcst/graph_encoder.py:60`.

   Regression test: `tests/test_repair5g567_od_perceiver.py:129`.

3. Gate-2 pilot initially selected non-auditable short-budget large contexts.

   Symptom: generated full-theta registry rows were recognized, but strict fingerprint was missing when the selected context produced no LTM update checkpoint (`loop_cnt=0`, `nonzero_ltm_edges=0`).

   Fix: Gate-2 bounded pilot now defaults to auditable large tiers `2000,3000` and selects larger-budget contexts in `scripts/run_repair5g567_gate2_bounded_pilot.py:213`.

4. Remote minimal package was missing LaCAM2 submodule contents.

   Symptom: remote C++ build failed because `external/lacam2/lacam2` did not exist.

   Fix used for preflight: uploaded a shallow LaCAM2 source package at commit `61a4c40` to the remote shared disk and extracted it under `external/lacam2`.

5. Remote pytest inherited Windows-only cache/basetemp paths.

   Symptom: Linux pytest setup failed because `pytest.ini` paths under `C:/tmp/...` were interpreted as invalid relative paths.

   Fix used for preflight: remote Gate-1 launcher overrode pytest addopts/cache/basetemp with Linux paths under the Gate artifact dir.

6. Small/medium staged contexts still used non-uniform legacy budgets.

   Symptom: after the large-tier budget repair, smaller diagnostic tiers could still cycle through short internal budgets, making cross-tier evidence non-comparable.

   Fix: commit `a245b791` makes every staged G5.67 row use `solver_internal_time_limit_sec=30.0` and `process_hard_timeout_sec=60.0`; non-primary purpose arguments no longer override the uniform contract.

7. G5.67 replay applied one hard timeout to a context-batched candidate group.

   Symptom: Stage-2A `uniform30_r4` planned one row per candidate but executed additive/static/g556/actor together in one subprocess, so four rows shared a single 60s hard timeout and produced 24 infrastructure timeout rows.

   Fix: commit `65c807b7` enables `G567_REPLAY_ROW_PROCESS_ISOLATION=1` for G5.67 replay. Each planned row is launched as its own subprocess, and the row-isolation unit test verifies the four-candidate group splits into four single-row tasks.

## Existing Repairs Verified By Gates

- A5 uses OD Perceiver instead of full OD self-attention for 3000 OD tokens.
- A5/A6/A7 keep `graph_global_layers=0` for large-scale variants.
- Stage-A large-context generation avoids full C0/F0 traffic prior calls.
- `astar_v1` remains opt-in only; default traffic prior is BFS.
- Label-v5.4 A/B safety semantics and true replicate identity tests pass in local and remote P0.

## Open Risks Before Any Full Run

1. Probe runner does not visibly enforce per-process hard timeout.

   During Gate-2, a `phase1a_batch --time-limit-sec 20.0` child process ran much longer than 20 seconds before returning. The bounded wrapper still completed, but `process_hard_timeout_sec` should be enforced by the outer runner before full solver acquisition.

2. Remote provenance is incomplete in the current minimal extraction.

   The Gate logs contain `fatal: not a git repository` warnings. Full runs should use a complete clean Git checkout at the pushed commit, not a source tar extraction.

3. Gate-2 was a bounded pilot only.

   It proves the large-tier solver/materialization/A5 BF16 path on 2 contexts, not full data scalability, final training quality, or blind performance.

4. 1000-agent short-budget contexts can produce no LTM update checkpoint.

   This is not necessarily a solver bug, but exact full-theta fingerprint checks are not meaningful on rows with no update checkpoint. Future summaries should distinguish "no checkpoint to audit" from true fingerprint mismatch.

5. Stage-2A row-isolated replay still has true hard timeouts.

   After row isolation, Stage-2A `uniform30_r5` streamed `248/256` rows and observed `8` real row-level hard timeouts on selected stress contexts (`g567-tunnel-24x24-a-v0`, `g567-cross-32x32-a-v3`, `g567-connector-48x48-a-v3`). This blocks Gate-3A.

6. Stage-2A runner exited without rc or final summary.

   The `uniform30_r5` tmux session ended with no active Python/solver process, no rc file, and no final Stage-2A summary. Treat this as an infrastructure provenance failure until reproduced and fixed.
