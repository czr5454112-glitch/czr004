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

8. G5.67 row-isolated replay still used the old static-flow counterfactual-probe path.

   Symptom: Stage-2A `uniform30_r5` reported additive/static/g556/A5 hard timeouts near 60.8-61.3s, but inspection showed the subprocess primary method was still static-flow with a counterfactual candidate callback. A "candidate_count=1" row was isolated by process, but it was not a direct additive/static/g556/A5 primary solver execution.

   Fix: `scripts/run_repair5g567_strict_pipeline.py` now executes `direct_exact_solver_row`: `--method` is the row's `materialized_method`, the registry is passed only to materialize generated theta, and no `--repair5g-counterfactual-update-probe-jsonl` callback is passed. Direct rows are marked `counts_as_exact_labelv54_solver_row`; counterfactual probe rows are marked diagnostic-only and do not count as exact labels.

   Regression test: `tests/test_repair5g567_direct_exact.py`.

9. Counterfactual probe diagnostics could consume a second full budget.

   Symptom: the old path could run a 30s outer static-flow solve and then launch an independent 30s counterfactual probe, producing the observed 60s hard-timeout pattern.

   Fix: diagnostic probe budget is capped to <=5000 ms in `scripts/repair5g549_common.py`, and C++ clips the effective probe budget to the parent deadline remaining time minus a guard. If no safe time remains, the probe row records `probe_skipped_parent_deadline=true` instead of launching another solver.

10. C++ LTM could do update/callback/cost-audit work after the solver deadline.

   Symptom: after `one_shot.solve`, `solve_with_ltm` still proceeded into UpdateLTM/callback work, and `phase1a_batch` always ran full `traffic_map.cost_audit(&instance)`.

   Fix: `cpp/ltm/ltm.cpp` now breaks immediately after a post-solve parent deadline expiry while preserving incumbent/basic stats. In perf mode, `cpp/tools/phase1a_batch.cpp` skips full cost audit after that deadline and records phase timings (`instance_load_ms`, `dist_table_ms`, `outer_solve_ms`, `update_ms`, `callback_ms`, `counterfactual_probe_ms`, `cost_audit_ms`, `output_write_ms`).

11. Stage-2A tmux execution relied on ad hoc runner finalization.

   Symptom: `uniform30_r5` ended without rc and without a final summary, leaving no atomic provenance for success/failure.

   Fix: added `scripts/server_start_repair5g567_stage2a_direct_exact.sh`, which requires `G567_EXPECTED_HEAD`, writes rc and atomic final summary on normal exit/fail-closed/exception/SIGTERM, records forbidden full-run actions as false, and writes stale-marker evidence if a previous run died without final summary.

12. Full launcher did not have a fresh manual GPT-Pro approval barrier.

   Symptom: `scripts/server_start_repair5g567_full.sh` had source/disk gates, but if invoked after technical gates it would proceed directly into 100k context generation and the full campaign. This was too easy to misinterpret as "all automated gates passed, so continue."

   Fix: full launch now requires `G567_FULL_MANUAL_APPROVAL` to exactly equal `APPROVE_G567_FULL_$(git rev-parse HEAD)`. Without that fresh user-provided token it exits with decision `g567_full_campaign_waiting_for_manual_gptpro_review`. Codex must not set, guess, or generate this variable.

   Regression test: `tests/test_repair5g567_full_manual_approval.py`.

13. Sparse checkout was not treated as an incomplete source checkout.

   Symptom: the RTX5090 worktree was sparse and excluded `artifacts/models/gcst/`, so the tracked G5.65 seed actor checkpoint was absent and Stage-2A failed closed as `stage2a_blocked_missing_seed_actor_checkpoint`. The existing source-state gate checked HEAD, dirty status, and submodules, but did not reject sparse checkout.

   Fix: `classify_source_state` now records and rejects `core.sparseCheckout=true` with `sparse_checkout_enabled`; the full launcher also refuses sparse checkout before any full command can run.

   Regression test: `tests/test_repair5g567_source_state_gate.py`.

14. Stage-2A default context pool under-sampled the 256-agent diagnostic tier.

   Symptom: with the default 64 contexts and 384 context pool, the RTX5090 Stage-2A rerun found only 13 valid tier-256 contexts while the balanced 4-tier diagnostic requires 16 per tier, so it failed before solver execution with `not enough Stage-2A contexts for tier 256: 13 < 16`.

   Fix: Stage-2A default context pool is now 2048, preserving the 64-context/4-tier/256-row diagnostic target rather than shrinking tiers or row counts.

   Regression test: `tests/test_repair5g567_stage2a_diagnostic.py`.

15. Gate-3A checkpoint inference passed `auto` directly to `torch.load`.

   Symptom: true A5 Gate-3A generated the context pool but failed before replay with `RuntimeError: don't know how to restore data location ... tagged with auto`, because `infer_checkpoint_thetas(..., device="auto")` used `torch.load(..., map_location="auto")`.

   Fix: `infer_checkpoint_thetas` now normalizes `auto` to `cuda` when CUDA is available, otherwise `cpu`, before checkpoint loading and tensor placement.

   Regression test: `tests/test_repair5g567_gate3a_preflight.py`.

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

5. Direct-exact Stage-2A has not yet been remotely rerun after the nested-probe repair.

   The `uniform30_r5` timeout rows are now classified as old-path nested-probe evidence, not direct exact additive/static/g556/A5 evidence. Stage-2A remains blocked until the direct-exact rerun completes 256/256 rows with zero process hard timeouts, rc/final summary, and a true diagnostic A5 checkpoint.

6. Extreme-tail contexts remain an audit panel until direct exact is stable.

   Do not delete `tunnel`, `cross`, or `connector`. Keep failed high-density combinations in the timeout/tail audit and reintroduce them through curriculum after direct exact execution is stable.

7. Full campaign remains under absolute manual lock.

   Gate pass status, available GPU time, clean worktree, or disk availability must never be treated as full-campaign approval. Full can only start after Gate-3B evidence is reviewed and a new user message provides `APPROVE_G567_FULL_<EXACT_COMMIT_SHA>`.
