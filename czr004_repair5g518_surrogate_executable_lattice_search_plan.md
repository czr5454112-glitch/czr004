# Repair5G.5.18 Surrogate Executable Lattice Search Plan

Date: 2026-06-08

## Objective

Run a deeper local Repair5G.5.18 exploration round after the G5.17 no-gain result. The goal is to test whether bounded dual-channel `UpdateLTM` parameter candidates can improve candidate-space oracle evidence over the old 14-candidate lattice before any ranker or runtime-policy work is promoted.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, restart, or solver-control semantics.
- Do not inspect or run IDs `166..205`.
- Use local PC execution with `max_workers=1`.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.
- Commit and push only G5.18-related files.

## Execution Chain

1. Verify the G5.17 prerequisite artifacts and autopsy the 960-row negative result with `scripts/analyze_repair5g518_g517_lattice_autopsy.py`.
2. Add a generic project-owned G5.18 adapter grammar in `cpp/tools/phase1a_batch.cpp` for bounded names like `repair5g518_grid_c1p25_b1p50_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0`.
3. Generate a 100-300 candidate bounded pool and select three local batches with `scripts/propose_repair5g518_surrogate_lattice.py`.
4. Verify adapter recognition, invalid-name rejection, and old-equivalent fingerprints with `scripts/verify_repair5g518_adapter_grammar.py`.
5. Run batches A, B, and C with `scripts/run_repair5g518_probe_batches.py --max-workers 1`.
6. Analyze each batch against the old-14 oracle with `scripts/analyze_repair5g518_probe_batches.py`.
7. Run `scripts/run_repair5g518_full_primary_probe.py` only if a batch passes the candidate-space gate.
8. Write the final decision with `scripts/write_repair5g518_decision.py`.

## Candidate-Space Gates

A target batch is positive only if at least one gate passes:

- `new_candidate_win_count >= 2`
- `mean_new_oracle_gap_vs_old_oracle <= -0.002`
- `harmful_false_positive_target_contexts_improved >= 1`
- `missed_helpful_oracle_gap_reduced >= 3`

Full-primary and ranker work stay closed unless target-batch evidence improves.
