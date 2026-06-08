# Repair5G.5.19 Full-Primary New-Lattice Ranker and Safety Calibration

## Objective

Use the G5.18 full-primary 22-candidate probe table to test whether an offline, runtime-safe candidate-level selector can exploit the new bounded dual-channel UpdateLTM candidates without opening runtime, Phase5.5, Phase6, or AAAI claims.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, restart, or solver-control semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not inspect or run IDs `166..205`.
- Default local PC execution.
- Do not run the solver unless an optional later probe gate explicitly justifies it.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.

## Execution Package

1. Verify G5.18 artifacts and gates with `scripts/verify_repair5g519_g518_artifacts.py`.
2. Reconstruct 60 x 22 candidate targets with `scripts/create_repair5g519_full_primary_candidate_targets.py`.
3. Analyze candidate-space distribution with `scripts/analyze_repair5g519_full_primary_candidate_space.py`.
4. Build v8 runtime-safe feature rows with `scripts/create_repair5g519_candidate_feature_matrix_v8.py`.
5. Analyze feature signal and leakage guard status with `scripts/analyze_repair5g519_feature_signal_v8.py`.
6. Train representative deterministic ranker models with `scripts/train_repair5g519_full_primary_ranker_suite.py`.
7. Evaluate the full policy/control suite with `scripts/eval_repair5g519_full_primary_ranker_suite.py`.
8. Run failure autopsy with `scripts/analyze_repair5g519_ranker_failure_autopsy.py`.
9. Write final decision with `scripts/write_repair5g519_decision.py`.

## Required Decision Boundary

Even if an offline ranker passes, this round only supports a diagnostic next step. It does not validate a learned runtime policy and does not permit Phase5.5, Phase6, or AAAI claims.
