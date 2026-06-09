# Repair5G.5.10 Executable Goal-Aware Dual-Channel Lattice Plan

## Goal

Make the G5.9 bounded goal-aware dual-channel UpdateLTM lattice executable as observed-ID-only same-context counterfactual probes, then gate feature/target/policy work on measured oracle evidence.

## Scope

- Use the project-owned `cpp/tools/phase1a_batch.cpp` counterfactual probe hook.
- Add a narrow adapter for the 14 G5.9 lattice candidate IDs.
- Preserve LaCAM*/PIBT/search semantics and leave `external/lacam2/lacam2/**` untouched.
- Keep IDs 166..205 reserved.
- Do not integrate or claim a runtime learned policy.

## Protocol

1. Verify G5.9 artifacts exist.
2. Build the project-owned batch runner after the C++ adapter change.
3. Run a smoke probe over observed ID 146, two agent counts, primary budgets, and parity references.
4. Check static/additive parity using actual UpdateParams hashes and probe scores.
5. Run feasible observed-ID lattice counterfactuals over G5.8 contexts and G5.9 candidates.
6. Analyze candidate-space oracle gap versus static, additive, and G5.8.
7. Build runtime-safe feature matrix v2 from pre-update features/checkpoints only.
8. Create confidence targets v4 from 1000/2000ms stability.
9. Train/evaluate an abstention parameter policy only if candidate-space, feature, and target gates pass.
10. Write server commands if the desktop cannot finish the full 60-context lattice run.

## Non-Claims

This round does not claim Phase5.5, Phase6, AAAI readiness, runtime policy integration, action learning, priority learning, restart learning, h-value prediction, or candidate deletion.
